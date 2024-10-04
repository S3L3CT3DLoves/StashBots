import csv
from datetime import datetime
from enum import Enum
import json, re, sys, argparse
import time
from typing import List
from requests import get
from StashBoxCache import StashBoxCache
from StashBoxHelperClasses import PerformerUploadConfig, StashSource, normalize_url
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

def createPerformers(source : StashSource, destination : StashSource, uploads : List[PerformerUploadConfig], comment : str, cache : StashBoxCache = None):
    stashFilter = StashBoxFilterManager(stash.get_stashbox_connection(StashBoxSitesMapper.SOURCE_INFOS[destination]['url']))

    print("Checking if performers are already added in Edits")
    uploads = stashFilter.filterPerformersInQueue(uploads, True)
    print("Checking if performers are already in the DB")
    uploads = stashFilter.filterPerformersDupes(uploads, True)

    print(f"There are {len(uploads)} performers to upload")

    for upload in uploads:
        print(f"CrossPosting {upload['name']} from {source.name} to {destination.name}")

        perfManager = StashBoxPerformerManager(stash, source, destination, cache=cache)
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
    sourceUrl = [url for url in performer['urls'] if url['url'].startswith(StashBoxSitesMapper.SOURCE_INFOS[source]['url'])][0]['url']
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
        if compare == [ComparisonReturnCode.IDENTICAL]:
            compareLatest = sourcePerformerHistory.compareAtDateTime(datetime.now(), performer)
            if compareLatest != [ComparisonReturnCode.IDENTICAL]:
                print(f"Ready to update {performer['name']} : Performer { '/ has Update' if hasUpdate else '' } { '/ is incomplete' if incomplete else '' }")

                updateInput = perfManager.asPerformerEditDetailsInput()

                # Keep existing links to avoid removing data
                concatUrls = list(map(lambda x: {'site_id':x["site"]["id"], "url": x["url"]}, performer["urls"]))
                justExistingLinks = list(map(lambda x: normalize_url(x["url"]), performer["urls"]))
                for urlData in updateInput["urls"]:
                    normUrl = normalize_url(urlData["url"])
                    if normUrl not in justExistingLinks:
                        concatUrls.append(urlData)

                #For some reason, sometimes there are empty URLs, so filter them out
                concatUrls = list(filter(
                    lambda url : url != {},
                    concatUrls
                ))
                updateInput["urls"] = concatUrls

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

def manualUpdatePerformer(source : StashSource, destination : StashSource, performer : t.Performer, sourceId : str, comment : str, cache : StashBoxCache = None):
    """
    ### Summary
    Force update of a Performer based on the source and sourceId, not performing any checks
    """

    print(f"Ready to update {performer['name']}")
    
    sourcePerf = StashBoxPerformerManager(stash, source, destination, siteMapper, cache=cache)
    sourcePerf.getPerformer(sourceId)
    draft = sourcePerf.asPerformerEditDetailsInput()

    # Keep existing links to avoid removing data (need to map to string to dedup)
    existingUrls = list(map(lambda x: {'site_id':x["site"]["id"], "url": x["url"]}, performer["urls"]))

    # Add url to source if there is none yet
    existingUrls.append({
                "url" : f"{siteMapper.SOURCE_INFOS[source]['url']}performers/{sourcePerf.performer['id']}",
                "site_id" : siteMapper.SOURCE_INFOS[destination]['siteIds'][source]
            })
    
    concatUrls = [json.dumps(data, sort_keys=True) for data in existingUrls + draft["urls"]]
    concatUrls = list(set(concatUrls))
    concatUrls = [json.loads(data) for data in concatUrls]

    draft["urls"] = concatUrls
    

    try:
        newImgs = sourcePerf.uploadPerformerImages(exclude=performer.get("images", []))
        draft["image_ids"] = newImgs
        sourcePerf.submitPerformerUpdate(performer["id"], draft, comment, False)
    except Exception as e:
        print("Error processing performer")
        print(e)
    

    print(f"{performer['name']} updated")

def addStashBoxLinkPerformer(source : StashSource, destination : StashSource, performer : t.Performer, sourceId : str, comment : str):
    """
    ### Summary
    Add a StashBox link to an existing performer
    """

    print(f"Ready to update {performer['name']}")
    
    perfManager = StashBoxPerformerManager(stash, source, destination)
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

    draft["urls"] = existingUrls
    

    try:
        perfManager.submitPerformerUpdate(performer["id"], draft, comment, False)
    except Exception as e:
        print("Error processing performer")
        print(e)
    

    print(f"{performer['name']} updated")

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




