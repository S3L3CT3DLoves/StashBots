import csv
from datetime import datetime
from enum import Enum
import json, re, sys, argparse
import time
from typing import List
from requests import get
from tabulate import tabulate
from StashBoxCache import StashBoxCache
from StashBoxHelperClasses import PerformerUploadConfig, StashSource, normalise_url
import schema_types as t
from StashBoxWrapper import ComparisonReturnCode, StashBoxFilterManager, StashBoxPerformerHistory, StashBoxSitesMapper, StashBoxPerformerManager, convertCountry, getAllEdits, getAllPerformers, getOpenEdits, stashDateToDateTime, getImgB64, StashBoxCacheManager, comparePerformers
from stashapi.stashapp import StashInterface
from stashapi.stashbox  import StashBoxInterface


siteMapper = StashBoxSitesMapper()
stash : StashInterface

class ReturnCode(Enum):
    SUCCESS = 1
    HAS_DRAFT = 0
    NO_NEED = -1
    DIFF = -2
    DIFF_IMG = -3
    ERROR = -99

def concatenateUrls(destination: StashSource, existingUrls : list[t.URL], newUrls : list[t.URL]) -> list[t.URL]:
    """Returns a concatenated list of urls ready to send to StashBox

    Args:
        destination (StashSource): To avoid adding links that point to itself
        existingUrls (list[t.URL]): Existing links, to keep them, and avoid creating duplicates
        newUrls (list[t.URL]): Links to be added

    Returns:
        list[t.URL]: Concatenation of the two lists, without duplicates, empty items, or self-references
    """
    concatUrls = list(map(lambda x: {'site_id':x["site"]["id"], "url": x["url"]}, existingUrls))
    normalisedExistingUrls = list(map(lambda x: normalise_url(x["url"]), existingUrls))

    for urlData in newUrls:
        normUrl = normalise_url(urlData["url"])
        if normUrl not in normalisedExistingUrls:
            concatUrls.append(urlData)
            normalisedExistingUrls.append(normUrl)
    
    # Remove any empty urls, and any circular references
    concatUrls = list(filter(
        lambda url : url != {} and not siteMapper.isTargetStashBoxLink(url["url"], destination),
        concatUrls
    ))

    return concatUrls

def createPerformers(source : StashSource, destination : StashSource, uploads : List[PerformerUploadConfig], comment : str, cache : StashBoxCache = None):
    stashFilter = StashBoxFilterManager(stash.get_stashbox_connection(StashBoxSitesMapper.SOURCE_INFOS[destination]['url']))

    print("Checking if performers are already added in Edits")
    uploads = stashFilter.filterPerformersInQueue(uploads, True)
    print("Checking if performers are already in the DB")
    uploads = stashFilter.filterPerformersDupes(uploads, True)

    print(f"There are {len(uploads)} performers to upload")

    for upload in uploads:
        print(f"CrossPosting {upload['name']} from {source.name} to {destination.name}")

        perfManager = StashBoxPerformerManager(stash, source, destination, sitesMapper=siteMapper, cache=cache)
        perfManager.getPerformer(upload['id'])
        createInput = perfManager.asPerformerEditDetailsInput()
        # Upload the images
        createInput['image_ids'] = perfManager.uploadPerformerImages()

        # Add a link to the source info
        if source in siteMapper.SOURCE_INFOS[destination]['siteIds']:
            createInput['urls'].append({
                "url" : f"{siteMapper.SOURCE_INFOS[source]['url']}performers/{perfManager.performer['id']}",
                "site_id" : siteMapper.SOURCE_INFOS[destination]['siteIds'][source]
            })
        
        submitted = perfManager.submitPerformerCreate(createInput, comment)

        print(f"Performer Edit submitted : {siteMapper.SOURCE_INFOS[destination]['url']}edits/{submitted['id']}")

