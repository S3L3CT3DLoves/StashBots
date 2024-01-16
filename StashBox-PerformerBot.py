from datetime import datetime
import json, os, re, sys, argparse
import schema_types as t
from StashBoxWrapper import PerformerUploadConfig, StashBoxFilterManager, StashBoxPerformerHistory, StashSource, StashBoxSitesMapper, StashBoxPerformerManager, convertCountry, getAllPerformers, stashDateToDateTime, getImgB64
from stashapi.stashapp import StashInterface


siteMapper = StashBoxSitesMapper()

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

        print(f"Performer Edit submitted : {siteMapper.SOURCE_INFOS[destination]['url']}/edits/{submitted['id']}")

def updatePerformer(stash : StashInterface, source : StashSource, destination : StashSource, performer : t.Performer, comment : str):
    sourceUrl = [url for url in performer['urls'] if url['url'].startswith(StashBoxSitesMapper.SOURCE_INFOS[source]['url'])][0]['url']
    sourceId = sourceUrl.split('/').pop()
    lastUpdate = stashDateToDateTime(performer["updated"])
    sourcePerformerHistory = StashBoxPerformerHistory(stash.get_stashbox_connection(StashBoxSitesMapper.SOURCE_INFOS[source]['url']), sourceId)
    perfManager = StashBoxPerformerManager(stash, source, destination)
    perfManager.setPerformer(sourcePerformerHistory.performer)

    if perfManager.hasOpenDrafts(performer, stash.get_stashbox_connection(StashBoxSitesMapper.SOURCE_INFOS[destination]['url'])):
        print(f"Skipping {performer['name']} - has Open Drafts")
        return False

    #Bugfix for non-iso country names
    performer["country"] = convertCountry(performer.get("country"))

    hasUpdate = sourcePerformerHistory.hasUpdate(lastUpdate)
    incomplete = sourcePerformerHistory.isIncomplete(lastUpdate, performer)
    if (hasUpdate or incomplete) and sourcePerformerHistory.compareAtDateTime(lastUpdate, performer):
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
        return True
    else:
        print(f"Not updating {performer['name']}")
    
    return False

def getPerformerUploadsFromStash(stash : StashInterface, source : StashSource, destination : StashSource) -> [PerformerUploadConfig]:
    sourceEndpointUrl = f"{StashBoxSitesMapper.SOURCE_INFOS[source]['url']}/graphql"
    destinationEndpointUrl = f"{StashBoxSitesMapper.SOURCE_INFOS[destination]['url']}/graphql"

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


def savePerformerData(file,data):
    first = True
    for performer in data:
        com = ','
        if(first and file.tell() < 100):
            com=''
            first = False

        print(f"{com} {json.dumps(performer)}", file=file)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog="StashBox Performer Manager",
        description="""CLI tool to allow management of StashBox performers\n
        Creation mode : lists Performers from your local Stash instance which have a link to SOURCE but not to TARGET, and creates the performer in TARGET\n
        Update mode : lists all Performers on TARGET that have a link to SOURCE, and updates them to mirror changes in SOURCE""",
        epilog="__StashBox_Perf_Mgr_v0.2__"
    )
    parser.add_argument("-m", help="Options: c - CREATE / u - UPDATE", choices=['create', 'update'], required=True)
    parser.add_argument("-s", "--stash", help="Local Stash url to be used to get the Stashbox config", default="http://localhost:9999/")
    parser.add_argument("-tsb", "--target-stashbox", help="Target StashBox instance", choices=['STASHDB', 'PMVSTASH', "FANSDB"], required=True)
    parser.add_argument("-ssb", "--source-stashbox", help="Source StashBox instance", choices=['STASHDB', 'PMVSTASH', "FANSDB"], required=True)
    parser.add_argument("-c", "--comment", help="Comment for StashBox Edits", default="[BOT] StashBox-PerformerBot Edit")
    parser.add_argument("-l", "--limit", help="Maximum number of edits allowed (Update mode only)", type=int, default=100000)

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

    count = 0

    if args.m.lower() == "update":
        print("Update mode")
        # Update mode
        performersList = []
        date = datetime.now().strftime("%Y-%m-%d")
        filename = f"{args.target_stashbox}_performers_cache_{date}.json"
        print(filename)
        if not os.path.exists(filename):
            print("Downloading the local cache, this could take some time")
            with open(filename, mode='w') as file:
                file.write('{ "performers" : [')

                getAllPerformers(stash.get_stashbox_connection(StashBoxSitesMapper.SOURCE_INFOS[TARGET]['url']), lambda x: savePerformerData(file, x))

                file.write("]}")
        
        with open(filename, mode='r') as cache:
            print("Using local cache")
            performersList = json.load(cache)['performers']
            performersList = list(filter(
                lambda performer: [url for url in performer['urls'] if url['url'].startswith(StashBoxSitesMapper.SOURCE_INFOS[SOURCE]['url'])] != []
                ,performersList
            ))
            print(len(performersList))
        
        #Now actually do the update
        plist = list(reversed(performersList))
        for performer in plist:
            if updatePerformer(stash, SOURCE, TARGET, performer, args.comment):
                count += 1
            
            if count >= args.limit:
                print(f"{count} performers updated")
                sys.exit()
        
        print(f"{count} performers updated")

    elif args.m.lower() == "create":
        print("Creation mode")
        createPerformers(stash, SOURCE, TARGET, getPerformerUploadsFromStash(stash), args.comment)
    

