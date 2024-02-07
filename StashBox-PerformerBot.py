import csv
from datetime import datetime, date, timedelta
from enum import Enum
import glob
import json, os, re, sys, argparse

from requests import get
from StashBoxCacheManager import StashBoxCacheManager
import schema_types as t
from StashBoxWrapper import PerformerUploadConfig, StashBoxFilterManager, StashBoxPerformerHistory, StashSource, StashBoxSitesMapper, StashBoxPerformerManager, convertCountry, getAllEdits, getAllPerformers, stashDateToDateTime, getImgB64
from stashapi.stashapp import StashInterface


siteMapper = StashBoxSitesMapper()

class ReturnCode(Enum):
    SUCCESS = 1
    HAS_DRAFT = 0
    NO_NEED = -1
    DIFF = -2
    ERROR = -99

    

def createPerformers(stash : StashInterface, source : StashSource, destination : StashSource, uploads : [PerformerUploadConfig], comment : str):
    stashFilter = StashBoxFilterManager(stash.get_stashbox_connection(StashBoxSitesMapper.SOURCE_INFOS[destination]['url']))

    print("Checking if performers are already added in Edits")
    uploads = stashFilter.filterPerformersInQueue(uploads, True)
    print("Checking if performers are already in the DB")
    uploads = stashFilter.filterPerformersDupes(uploads, True)

    print(f"There are {len(uploads)} performers to upload")

    for upload in uploads:
        print(f"CrossPosting {upload['name']} from {source} to {destination}")

        perfManager = StashBoxPerformerManager(stash, source, destination)
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

def updatePerformer(stash : StashInterface, source : StashSource, destination : StashSource, performer : t.Performer, comment : str, outputFileStream = None) -> ReturnCode:
    sourceUrl = [url for url in performer['urls'] if url['url'].startswith(StashBoxSitesMapper.SOURCE_INFOS[source]['url'])][0]['url']
    sourceId = sourceUrl.split('/').pop()
    lastUpdate = stashDateToDateTime(performer["updated"])
    sourcePerformerHistory = StashBoxPerformerHistory(stash.get_stashbox_connection(StashBoxSitesMapper.SOURCE_INFOS[source]['url']), sourceId)
    perfManager = StashBoxPerformerManager(stash, source, destination)
    perfManager.setPerformer(sourcePerformerHistory.performer)

    if perfManager.hasOpenDrafts(performer, stash.get_stashbox_connection(StashBoxSitesMapper.SOURCE_INFOS[destination]['url'])):
        return ReturnCode.HAS_DRAFT

    #Bugfix for non-iso country names
    if performer.get("country"):
        performer["country"] = convertCountry(performer.get("country"))

    hasUpdate = sourcePerformerHistory.hasUpdate(lastUpdate)
    incomplete = sourcePerformerHistory.isIncomplete(lastUpdate, performer)
    compare = sourcePerformerHistory.compareAtDateTime(lastUpdate, performer)
    if (hasUpdate or incomplete) and compare:
        print(f"Ready to update {performer['name']}")

        updateInput = perfManager.asPerformerEditDetailsInput()

        # Keep existing links to avoid removing data (need to map to string to dedup)
        existingUrls = list(map(lambda x: {'site_id':x["site"]["id"], "url": x["url"]}, performer["urls"]))
        concatUrls = [json.dumps(data, sort_keys=True) for data in existingUrls + updateInput["urls"]]
        concatUrls = list(set(concatUrls))
        concatUrls = [json.loads(data) for data in concatUrls]
        updateInput["urls"] = concatUrls

        print("Loading existing images")
        existingImgs = list(map(lambda x: getImgB64(x['url']),performer.get("images", [])))
        print("Uploading new images")
        newImgs = perfManager.uploadPerformerImages(exclude=existingImgs)
        updateInput["image_ids"] = newImgs + list(map(lambda x: x['id'],performer.get("images", [])))


        perfManager.submitPerformerUpdate(performer["id"], updateInput, comment)
        return ReturnCode.SUCCESS
    else:
        if not hasUpdate and not incomplete:
            return ReturnCode.NO_NEED
        if not compare:
            if outputFileStream is not None:
                print(f"{performer['name']},{performer['id']},{perfManager.performer['id']},DIFF,False", file=outputFileStream)
            return ReturnCode.DIFF
    
    return ReturnCode.ERROR

def manualUpdatePerformer(stash : StashInterface, source : StashSource, destination : StashSource, performer : t.Performer, sourceId : str, comment : str):
    """
    ### Summary
    Force update of a Performer based on the source and sourceId, not performing any checks
    """

    print(f"Ready to update {performer['name']}")
    
    sourcePerf = StashBoxPerformerManager(stash, source, destination, siteMapper)
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
    

    print("Loading existing images")
    existingImgs = list(map(lambda x: getImgB64(x['url']),performer.get("images", [])))
    print("Uploading new images")
    newImgs = sourcePerf.uploadPerformerImages(exclude=existingImgs)
    draft["image_ids"] = newImgs + list(map(lambda x: x['id'],performer.get("images", [])))
    sourcePerf.submitPerformerUpdate(performer["id"], draft, comment, False)

    print(f"{performer['name']} updated")

