import argparse
import configparser
import csv
import sys
import time
from datetime import datetime
from enum import Enum
from typing import List

from tabulate import tabulate

import schema_types as t
from StashBoxCache import StashBoxCache
from StashBoxHelperClasses import StashSource, normalise_url
from StashBoxWrapper import (
    ComparisonReturnCode,
    StashBoxCacheManager,
    StashBoxPerformerHistory,
    StashBoxPerformerManager,
    StashBoxSitesMapper,
    comparePerformers,
    convertCountry,
    getOpenEdits,
    stashDateToDateTime,
)

SITEMAPPER = StashBoxSitesMapper()


class ReturnCode(Enum):
    '''Aliases for the performer update return codes'''
    SUCCESS = 1
    HAS_DRAFT = 0
    NO_NEED = -1
    DIFF = -2
    DIFF_IMG = -3
    ERROR = -99


def concat_urls(destination: StashSource, existing_urls: list[t.URL], new_urls: list[t.URL]) -> list[t.URL]:
    """Returns a concatenated list of urls ready to send to StashBox

    Args:
        destination (StashSource): To avoid adding links that point to itself
        existingUrls (list[t.URL]): Existing links, to keep them, and avoid creating duplicates
        newUrls (list[t.URL]): Links to be added

    Returns:
        list[t.URL]: Concatenation of the two lists, without duplicates, empty items, or self-references
    """
    future_urls = list(
        map(lambda x: {'site_id': x["site"]["id"], "url": x["url"]}, existing_urls))
    normalised_existing_urls = list(
        map(lambda x: normalise_url(x["url"]), existing_urls))

    for url_data in new_urls:
        normalised_url = normalise_url(url_data["url"])
        if normalised_url not in normalised_existing_urls:
            future_urls.append(url_data)
            normalised_existing_urls.append(normalised_url)

    # Remove any empty urls, and any circular references
    future_urls = list(filter(
        lambda url: url != {} and not SITEMAPPER.is_link_to_instance(
            url["url"], destination),
        future_urls
    ))

    return future_urls


def update_performer(source_endpoint, destination_endpoint, target_performer: t.Performer, comment: str, output_filestream=None, cache: StashBoxCache = None) -> ReturnCode:
    '''
    Updates target_performer in destination_endpoint with the data from source_endpoint.
        target_performer must be sourced from destination_endpoint
        target_performer must have a url link to the source_endpoint

        comment is directly sent to the destination_endpoint as the Edit comment
        output_filestream allows error messages to be sent to a file, for later processing with *manual* mode
    '''
    source_url = [url for url in target_performer['urls'] if SITEMAPPER.is_link_to_instance(
        url['url'], source_endpoint['name'])][0]['url']
    source_id = source_url.split('/').pop()
    latest_update_date = stashDateToDateTime(target_performer["updated"])

    try:
        source_performer_history = StashBoxPerformerHistory(
            source_endpoint, source_id, cache, SITEMAPPER)
    except Exception:
        print(f"{target_performer['name']} --- Error while processing --- !!!")
        print(
            f"{target_performer['name']},{target_performer['id']},{source_id},ERROR,False", file=output_filestream)
        return ReturnCode.ERROR
    performer_manager = StashBoxPerformerManager(
        source_endpoint, destination_endpoint, cache=cache, sitesMapper=SITEMAPPER)
    performer_manager.setPerformer(source_performer_history.performer)

    # Bugfix for non-iso country names
    if target_performer.get("country"):
        target_performer["country"] = convertCountry(
            target_performer.get("country"))

    has_update = source_performer_history.hasUpdate(latest_update_date)
    incomplete = source_performer_history.isIncomplete(
        latest_update_date, target_performer)

    if (has_update or incomplete):
        # Only update if the current info of Performer is identical to the past info in SOURCE (avoid overwritting manually changed info)
        compare = source_performer_history.compareAtDateTime(
            latest_update_date, target_performer)
        if compare in ([ComparisonReturnCode.IDENTICAL], [ComparisonReturnCode.images]):
            # Check that there is actually a change to push
            if source_performer_history.compareAtDateTime(datetime.now(), target_performer) != [ComparisonReturnCode.IDENTICAL]:
                print(
                    f"Ready to update {target_performer['name']} : Performer {'/ has Update' if has_update else ''} {'/ is incomplete' if incomplete else ''}")

                update_input = performer_manager.asPerformerEditDetailsInput()
                update_input["urls"] = concat_urls(
                    destination_endpoint['name'], target_performer["urls"], update_input["urls"])

                print("Uploading new images")
                update_input["image_ids"] = performer_manager.uploadPerformerImages(existing=target_performer.get(
                    "images", []), removed=source_performer_history.removedImages)

                try:
                    performer_manager.submitPerformerUpdate(
                        target_performer["id"], update_input, comment)
                    return ReturnCode.SUCCESS
                except Exception as e:
                    print("Error updating performer")
                    print(e)
                    return ReturnCode.ERROR
            else:
                return ReturnCode.DIFF

        if output_filestream is not None:
            differences = ";".join(map(lambda x: x.name, compare))
            print(
                f"{target_performer['name']},{target_performer['id']},{performer_manager.performer['id']},{differences},False", file=output_filestream)
        return ReturnCode.DIFF
    return ReturnCode.NO_NEED