def updatePerformer(source : StashSource, destination : StashSource, performer : t.Performer, comment : str, outputFileStream = None, cache : StashBoxCache = None) -> ReturnCode:
    global siteMapper
    sourceUrl = [url for url in performer['urls'] if siteMapper.isTargetStashBoxLink(url['url'], source)][0]['url']
    sourceId = sourceUrl.split('/').pop()
    latestUpdateSource = stashDateToDateTime(performer["updated"])

    try:
        sourcePerformerHistory = StashBoxPerformerHistory(stash.get_stashbox_connection(StashBoxSitesMapper.SOURCE_INFOS[source]['url']), sourceId, cache, siteMapper)
    except Exception as e:
        print(f"{performer['name']} --- Error while processing --- !!!")
        print(f"{performer['name']},{performer['id']},{sourceId},ERROR,False", file=outputFileStream)
        return ReturnCode.ERROR
    perfManager = StashBoxPerformerManager(stash, source, destination, cache=cache, sitesMapper=siteMapper)
    perfManager.setPerformer(sourcePerformerHistory.performer)

    #Bugfix for non-iso country names
    if performer.get("country"):
        performer["country"] = convertCountry(performer.get("country"))

    hasUpdate = sourcePerformerHistory.hasUpdate(latestUpdateSource)
    incomplete = sourcePerformerHistory.isIncomplete(latestUpdateSource, performer)
    
    if (hasUpdate or incomplete):
        compare = sourcePerformerHistory.compareAtDateTime(latestUpdateSource, performer)
        if compare == [ComparisonReturnCode.IDENTICAL] or compare == [ComparisonReturnCode.images]:
            compareLatest = sourcePerformerHistory.compareAtDateTime(datetime.now(), performer)
            if compareLatest != [ComparisonReturnCode.IDENTICAL]:
                print(f"Ready to update {performer['name']} : Performer { '/ has Update' if hasUpdate else '' } { '/ is incomplete' if incomplete else '' }")

                updateInput = perfManager.asPerformerEditDetailsInput()
                updateInput["urls"] = concatenateUrls(destination, performer["urls"], updateInput["urls"])

                print("Uploading new images")
                newImgs = perfManager.uploadPerformerImages(existing=performer.get("images", []), removed=sourcePerformerHistory.removedImages)
                updateInput["image_ids"] = newImgs

                try:
                    perfManager.submitPerformerUpdate(performer["id"], updateInput, comment)
                    return ReturnCode.SUCCESS
                except Exception as e:
                    print("Error updating performer")
                    print(e)
                    return ReturnCode.ERROR
            else:
                return ReturnCode.NO_NEED
        
        if outputFileStream is not None:
            differences = ";".join(map(lambda x: x.name, compare))
            print(f"{performer['name']},{performer['id']},{perfManager.performer['id']},{differences},False", file=outputFileStream)
        return ReturnCode.DIFF
    else:
       return ReturnCode.NO_NEED

def manualUpdatePerformer(source : StashSource, destination : StashSource, performer : t.Performer, sourceId : str, comment : str, cache : StashBoxCache = None, bot = False):
    """
    ### Summary
    Force update of a Performer based on the source and sourceId, not performing any checks
    """

    print(f"Ready to update {performer['name']}")
    
    sourcePerf = StashBoxPerformerManager(stash, source, destination, siteMapper, cache=cache)
    sourcePerf.getPerformer(sourceId)
    draft = sourcePerf.asPerformerEditDetailsInput()

    # Add url to source, in case it's not there yet
    draft["urls"].append({
                "url" : f"{siteMapper.SOURCE_INFOS[source]['url']}performers/{sourcePerf.performer['id']}",
                "site_id" : siteMapper.SOURCE_INFOS[destination]['siteIds'][source]
            })
    draft["urls"] = concatenateUrls(destination, performer["urls"], draft["urls"])
    

    try:
        existingImgs = list(map(lambda x: x["id"],performer.get("images")))
        newImgs = sourcePerf.uploadPerformerImages(existing=performer.get("images", []))
        draft["image_ids"] = existingImgs + newImgs
        sourcePerf.submitPerformerUpdate(performer["id"], draft, comment, bot)
    except Exception as e:
        print("Error processing performer")
        print(e)
    

    print(f"{performer['name']} updated")