def getPerformerUploadsFromStash(stash : StashInterface, source : StashSource, destination : StashSource) -> [PerformerUploadConfig]:
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

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog="StashBox Performer Manager",
        description="""CLI tool to allow management of StashBox performers\n
        Creation mode : lists Performers from your local Stash instance which have a link to SOURCE but not to TARGET, and creates the performer in TARGET\n
        Update mode : lists all Performers on TARGET that have a link to SOURCE, and updates them to mirror changes in SOURCE\n
        Manual mode: takes an input CSV file to force update performers, even if they would not be updated through Update mode (unless is has a Draft already)
        """,
        epilog="__StashBox_Perf_Mgr_v0.4__"
    )
    parser.add_argument("-m", help="Options: c - CREATE / u - UPDATE", choices=['create', 'update','manual', 'updatecache', 'test'], required=True)
    parser.add_argument("-s", "--stash", help="Local Stash url to be used to get the Stashbox config", default="http://localhost:9999/")
    parser.add_argument("-tsb", "--target-stashbox", help="Target StashBox instance", choices=['STASHDB', 'PMVSTASH', "FANSDB"], required=True)
    parser.add_argument("-ssb", "--source-stashbox", help="Source StashBox instance", choices=['STASHDB', 'PMVSTASH', "FANSDB"], required=True)
    parser.add_argument("-c", "--comment", help="Comment for StashBox Edits", default="[BOT] StashBox-PerformerBot Edit")
    parser.add_argument("-l", "--limit", help="Maximum number of edits allowed (Update mode only)", type=int, default=100000)
    parser.add_argument("-o", "--output", help="Output file for update mode, to list not-updated performers", type=argparse.FileType('w+', encoding='UTF-8'))
    parser.add_argument("-i", "--input-file", help="Input csv file containing the performers to be updated in Manual mode", type=argparse.FileType('r', encoding='UTF-8'))

    argv = sys.argv
    argv.pop(0)
    args = parser.parse_args(argv)


    stashParams = re.match("(https?):\/\/([-a-zA-Z0-9.]{2,256})*:?(\d{0,5})", args.stash)
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

    sourceCacheMgr = StashBoxCacheManager(stash.get_stashbox_connection(StashBoxSitesMapper.SOURCE_INFOS[SOURCE]['url']), SOURCE, False)
    targetCacheMgr = StashBoxCacheManager(stash.get_stashbox_connection(StashBoxSitesMapper.SOURCE_INFOS[TARGET]['url']), TARGET, True)

    count = 0

    if args.m.lower() == "update":
        print("Update mode")
        # Update mode
        performersList = []

        targetCacheMgr.loadCache(True, 24, 7)
        print("Using local cache")

        performersList = list(filter(
            lambda performer: [url for url in performer['urls'] if url['url'].startswith(StashBoxSitesMapper.SOURCE_INFOS[SOURCE]['url'])] != [],
            targetCacheMgr.cache.getCache()
        ))
        print(len(performersList))
        
        #Now actually do the update
        plist = list(reversed(performersList))
        for performer in plist:
            status = updatePerformer(stash, SOURCE, TARGET, performer, args.comment, args.output)
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

    elif args.m.lower() == "create":
        print("Creation mode")
        createPerformers(stash, SOURCE, TARGET, getPerformerUploadsFromStash(stash, SOURCE, TARGET), args.comment)

    elif args.m.lower() == "manual":
        print("Manual Update mode")
        if args.input_file is None:
            print("An input CSV file is required")
            sys.exit()
        updateList = csv.DictReader(args.input_file, fieldnames=['name','targetId','sourceId',"reason","force"])
        for perf in updateList:
            if perf['force'].lower() == "true":
                performerGetter = StashBoxPerformerManager(stash, TARGET, TARGET, siteMapper)
                performerGetter.getPerformer(perf['targetId'])
                if not performerGetter.hasOpenDrafts():
                    manualUpdatePerformer(stash, SOURCE, TARGET, performerGetter.performer, perf['sourceId'],args.comment)
                else:
                    print(f"Has Draft already {perf['name']}")
            else:
                print(f"Not updating {perf['name']}")


        args.input_file.close()
    
    elif args.m.lower() == "test":
        ip = get('https://api.ipify.org').content.decode('utf8')
        print('My public IP address is: {}'.format(ip))

    elif args.m.lower() == "updatecache":
        print("Cache Update mode - Updating Target cache")
        targetCacheMgr.loadCache(True, 24, 7)
        print("Cache Update mode - Updating Source cache")
        sourceCacheMgr.loadCache(True, 24, 7)