def manual_update_performer(source_endpoint, destination_endpoint, target_performer: t.Performer, source_id: str, comment: str, cache: StashBoxCache = None, bot=False):
    '''
    ### Summary
    Force update of a Performer based on the source and sourceId, not performing any checks.
    Explicitely designed to NOT remove images unless those were removed from Source.
    Explicitely designed to ONLY ADD aliases, removals must be handled manually to avoid data loss.
    '''

    print(f"Ready to update {target_performer['name']}")

    source_performer_manager = StashBoxPerformerManager(
        source_endpoint, destination_endpoint, SITEMAPPER, cache=cache)
    source_performer_manager.getPerformer(source_id)
    try:
        source_performer_history = StashBoxPerformerHistory(
            source_endpoint, source_id, cache, SITEMAPPER)
    except Exception:
        print(f"{target_performer['name']} --- Error while retrieving SOURCE history --- !!!")
        return ReturnCode.ERROR

    draft = source_performer_manager.asPerformerEditDetailsInput()

    # Add url to source, in case it's not there yet
    draft["urls"].append({
        "url": f"{SITEMAPPER.SOURCE_INFOS[StashSource[source_endpoint['name']]]['url']}performers/{source_performer_manager.performer['id']}",
        "site_id": SITEMAPPER.SOURCE_INFOS[StashSource[destination_endpoint['name']]]['siteIds'][StashSource[source_endpoint['name']]]
    })
    draft["urls"] = concat_urls(destination_endpoint['name'], target_performer["urls"], draft["urls"])

    # Only perform ADD on aliases, too many differences in the guidelines, was causing issues
    draft["aliases"] = target_performer["aliases"]
    for alias in source_performer_manager.performer['aliases']:
        if alias not in draft["aliases"]:
            draft['aliases'].append(alias)

    try:
        new_images = source_performer_manager.uploadPerformerImages(
            existing=target_performer.get("images", []), removed=source_performer_history.removedImages)
        draft["image_ids"] = new_images
        source_performer_manager.submitPerformerUpdate(target_performer["id"], draft, comment, bot)
    except Exception as e:
        print("Error processing performer")
        print(e)

    print(f"{target_performer['name']} updated")