def addStashBoxLinkPerformer(source : StashSource, destination : StashSource, performer : t.Performer, sourceId : str, comment : str):
    """
    ### Summary
    Add a StashBox link to an existing performer
    """

    perfManager = StashBoxPerformerManager(stash, source, destination, siteMapper)
    perfManager.setPerformer(performer)
    draft = perfManager.asPerformerEditDetailsInput()


    # Keep existing links to avoid removing data
    existingUrls = list(map(lambda x:{
        'site_id': x["site"]["id"] if "site" in x else x["site_id"],
        "url": x["url"]
        }, draft["urls"]))

    # Add url
    existingUrls.append({
                "url" : f"{siteMapper.SOURCE_INFOS[source]['url']}performers/{sourceId}",
                "site_id" : siteMapper.SOURCE_INFOS[destination]['siteIds'][source]
            })

    # Call concatenateUrls, just to make sure we don't add duplicates (can cause Failed updates)
    draft["urls"] = concatenateUrls(destination, [], existingUrls)
    

    try:
        perfManager.submitPerformerUpdate(performer["id"], draft, comment, True)
        print(f"{performer['name']} updated")
    except Exception as e:
        print(f"Error processing performer {performer['name']}")
        raise(e)

def getPerformerUploadsFromStash(source : StashSource, destination : StashSource) -> List[PerformerUploadConfig]:
    sourceEndpointUrl = f"{StashBoxSitesMapper.SOURCE_INFOS[source]['url']}graphql"
    destinationEndpointUrl = f"{StashBoxSitesMapper.SOURCE_INFOS[destination]['url']}graphql"

    query = stash.find_performers(f = {
        "scene_count": {
            "modifier": "GREATER_THAN",
            "value": 0
        },
        "stash_id_endpoint": {
            "endpoint": sourceEndpointUrl,
            "stash_id": "",
            "modifier": "NOT_NULL"
        }
    })

    # Filter for performers which don't have a link to Destination yet
    TO_UPLOAD = filter(
        lambda perf: [stashbox for stashbox in perf['stash_ids'] if stashbox['endpoint'] == destinationEndpointUrl] == []
        , query
    )
    TO_UPLOAD = list(map(
        lambda perf: {
            "name" : perf["name"],
            "id" : [stashbox for stashbox in perf['stash_ids'] if stashbox['endpoint'] == sourceEndpointUrl][0]["stash_id"],
            "comment" : "StashDB Scrape"
        }
        , TO_UPLOAD
    ))
    return TO_UPLOAD

def filterPerformersForUpdate(performersList : List[t.Performer], source : StashSource, target : StashSource, verbose = False) -> List[t.Performer]:
    newList = []
    openEdits = getOpenEdits(stash.get_stashbox_connection(StashBoxSitesMapper.SOURCE_INFOS[target]['url']))
    performersWithOpenEdits = list(map(
        lambda edit : edit["target"]["id"],
        filter(
            lambda edit : edit["operation"] in ["MODIFY", "DESTROY"],
            openEdits
        )
    ))
    multiLink = 0
    haveLink = 0
    skipEdit = 0
    for performer in performersList:
        if performer.get("urls"):
            if performer["deleted"]:
                # Performer is deleted, skip
                continue

            if performer["id"] in performersWithOpenEdits:
                # Performer has an open Edit, skip
                skipEdit += 1
                continue

            if [url for url in performer['urls'] if siteMapper.isTargetStashBoxLink(url['url'], source)] == []:
                # Performer has no link to source
                continue
            haveLink += 1

            counter = 0
            for url in [url["url"] for url in performer["urls"]]:
                if siteMapper.whichStashBoxLink(url) != None:
                    counter += 1

            if counter > 1:
                # Performer has more than one StashBox link, for now this is not supported
                multiLink += 1
                continue

            newList.append(performer)

    if verbose:
        print(f"There are {haveLink} performers with Links to {source.name}")
        print(f"Skipping {multiLink} performers due to multiple StashBox Links")
        print(f"Skipping {skipEdit} performers ongoing edits")
        print(f"Filtered : {len(newList)}")
    return newList