if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog="StashBox Performer Manager",
        description="""CLI tool to allow management of StashBox performers\n
        Creation mode : lists Performers from your local Stash instance which have a link to SOURCE but not to TARGET, and creates the performer in TARGET\n
        Update mode : lists all Performers on TARGET that have a link to SOURCE, and updates them to mirror changes in SOURCE\n
        Manual mode: takes an input CSV file to force update performers, even if they would not be updated through Update mode (unless is has a Draft already)
        """,
        epilog="__StashBox_Perf_Mgr_v1.1__"
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

    statsParser = subparsers.add_parser("stats", parents=[generalParser], help="")

    linksParser = subparsers.add_parser("links", parents=[generalParser], help="")
    linksParser.add_argument("-l", "--limit", help="Maximum number of edits allowed", type=int, default=10)
    linksParser.add_argument("-m", "--mode", help="Mode", choices=['NOLINKS', 'NOSTASHBOX', "NOFANSDB"], default="NOLINKS")
    linksParser.add_argument("-e", "--exact", help="Only use exact matches", action="store_true")

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
            if perf["force"] != None and perf['force'].lower() == "true":
                performerGetter = StashBoxPerformerManager(stash, TARGET, TARGET, siteMapper)
                performerGetter.getPerformer(perf['targetId'])
                if not perf["targetId"] in performersWithOpenEdits:
                    manualUpdatePerformer(SOURCE, TARGET, performerGetter.performer, perf['sourceId'],args.comment)
                else:
                    print(f"Has Draft already {perf['name']}")
            else:
                print(f"Not updating {perf['name']}")


        args.input_file.close()
    
    elif sys.argv[0].lower() == "stats":
        performersList = []

        print("Using local cache for TARGET (always on)")
        targetCacheMgr.loadCache(True, 1, 2)

        print("Parsing list of performers to update")
        performersList = filterPerformersForUpdate(targetCacheMgr.cache.getCache(), SOURCE, TARGET, True)
        print(f"There are {len(performersList)} to review")

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
                    elif len(stashBoxUrls) == 1 and siteMapper.whichStashBoxLink(stashBoxUrls[0]["url"]) != TARGET:
                        otherStashBox.append({"id" : performer.get("id"), "name" : performer.get("name")})
                else:
                    noStashBox.append({"id" : performer.get("id"), "name" : performer.get("name")})
            else:
                noLinks.append({"id" : performer.get("id"), "name" : performer.get("name")})
        
        print(f"There are {len(multiLink)} performers with multiple links")
        print(f"There are {len(otherStashBox)} performers with a link to a single other StashBox")
        print(f"There are {len(noStashBox)} performers with no StashBox links")
        print(f"There are {len(noLinks)} performers with no links at all")

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
            if performer.get("urls"):
                if performer["deleted"]:
                    # Performer is deleted, skip
                    continue
                
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
        print(f"Mode = {args.mode} // Limit = {args.limit} // Exact = {args.exact}")
        if args.mode == "NOLINKS":
            print(f"There are {len(noLinks)} performers with no links in the target")
        elif args.mode == "NOSTASHBOX":
            print(f"There are {len(noStashBox)} performers with no links to the source in the target")
        
        for performerA in sourceCacheMgr.cache.getCache():
            if len(partialMatches) >= args.limit or len(matches) >= args.limit:
                break
            if i%1000 == 0:
                print(f"Searching... {i / len(sourceCacheMgr.cache.getCache()):.2%} in {time.time()-start:.2f}s")
            
            if args.mode == "NOSTASHBOX":
                for performerB in noStashBox:
                    if performerB.get("name").lower() == performerA.get("name").lower():
                        comp = comparePerformers(performerA, performerB)
                        if comp == [ComparisonReturnCode.IDENTICAL]:
                            print(f"Found {performerB["name"]} in noStashBox")
                            matches.append((performerA.get("id"), performerB.get("id")))

                        elif not args.exact and not ComparisonReturnCode.name in comp:
                            partialMatches.append((performerA.get("id"), performerB.get("id")))
                    else:
                        #for now only extact matches are supported
                        continue

            elif args.mode == "NOFANSDB":
                print("Not supported yet")
                sys.exit(0)

            elif args.mode == "NOLINKS":
                for performerB in noLinks:
                    if performerB.get("name").lower() == performerA.get("name").lower():
                        comp = comparePerformers(performerA, performerB)
                        if comp == [ComparisonReturnCode.IDENTICAL]:
                            print(f"Found {performerB["name"]} in noLinks")
                            matches.append((performerA.get("id"), performerB.get("id")))
                        elif not args.exact and not ComparisonReturnCode.name in comp:
                            partialMatches.append((performerA.get("id"), performerB.get("id")))
                    else:
                        #for now only extact matches are supported
                        continue
            i = i + 1
        
        if len(matches) > 0 or len(partialMatches) > 0:
            uploaded = 0
            if uploaded < args.limit:
                for sourcePerf, targetPerf in matches:
                    addStashBoxLinkPerformer(StashSource.STASHDB, StashSource.PMVSTASH,targetCacheMgr.cache.getPerformerById(targetPerf),sourcePerf, "Add StashDB Link")
                    uploaded = uploaded + 1
            sys.exit(0)