def filter_performers_for_update(performer_list: List[t.Performer], source_endpoint, target_endpoint, verbose=False) -> List[t.Performer]:
    '''
    Filters a list of performers to remove those that:
    - already have open Edits
    - don't have a link to the source
    - have links to more than one StashBox instances (not supported, can't chose one over another)

    Also allows reporting of the number of performers excluded for each reason in verbose mode.
    '''

    new_list = []
    open_edits = getOpenEdits(target_endpoint)
    performers_with_open_edits = list(map(
        lambda edit: edit["target"]["id"],
        filter(
            lambda edit: edit["operation"] in ["MODIFY", "DESTROY"],
            open_edits
        )
    ))

    # Variables for stats
    multi_link = 0
    have_link = 0
    skip_edit = 0

    for each_performer in performer_list:
        if each_performer.get("urls"):
            if each_performer["deleted"]:
                # Performer is deleted, skip
                continue

            if each_performer["id"] in performers_with_open_edits:
                # Performer has an open Edit, skip
                skip_edit += 1
                continue

            if [url for url in each_performer['urls'] if SITEMAPPER.is_link_to_instance(url['url'], source_endpoint['name'])] == []:
                # Performer has no link to source
                continue
            have_link += 1

            counter = 0
            for url in [url["url"] for url in each_performer["urls"]]:
                if SITEMAPPER.whichStashBoxLink(url) is not None:
                    counter += 1

            if counter > 1:
                # Performer has more than one StashBox link, for now this is not supported
                multi_link += 1
                continue

            new_list.append(each_performer)

    if verbose:
        print(
            f"There are {have_link} performers with Links to {source_endpoint['name']}")
        print(
            f"Skipping {multi_link} performers due to multiple StashBox Links")
        print(f"Skipping {skip_edit} performers ongoing edits")
        print(f"Filtered : {len(new_list)}")
    return new_list


def console_confirm_performer_comparison(target_performer, source_performer):
    '''
    Creates a comparison table, then prints it to the console and requests the user to confirm if the performers are identical.
    '''
    comparison = comparePerformers(source_performer, target_performer)
    if comparison == [ComparisonReturnCode.IDENTICAL]:
        # Happens sometimes, due to diff between comparePerformers and compareAtDateTime
        return True

    comparison_table = []
    for attr in "name", "gender", "ethnicity", "country":
        attr_title = attr
        if ComparisonReturnCode[attr] in comparison:
            attr_title = "[*]" + attr_title
        comparison_table.append(
            [attr_title, target_performer.get(attr), source_performer.get(attr)])

    bday_title = "bday"
    if ComparisonReturnCode.birth_date in comparison:
        bday_title = "[*]" + bday_title
    comparison_table.append([bday_title, target_performer.get("birth_date", target_performer.get(
        "birthdate")), source_performer.get("birth_date", source_performer.get("birthdate"))])

    for attr in "aliases", "disambiguation", "breast_type", "cup_size", "band_size", "waist_size", "eye_color", "hair_color", "height", "hip_size", "career_start_year", "career_end_year":
        attr_title = attr
        if ComparisonReturnCode[attr] in comparison:
            attr_title = "[*]" + attr_title
        comparison_table.append(
            [attr_title, target_performer.get(attr), source_performer.get(attr)])

    print(tabulate(comparison_table, headers=['Attr', 'Target', 'Source']))
    try:
        user_return = input("Are these the same performer? (y/N) ")
        return user_return.lower() == "y"
    except KeyboardInterrupt:
        print("Exiting")
        sys.exit(0)
    except Exception as e:
        raise e


def add_stashbox_link_to_performer(source_endpoint, destination_endpoint, target_performer: t.Performer, source_id: str, comment: str):
    '''
    Adds a StashBox link to an existing performer
    '''

    performer_namager = StashBoxPerformerManager(
        source_endpoint, destination_endpoint, SITEMAPPER)
    performer_namager.setPerformer(target_performer)
    draft = performer_namager.asPerformerEditDetailsInput()

    # Keep existing links to avoid removing data
    existing_urls = list(map(lambda x: {
        'site_id': x["site"]["id"] if "site" in x else x["site_id"],
        "url": x["url"]
    }, draft["urls"]))

    # Add url
    existing_urls.append({
        "url": f"{SITEMAPPER.SOURCE_INFOS[StashSource[source_endpoint['name']]]['url']}performers/{source_id}",
        "site_id": SITEMAPPER.SOURCE_INFOS[StashSource[destination_endpoint['name']]]['siteIds'][StashSource[source_endpoint['name']]]
    })

    # Call concatenateUrls, just to make sure we don't add duplicates (can cause Failed updates)
    draft["urls"] = concat_urls(destination_endpoint['name'], [], existing_urls)

    try:
        performer_namager.submitPerformerUpdate(
            target_performer["id"], draft, comment, False)
        print(f"{target_performer['name']} updated")
    except Exception as e:
        print(f"Error processing performer {target_performer['name']}")
        raise e