def userCheckPerformerComparison(targetPerformer, sourcePerformer):
    comparison = comparePerformers(sourcePerformer, targetPerformer)
    if comparison == [ComparisonReturnCode.IDENTICAL]:
        # Not sure how that is possible, but it happens sometimes, due to diff between comparePerformers and compareAtDateTime
        return True

    comparisonTable = []
    for attr in "name","gender","ethnicity","country":
        attrTitle = attr
        if ComparisonReturnCode[attr] in comparison:
            attrTitle = "[*]" + attrTitle
        comparisonTable.append([attrTitle, targetPerformer.get(attr), sourcePerformer.get(attr)])

    bdayTitle = "bday"
    if ComparisonReturnCode.birth_date in comparison:
        bdayTitle = "[*]" + bdayTitle
    comparisonTable.append([bdayTitle, targetPerformer.get("birth_date", targetPerformer.get("birthdate")),sourcePerformer.get("birth_date", sourcePerformer.get("birthdate"))])
    
    for attr in "aliases", "disambiguation","breast_type","cup_size","band_size","waist_size", "eye_color","hair_color","height","hip_size","career_start_year","career_end_year":
        attrTitle = attr
        if ComparisonReturnCode[attr] in comparison:
            attrTitle = "[*]" + attrTitle
        comparisonTable.append([attrTitle, targetPerformer.get(attr), sourcePerformer.get(attr)])
    
    print(tabulate(comparisonTable, headers=['Attr', 'Target', 'Source']))
    try:
        userReturn = input("Are these the same performer? (y/N) ")
        return userReturn.lower() == "y"
    except KeyboardInterrupt as k:
        print("Exiting")
        sys.exit(0)
    except Exception as e:
        raise e

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog="StashBox Performer Manager",
        description="""CLI tool to allow management of StashBox performers\n
        Creation mode : lists Performers from your local Stash instance which have a link to SOURCE but not to TARGET, and creates the performer in TARGET\n
        Update mode : lists all Performers on TARGET that have a link to SOURCE, and updates them to mirror changes in SOURCE\n
        Manual mode: takes an input CSV file to force update performers, even if they would not be updated through Update mode (unless is has a Draft already)\n
        Stats mode: returns information about performers and their links to other StashBoxes\n
        Links mode: automates adding links to performers that were scraped from a StashBox but don't have a link
        """,
        epilog="__StashBox_Perf_Mgr_v1.2__"
    )
    subparsers = parser.add_subparsers()

    generalParser = argparse.ArgumentParser(add_help=False)
    generalParser.add_argument("-s", "--stash", help="Local Stash url to be used to get the Stashbox config", default="http://localhost:9999/")
    generalParser.add_argument("-c", "--comment", help="Comment for StashBox Edits", default="[BOT] StashBox-PerformerBot Edit")
    generalParser.add_argument("-tsb", "--target-stashbox", help="Target StashBox instance", choices=['STASHDB', 'PMVSTASH', "FANSDB"], required=True)
    generalParser.add_argument("-ssb", "--source-stashbox", help="Source StashBox instance", choices=['STASHDB', 'PMVSTASH', "FANSDB"], required=True)

    createParser = subparsers.add_parser("create", parents=[generalParser], help="")

    updateParser = subparsers.add_parser("update", parents=[generalParser], help="")
    updateParser.add_argument("-o", "--output", help="Output file to list not-updated performers", type=argparse.FileType('w+', encoding='UTF-8'))
    updateParser.add_argument("-l", "--limit", help="Maximum number of edits allowed", type=int, default=100000)
    updateParser.add_argument("-sc", "--source-cache", help="Use a local cache for Source StashBox", action="store_true")

    manualParser = subparsers.add_parser("manual", parents=[generalParser], help="")
    manualParser.add_argument("-i", "--input-file", help="Input csv file containing the performers to be updated", type=argparse.FileType('r', encoding='UTF-8'))
    manualParser.add_argument("-t", "--terminal", help="Show text comparisons in the terminal for user review", action="store_true")

    statsParser = subparsers.add_parser("stats", parents=[generalParser], help="")

    linksParser = subparsers.add_parser("links", parents=[generalParser], help="")
    linksParser.add_argument("-l", "--limit", help="Maximum number of edits allowed", type=int, default=10)
    linksParser.add_argument("-m", "--mode", help="Mode", choices=['NOLINKS', 'NOSTASHBOX', 'ALL'], default="NOLINKS")
    linksParser.add_argument("-e", "--exact", help="Only use exact matches", action="store_true")
    linksParser.add_argument("-sk", "--skip", help="Skip X% of the DB", type=int, default=0)

    argv = sys.argv
    argv.pop(0)
    args = parser.parse_args(argv)


    stashParams = re.match("(https?)://([-a-zA-Z0-9.]{2,256})*:?(\\d{0,5})", args.stash)
    if not stashParams:
        print("Stash URL must be of format: http(s)://domain:port\nExample: http://localhost:9999")
        sys.exit(1)
    
    stashInt = {
        "scheme": stashParams.groups()[0],
        "host": stashParams.groups()[1]
    }
    if len(stashParams.groups()) == 3:
        stashInt["port"] = stashParams.groups()[2]

    stash = StashInterface(stashInt)

    SOURCE = StashSource[args.source_stashbox]
    TARGET = StashSource[args.target_stashbox]
    siteMapper.SOURCE = SOURCE
    siteMapper.DESTINATION = TARGET
    siteMapper.getSitesFromDestinationServer(stash.get_stashbox_connection(StashBoxSitesMapper.SOURCE_INFOS[TARGET]['url']))

    targetCacheMgr = StashBoxCacheManager(stash.get_stashbox_connection(StashBoxSitesMapper.SOURCE_INFOS[TARGET]['url']), TARGET, True)

    count = 0

    if sys.argv[0].lower() == "update":
        print("Update mode")
        # Update mode
        performersList = []

        print("Using local cache for TARGET (always on)")
        targetCacheMgr.loadCache(True, 24, 7)
        sourceCacheMgr = StashBoxCacheManager(stash.get_stashbox_connection(StashBoxSitesMapper.SOURCE_INFOS[SOURCE]['url']), SOURCE, True) if args.source_cache else None
        if sourceCacheMgr != None:
            print("Using local cache for SOURCE")
            sourceCacheMgr.loadCache(True, 24, 7)

        print("Parsing list of performers to update")
        performersList = filterPerformersForUpdate(targetCacheMgr.cache.getCache(), SOURCE, TARGET)
        print(f"There are {len(performersList)} to review")
        
        #Now actually do the update
        plist = list(reversed(performersList))
        for performer in plist:
            status = updatePerformer(SOURCE, TARGET, performer, args.comment, args.output, cache=sourceCacheMgr.cache if sourceCacheMgr != None else None)
            if status == ReturnCode.SUCCESS:
                count += 1
                print(f"{performer['name']} updated")
            else:
                if status == ReturnCode.HAS_DRAFT:
                    print(f"{performer['name']} not updated - DRAFT exists")
                elif status == ReturnCode.NO_NEED:
                    print(f"{performer['name']} not updated - no update required")
                elif status == ReturnCode.DIFF:
                    print(f"{performer['name']} not updated - manual change was made")
                elif status == ReturnCode.ERROR:
                    print(f"{performer['name']} not updated - ERROR")
                
            if count >= args.limit:
                print(f"{count} performers updated")
                sys.exit()
        
        if args.output is not None:
            args.output.close()
        print(f"{count} performers updated")

    elif sys.argv[0].lower() == "create":
        print("Creation mode")
        createPerformers(SOURCE, TARGET, getPerformerUploadsFromStash(SOURCE, TARGET), args.comment)

    elif sys.argv[0].lower() == "manual":
        print("Manual Update mode")
        if args.input_file is None:
            print("An input CSV file is required")
            sys.exit()
        updateList = csv.DictReader(args.input_file, fieldnames=['name','targetId','sourceId',"reason","force"])
        openEdits = getOpenEdits(stash.get_stashbox_connection(StashBoxSitesMapper.SOURCE_INFOS[TARGET]['url']))
        performersWithOpenEdits = list(map(
            lambda edit : edit["target"]["id"],
            filter(
                lambda edit : edit["operation"] in ["MODIFY", "DESTROY"],
                openEdits
            )
        ))
        for perf in updateList:
            if perf["targetId"] in performersWithOpenEdits:
                print(f"Has Draft already {perf['name']}")
                continue
            if perf["force"] != None and perf['force'].lower() == "true":
                performerGetter = StashBoxPerformerManager(stash, TARGET, TARGET, siteMapper)
                performerGetter.getPerformer(perf['targetId'])
                manualUpdatePerformer(SOURCE, TARGET, performerGetter.performer, perf['sourceId'],args.comment, bot=False)
            elif args.terminal and perf["reason"] != None and "images" not in perf["reason"].split(";"):
                perfTarget = StashBoxPerformerManager(stash, TARGET, TARGET, siteMapper)
                perfTarget.getPerformer(perf['targetId'])

                perfSource = StashBoxPerformerManager(stash, SOURCE, SOURCE, siteMapper)
                perfSource.getPerformer(perf['sourceId'])

                if userCheckPerformerComparison(perfTarget.performer, perfSource.performer):
                    manualUpdatePerformer(SOURCE, TARGET, perfTarget.performer, perf['sourceId'],args.comment, bot=True)
                else:
                    print(f"Not updating {perf['name']}")

            else:
                print(f"Not updating {perf['name']}")


        args.input_file.close()
    
    elif sys.argv[0].lower() == "stats":
        performersList = []

        print("Using local cache for TARGET (always on)")
        targetCacheMgr.loadCache(True, 12, 2)

        targetStashBox = []
        multiLink = []
        otherStashBox = []
        noLinks = []
        noStashBox = []
        for performer in targetCacheMgr.cache.getCache():
            if performer.get("urls"):
                if performer["deleted"]:
                    # Performer is deleted, skip
                    continue
                
                stashBoxUrls = [url for url in performer['urls'] if siteMapper.whichStashBoxLink(url["url"]) != None]
                if stashBoxUrls != []:
                    if len(stashBoxUrls) > 1:
                        multiLink.append({"id" : performer.get("id"), "name" : performer.get("name")})
                    elif len(stashBoxUrls) == 1 and siteMapper.whichStashBoxLink(stashBoxUrls[0]["url"]) == SOURCE:
                        targetStashBox.append({"id" : performer.get("id"), "name" : performer.get("name")})
                    elif len(stashBoxUrls) == 1 and siteMapper.whichStashBoxLink(stashBoxUrls[0]["url"]) != SOURCE:
                        otherStashBox.append({"id" : performer.get("id"), "name" : performer.get("name")})
                else:
                    noStashBox.append({"id" : performer.get("id"), "name" : performer.get("name")})
            else:
                noLinks.append({"id" : performer.get("id"), "name" : performer.get("name")})
        
        statsTable = [
            ["Linked to TARGET", len(targetStashBox)],
            ["Links to multiple StashBoxes" , len(multiLink)],
            ["Linked to another StashBox only", len(otherStashBox)],
            ["No StashBox links", len(noStashBox)],
            ["No links", len(noLinks)]
        ]
        print(tabulate(statsTable))

        with open("stats-nolinks.json", mode='w') as file:
            json.dump(noLinks, file)
        with open("stats-multilinks.json", mode='w') as file:
            json.dump(multiLink, file)
        with open("stats-noSB.json", mode='w') as file:
            json.dump(noStashBox, file)
 
    elif sys.argv[0].lower() == "links":
        targetCacheMgr.loadCache(True, 12, 2)
        sourceCacheMgr = StashBoxCacheManager(stash.get_stashbox_connection(StashBoxSitesMapper.SOURCE_INFOS[SOURCE]['url']), SOURCE, True)
        sourceCacheMgr.loadCache(True, 48, 7)

        openEdits = getOpenEdits(stash.get_stashbox_connection(StashBoxSitesMapper.SOURCE_INFOS[TARGET]['url']))
        performersWithOpenEdits = list(map(
            lambda edit : edit["target"]["id"],
            filter(
                lambda edit : edit["operation"] in ["MODIFY", "DESTROY"],
                openEdits
            )
        ))

        noLinks = []
        noStashBox = []
        for performer in targetCacheMgr.cache.getCache():
            if performer["id"] in performersWithOpenEdits:
                # Don't edit performers with ongoing changes, to avoid conflicts
                continue
            if performer["deleted"]:
                # Performer is deleted, skip
                continue
            if performer.get("urls"):
                stashBoxUrls = [url for url in performer['urls'] if siteMapper.whichStashBoxLink(url["url"]) != None]
                if stashBoxUrls != []:
                    continue
                else:
                    noStashBox.append(performer)
            else:
                noLinks.append(performer)
        
        matches = []
        partialMatches = []

        print(f"There are {len(sourceCacheMgr.cache.getCache())} performers in the source")
        i = 0
        start = time.time()
        print(f"Mode = {args.mode} // Limit = {args.limit} (Skip {args.skip}%) // Exact = {args.exact}")
        if args.mode == "ALL" or args.mode == "NOLINKS":
            print(f"There are {len(noLinks)} performers with no links in the target")
        if args.mode == "ALL" or args.mode == "NOSTASHBOX":
            print(f"There are {len(noStashBox)} performers with no links to the source in the target")
        
        for performerA in sourceCacheMgr.cache.getCache():
            if len(matches) >= args.limit:
                break

            # Display progress
            if i%1000 == 0:
                print(f"Searching... {i / len(sourceCacheMgr.cache.getCache()):.2%} in {time.time()-start:.2f}s")

            # Skip X% of the DB, to save time when using a low limit and calling the function several times
            if i*100 / len(sourceCacheMgr.cache.getCache()) < args.skip:
                i = i +1
                continue

            if args.mode == "ALL" or args.mode == "NOSTASHBOX":
                for performerB in noStashBox:
                    if performerB.get("name").lower() == performerA.get("name").lower():
                        comp = comparePerformers(performerA, performerB)
                        if comp == [ComparisonReturnCode.IDENTICAL]:
                            print(f"Found {performerB["name"]} in noStashBox")
                            matches.append((performerA.get("id"), performerB.get("id")))
                        elif not args.exact and not ComparisonReturnCode.gender in comp:
                            if userCheckPerformerComparison(performerB, performerA):
                                matches.append((performerA.get("id"), performerB.get("id")))
                    else:
                        #for now only name matches are supported
                        continue

            if args.mode == "ALL" or args.mode == "NOLINKS":
                for performerB in noLinks:
                    if performerB.get("name").lower() == performerA.get("name").lower():
                        comp = comparePerformers(performerA, performerB)
                        if comp == [ComparisonReturnCode.IDENTICAL]:
                            print(f"Found {performerB["name"]} in noLinks")
                            matches.append((performerA.get("id"), performerB.get("id")))
                        elif not args.exact and not ComparisonReturnCode.gender in comp:
                            if userCheckPerformerComparison(performerB, performerA):
                                matches.append((performerA.get("id"), performerB.get("id")))
                    else:
                        #for now only name matches are supported
                        continue
            i = i + 1

        
        if len(matches) > 0:
            uploaded = 0
            print(f"Found {len(matches)} matches to upload")
            if uploaded < args.limit:
                for sourcePerf, targetPerf in matches:
                    addStashBoxLinkPerformer(SOURCE, TARGET,targetCacheMgr.cache.getPerformerById(targetPerf),sourcePerf, "Add FansDB Link")
                    uploaded = uploaded + 1
            sys.exit(0)