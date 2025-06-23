import csv
from datetime import datetime
from enum import Enum
import sys, argparse
from typing import List
from tabulate import tabulate
from StashBoxCache import StashBoxCache
from StashBoxHelperClasses import StashSource, normalise_url
import schema_types as t
from StashBoxWrapper import ComparisonReturnCode, StashBoxPerformerHistory, StashBoxSitesMapper, StashBoxPerformerManager, convertCountry, getOpenEdits, stashDateToDateTime, StashBoxCacheManager, comparePerformers
from stashapi.stashapp import StashInterface
import configparser


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

def updatePerformer(source : StashSource, destination : StashSource, sourceEndpoint, destinationEndpoint, performer : t.Performer, comment : str, outputFileStream = None, cache : StashBoxCache = None) -> ReturnCode:
    global siteMapper
    sourceUrl = [url for url in performer['urls'] if siteMapper.isTargetStashBoxLink(url['url'], source)][0]['url']
    sourceId = sourceUrl.split('/').pop()
    latestUpdateDate = stashDateToDateTime(performer["updated"])

    try:
        sourcePerformerHistory = StashBoxPerformerHistory(sourceEndpoint, sourceId, cache, siteMapper)
    except Exception as e:
        print(f"{performer['name']} --- Error while processing --- !!!")
        print(f"{performer['name']},{performer['id']},{sourceId},ERROR,False", file=outputFileStream)
        return ReturnCode.ERROR
    perfManager = StashBoxPerformerManager(sourceEndpoint, destinationEndpoint, cache=cache, sitesMapper=siteMapper)
    perfManager.setPerformer(sourcePerformerHistory.performer)

    #Bugfix for non-iso country names
    if performer.get("country"):
        performer["country"] = convertCountry(performer.get("country"))

    hasUpdate = sourcePerformerHistory.hasUpdate(latestUpdateDate)
    incomplete = sourcePerformerHistory.isIncomplete(latestUpdateDate, performer)
    
    if (hasUpdate or incomplete):
        # Only update if the current info of Performer is identical to the past info in SOURCE (avoid overwritting manually changed info)
        compare = sourcePerformerHistory.compareAtDateTime(latestUpdateDate, performer)
        if compare == [ComparisonReturnCode.IDENTICAL] or compare == [ComparisonReturnCode.images]:
            # Check that there is actually a change to push
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
                return ReturnCode.DIFF
        
        if outputFileStream is not None:
            differences = ";".join(map(lambda x: x.name, compare))
            print(f"{performer['name']},{performer['id']},{perfManager.performer['id']},{differences},False", file=outputFileStream)
        return ReturnCode.DIFF
    else:
       return ReturnCode.NO_NEED

def manualUpdatePerformer(source : StashSource, destination : StashSource, sourceEndpoint, destinationEndpoint, performer : t.Performer, sourceId : str, comment : str, cache : StashBoxCache = None, bot = False):
    """
    ### Summary
    Force update of a Performer based on the source and sourceId, not performing any checks
    """

    print(f"Ready to update {performer['name']}")
    
    sourcePerf = StashBoxPerformerManager(sourceEndpoint, destinationEndpoint, siteMapper, cache=cache)
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

def filterPerformersForUpdate(performersList : List[t.Performer], source : StashSource, sourceEndpoint, verbose = False) -> List[t.Performer]:
    newList = []
    openEdits = getOpenEdits(sourceEndpoint)
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
        print(f"There are {haveLink} performers with Links to {sourceEndpoint.name}")
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


def configureArgumentParser():
    parser = argparse.ArgumentParser(
        prog="StashBox Performer Manager",
        description="""CLI tool to allow management of StashBox performers\n
        Update mode : lists all Performers on TARGET that have a link to SOURCE, and updates them to mirror changes in SOURCE\n
        Manual mode: takes an input CSV file to force update performers, even if they would not be updated through Update mode (unless is has a Draft already)
        """,
        epilog="__StashBox_Perf_Mgr_v2.0__"
    )
    subparsers = parser.add_subparsers()

    generalParser = argparse.ArgumentParser(add_help=False)
    generalParser.add_argument("-c", "--comment", help="Comment for StashBox Edits", default="[BOT] StashBox-PerformerBot Edit")
    generalParser.add_argument("-tsb", "--target-stashbox", help="Target StashBox instance", choices=['STASHDB', 'PMVSTASH', "FANSDB"], required=True)
    generalParser.add_argument("-ssb", "--source-stashbox", help="Source StashBox instance", choices=['STASHDB', 'PMVSTASH', "FANSDB"], required=True)

    updateParser = subparsers.add_parser("update", parents=[generalParser], help="")
    updateParser.add_argument("-o", "--output", help="Output file to list not-updated performers", type=argparse.FileType('w+', encoding='UTF-8'))
    updateParser.add_argument("-l", "--limit", help="Maximum number of edits allowed", type=int, default=100000)
    updateParser.add_argument("-sc", "--source-cache", help="Use a local cache for Source StashBox", action="store_true")

    manualParser = subparsers.add_parser("manual", parents=[generalParser], help="")
    manualParser.add_argument("-i", "--input-file", help="Input csv file containing the performers to be updated", type=argparse.FileType('r', encoding='UTF-8'))
    manualParser.add_argument("-t", "--terminal", help="Show text comparisons in the terminal for user review", action="store_true")

    return parser