def configure_argparse():
    '''
    Configures the command line options. Very verbose so it moved to it's own function to keep the main lean.
    '''
    parser = argparse.ArgumentParser(
        prog="StashBox Performer Manager",
        description="""CLI tool to allow management of StashBox performers\n
        Update mode : lists all Performers on TARGET that have a link to SOURCE, and updates them to mirror changes in SOURCE\n
        Manual mode: takes an input CSV file to force update performers, even if they would not be updated through Update mode (unless is has a Draft already)
        """,
        epilog="__StashBox_Perf_Mgr_v2.1__"
    )
    subparsers = parser.add_subparsers()

    general_parser = argparse.ArgumentParser(add_help=False)
    general_parser.add_argument(
        "-c", "--comment", help="Comment for StashBox Edits", default="[BOT] StashBox-PerformerBot Edit")
    general_parser.add_argument("-tsb", "--target-stashbox", help="Target StashBox instance",
                               choices=['STASHDB', 'PMVSTASH', "FANSDB"], required=True)
    general_parser.add_argument("-ssb", "--source-stashbox", help="Source StashBox instance",
                               choices=['STASHDB', 'PMVSTASH', "FANSDB"], required=True)

    update_parser = subparsers.add_parser(
        "update", parents=[general_parser], help="")
    update_parser.add_argument("-o", "--output", help="Output file to list not-updated performers",
                              type=argparse.FileType('w+', encoding='UTF-8'))
    update_parser.add_argument(
        "-l", "--limit", help="Maximum number of edits allowed", type=int, default=100000)
    update_parser.add_argument(
        "-sc", "--source-cache", help="Use a local cache for Source StashBox", action="store_true")

    manual_parser = subparsers.add_parser(
        "manual", parents=[general_parser], help="")
    manual_parser.add_argument("-i", "--input-file", help="Input csv file containing the performers to be updated",
                              type=argparse.FileType('r', encoding='UTF-8'))

    links_parser = subparsers.add_parser(
        "links", parents=[general_parser], help="")
    links_parser.add_argument(
        "-l", "--limit", help="Maximum number of edits allowed", type=int, default=10)
    links_parser.add_argument("-m", "--mode", help="Mode",
                             choices=['NOLINKS', 'NOSTASHBOX', 'ALL'], default="NOLINKS")
    links_parser.add_argument("-s", "--save-file", help="File where the false positives are saved to avoid repeating next run", type=argparse.FileType('r+', encoding='UTF-8'), required=True)
    links_parser.add_argument(
        "-e", "--exact", help="Only use exact matches", action="store_true")
    links_parser.add_argument(
        "-sk", "--skip", help="Skip X% of the DB", type=int, default=0)

    return parser


def read_config_file():
    '''
    Reads the configuration from config.ini
    '''
    config_parser = configparser.ConfigParser()
    config_parser.read('config.ini')

    config_values = {}

    for each_section in config_parser.sections():
        if each_section == "GENERAL":
            config_values["STASH"] = config_parser.get(
                each_section, 'stash_url')
        else:
            config_values[each_section] = {
                "name": each_section,
                "endpoint": config_parser.get(each_section, 'api_url'),
                "api_key": config_parser.get(each_section, 'api_key')
            }

    return config_values


if __name__ == '__main__':
    argument_parser = configure_argparse()
    argv = sys.argv
    argv.pop(0)
    args = argument_parser.parse_args(argv)
    config = read_config_file()

    SOURCE_ENDPOINT = config[args.source_stashbox]
    TARGET_ENDPOINT = config[args.target_stashbox]

    SITEMAPPER.SOURCE = StashSource[SOURCE_ENDPOINT['name']]
    SITEMAPPER.DESTINATION = StashSource[TARGET_ENDPOINT['name']]
    SITEMAPPER.getSitesFromDestinationServer(TARGET_ENDPOINT)

    target_cache_manager = StashBoxCacheManager(TARGET_ENDPOINT, True)

    if sys.argv[0].lower() == "update":
        print("Update mode")
        COUNT = 0
        performers_list = []

        print("Using local cache for TARGET (always on)")
        target_cache_manager.loadCache(True, 12, 7)
        source_cache_manager = StashBoxCacheManager(
            SOURCE_ENDPOINT,  True) if args.source_cache else None
        if source_cache_manager is not None:
            print("Using local cache for SOURCE")
            source_cache_manager.loadCache(True, 24, 14)

        print("Parsing list of performers to update")
        performers_list = filter_performers_for_update(
            target_cache_manager.cache.getCache(), SOURCE_ENDPOINT, TARGET_ENDPOINT)
        print(f"There are {len(performers_list)} to review")

        # Now actually do the update
        clean_performer_list = list(reversed(performers_list))
        for performer in clean_performer_list:
            status = update_performer(SOURCE_ENDPOINT, TARGET_ENDPOINT, performer, args.comment,
                                      args.output, cache=source_cache_manager.cache if source_cache_manager is not None else None)
            if status == ReturnCode.SUCCESS:
                COUNT += 1
                print(f"{performer['name']} updated")
            else:
                if status == ReturnCode.HAS_DRAFT:
                    print(f"{performer['name']} not updated - DRAFT exists")
                elif status == ReturnCode.NO_NEED:
                    print(
                        f"{performer['name']} not updated - no update required")
                elif status == ReturnCode.DIFF:
                    print(
                        f"{performer['name']} not updated - manual change was made")
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
        updateList = csv.DictReader(args.input_file, fieldnames=[
                                    'name', 'targetId', 'sourceId', "reason", "force"])
        openEdits = getOpenEdits(TARGET_ENDPOINT)
        performersWithOpenEdits = list(map(
            lambda edit: edit["target"]["id"],
            filter(
                lambda edit: edit["operation"] in ["MODIFY", "DESTROY"],
                openEdits
            )
        ))
        for perf in updateList:
            if perf["targetId"] in performersWithOpenEdits:
                print(f"Has Draft already {perf['name']}")
                continue
            if perf["force"] is not None and perf['force'].lower() == "true":
                performerGetter = StashBoxPerformerManager(
                    TARGET_ENDPOINT, None, SITEMAPPER)
                performerGetter.getPerformer(perf['targetId'])
                manual_update_performer(SOURCE_ENDPOINT, TARGET_ENDPOINT,
                                      performerGetter.performer, perf['sourceId'], args.comment, bot=False)
            else:
                print(f"Not updating {perf['name']}")

        args.input_file.close()

    elif sys.argv[0].lower() == "links":
        target_cache_manager.loadCache(True, 12, 2)
        source_cache_manager = StashBoxCacheManager(SOURCE_ENDPOINT, True)
        source_cache_manager.loadCache(True, 48, 7)

        openEdits = getOpenEdits(TARGET_ENDPOINT)
        performersWithOpenEdits = list(map(
            lambda edit: edit["target"]["id"],
            filter(
                lambda edit: edit["operation"] in ["MODIFY", "DESTROY"],
                openEdits
            )
        ))

        noLinks = []
        noStashBox = []
        for performer in target_cache_manager.cache.getCache():
            if performer["id"] in performersWithOpenEdits:
                # Don't edit performers with ongoing changes, to avoid conflicts
                continue
            if performer["deleted"]:
                # Performer is deleted, skip
                continue
            if performer.get("urls"):
                stashBoxUrls = [url for url in performer['urls']
                                if SITEMAPPER.whichStashBoxLink(url["url"]) is not None]
                if stashBoxUrls != []:
                    continue
                noStashBox.append(performer)
            else:
                noLinks.append(performer)

        matches = []
        partialMatches = []

        print(
            f"There are {len(source_cache_manager.cache.getCache())} performers in the source")
        i = 0
        start = time.time()
        print(
            f"Mode = {args.mode} // Limit = {args.limit} (Skip {args.skip}%) // Exact = {args.exact}")
        if args.mode == "ALL" or args.mode == "NOLINKS":
            print(
                f"There are {len(noLinks)} performers with no links in the target")
        if args.mode == "ALL" or args.mode == "NOSTASHBOX":
            print(
                f"There are {len(noStashBox)} performers with no links to the source in the target")

        previous_decisions_reader = list(csv.DictReader(args.save_file, fieldnames=[
                                            'targetId', 'sourceId']))
        decision_writer = csv.DictWriter(args.save_file, fieldnames=[
                                        'targetId', 'sourceId'])

        try:
            for performerA in source_cache_manager.cache.getCache():
                if len(matches) >= args.limit:
                    break

                # Display progress
                if i % 1000 == 0:
                    print(
                        f"Searching... {i / len(source_cache_manager.cache.getCache()):.2%} in {time.time()-start:.2f}s")

                # Skip X% of the DB, to save time when using a low limit and calling the function several times
                if i*100 / len(source_cache_manager.cache.getCache()) < args.skip:
                    i = i + 1
                    continue

                if args.mode == "ALL" or args.mode == "NOSTASHBOX":
                    for performerB in noStashBox:
                        if performerB.get("name").lower() == performerA.get("name").lower():
                            comp = comparePerformers(performerA, performerB)
                            if comp == [ComparisonReturnCode.IDENTICAL]:
                                print(f"Found {performerB["name"]} in noStashBox")
                                matches.append(
                                    (performerA.get("id"), performerB.get("id")))
                            elif not args.exact and ComparisonReturnCode.gender not in comp:
                                in_save_file = [record for record in previous_decisions_reader if (record["targetId"] == performerB["id"] or record["targetId"] == "*") and (record["sourceId"] == performerA["id"] or record["sourceId"]=="*")]
                                if len(in_save_file) == 0:
                                    if console_confirm_performer_comparison(performerB, performerA):
                                        matches.append(
                                            (performerA.get("id"), performerB.get("id")))
                                    else:
                                        decision_writer.writerow({"targetId": performerB["id"], "sourceId": performerA["id"]})
                        else:
                            # for now only name matches are supported
                            continue

                if args.mode == "ALL" or args.mode == "NOLINKS":
                    for performerB in noLinks:
                        if performerB.get("name").lower() == performerA.get("name").lower():
                            comp = comparePerformers(performerA, performerB)
                            if comp == [ComparisonReturnCode.IDENTICAL]:
                                print(f"Found {performerB["name"]} in noLinks")
                                matches.append(
                                    (performerA.get("id"), performerB.get("id")))
                            elif not args.exact and ComparisonReturnCode.gender not in comp:
                                in_save_file = [record for record in previous_decisions_reader if (record["targetId"] == performerB["id"] or record["targetId"] == "*") and (record["sourceId"] == performerA["id"] or record["sourceId"]=="*")]
                                if len(in_save_file) == 0:
                                    if console_confirm_performer_comparison(performerB, performerA):
                                        matches.append(
                                            (performerA.get("id"), performerB.get("id")))
                                    else:
                                        decision_writer.writerow({"targetId": performerB["id"], "sourceId": performerA["id"]})
                        else:
                            # for now only name matches are supported
                            continue
                i = i + 1

            if len(matches) > 0:
                UP_COUNT = 0
                print(f"Found {len(matches)} matches to upload")
                if UP_COUNT < args.limit:
                    for sourcePerf, targetPerf in matches:
                        add_stashbox_link_to_performer(SOURCE_ENDPOINT, TARGET_ENDPOINT,
                                            target_cache_manager.cache.getPerformerById(targetPerf), sourcePerf, args.comment)
                        UP_COUNT = UP_COUNT + 1
                args.save_file.close()
                sys.exit(0)
        except KeyboardInterrupt:
            args.save_file.close()