def readConfigFile():
    config = configparser.ConfigParser()
    config.read('config.ini')

    config_values = {}

    for each_section in config.sections():
        if each_section == "GENERAL":
            config_values["STASH"] =  config.get(each_section, 'stash_url')
        else:
            config_values[each_section] = {
                "name" : each_section,
                "endpoint" : config.get(each_section, 'api_url'),
                "api_key" : config.get(each_section, 'api_key')
            }

    return config_values

if __name__ == '__main__':
    argumentParser = configureArgumentParser()
    argv = sys.argv
    argv.pop(0)
    args = argumentParser.parse_args(argv)
    config = readConfigFile()

    SOURCE = StashSource[args.source_stashbox]
    SOURCE_ENDPOINT = config[args.source_stashbox]
    TARGET = StashSource[args.target_stashbox]
    TARGET_ENDPOINT = config[args.target_stashbox]

    siteMapper.SOURCE = SOURCE
    siteMapper.DESTINATION = TARGET
    siteMapper.getSitesFromDestinationServer(TARGET_ENDPOINT)

    targetCacheMgr = StashBoxCacheManager(TARGET_ENDPOINT, True)

    COUNT = 0

    if sys.argv[0].lower() == "update":
        print("Update mode")
        # Update mode
        performersList = []

        print("Using local cache for TARGET (always on)")
        targetCacheMgr.loadCache(True, 24, 7)
        sourceCacheMgr = StashBoxCacheManager(SOURCE_ENDPOINT,  True) if args.source_cache else None
        if sourceCacheMgr is not None:
            print("Using local cache for SOURCE")
            sourceCacheMgr.loadCache(True, 24, 14)

        print("Parsing list of performers to update")
        performersList = filterPerformersForUpdate(targetCacheMgr.cache.getCache(), SOURCE, SOURCE_ENDPOINT)
        print(f"There are {len(performersList)} to review")
        
        #Now actually do the update
        plist = list(reversed(performersList))
        for performer in plist:
            status = updatePerformer(SOURCE, TARGET, SOURCE_ENDPOINT, TARGET_ENDPOINT, performer, args.comment, args.output, cache=sourceCacheMgr.cache if sourceCacheMgr != None else None)
            if status == ReturnCode.SUCCESS:
                COUNT += 1
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
                
            if COUNT >= args.limit:
                print(f"{COUNT} performers updated")
                sys.exit()
        
        if args.output is not None:
            args.output.close()
        print(f"{COUNT} performers updated")

    elif sys.argv[0].lower() == "manual":
        print("Manual Update mode")
        if args.input_file is None:
            print("An input CSV file is required")
            sys.exit()
        updateList = csv.DictReader(args.input_file, fieldnames=['name','targetId','sourceId',"reason","force"])
        openEdits = getOpenEdits(TARGET_ENDPOINT)
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
            if perf["force"] is not None and perf['force'].lower() == "true":
                performerGetter = StashBoxPerformerManager(TARGET_ENDPOINT, None, siteMapper)
                performerGetter.getPerformer(perf['targetId'])
                manualUpdatePerformer(SOURCE, TARGET, SOURCE_ENDPOINT, TARGET_ENDPOINT, performerGetter.performer, perf['sourceId'],args.comment, bot=True)
            elif args.terminal and perf["reason"] is not None and "images" not in perf["reason"].split(";"):
                perfTarget = StashBoxPerformerManager(TARGET_ENDPOINT, None, siteMapper)
                perfTarget.getPerformer(perf['targetId'])

                perfSource = StashBoxPerformerManager(SOURCE_ENDPOINT, None, siteMapper)
                perfSource.getPerformer(perf['sourceId'])

                if userCheckPerformerComparison(perfTarget.performer, perfSource.performer):
                    manualUpdatePerformer(SOURCE, TARGET, SOURCE_ENDPOINT, TARGET_ENDPOINT, perfTarget.performer, perf['sourceId'],args.comment, bot=True)
                else:
                    print(f"Not updating {perf['name']}")

            else:
                print(f"Not updating {perf['name']}")


        args.input_file.close()