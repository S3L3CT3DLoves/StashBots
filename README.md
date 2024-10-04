# StashBox Performer Bot
This program is designed to help automate the creation and updating of Performers on StashBox instances.

It is designed to copy Performer info from one StashBox to another, to avoid having to maintain the information in both sources manually.

## Requirements
Make sure all required python libraries are installed

You must have a (running) Stash instance, with working credentials for the StashBox instances you want to connect to (StashDB, PMVStash, ...)

You must have BOT rights on TARGET

## Terms Used
- TARGET (-tsb) : StashBox instance where the performers will be created / updated
- SOURCE (-ssb) : StashBox instance where the performer data will be copied from (generally STASHDB)
- STASH (-s) : Your local Stash instance, used to get credentials for StashBoxes (and as a data source for Create mode)

## Usual commands

Create mode : `python .\StashBox-PerformerBot.py create -ssb STASHDB -tsb PMVSTASH -s http://localhost:9999/ -c "[PBOT] StashDB Scrape"`

Update mode : `python .\StashBox-PerformerBot.py update -sc -tsb PMVSTASH -ssb STASHDB -s http://localhost:9999/ -c "[PBOT] StashDB Update" -l 5 -o manualcheck_output.csv`

Manual mode : `python .\StashBox-PerformerBot.py manual -tsb PMVSTASH -ssb STASHDB -s http://localhost:9999/ -c "[PBOT] StashDB Update - Manually checked" -i manualcheck_output.csv`

---

# Modes
## Create Mode
In Create mode, the Bot will look at the list of performers in your local Stash instance and create new performer entries on TARGET based on that.

To make it work, the performers must be Tagged in Stash with the SOURCE.

The Bot will grab the information directly from SOURCE and copy it to TARGET.

==** Warning :** You are responsible for making sure the bot does not create duplicates ! Before running it, check that the performers in your Stash have all been tagged for TARGET !==

## Update Mode
In Update mode, the Bot will look at the list of all performers in TARGET, and attempt to update them based on SOURCE.

The Bot only updates data if all the following conditions are met:
- The performer in TARGET has a link to SOURCE
- The performer in TARGET was never changed manually (it is an exact copy of SOURCE at the time of creation)
- There are no ongoing Edits on the performer

## Manual Update Mode
In Manual Update mode, the Bot will take a list of performers from a CSV file (following the output format of Update mode).

For all lines in the file where the last element is True, it will force the update of the performer, even if Update mode has failed it.

This must only be used after a manual review of the list of performers has been done, to ensure no import data will be overwritten.

Because this operation can be destructive, it will not be send in BOT mode, and will show up a normal Edit in StashBox.


## Stats Mode
In Stats mode, the Bot will identify the number of performers that have No Links (at all), and how many have links to other StashBox instances.

## Links Mode
In Links mode, the Bot will compare the performer information in the TARGET with other StashBox instances, and add the link to the source if it exists.

This can be used to add StashDB links to performers that were scrapped from there, but the link to the source was not added.

*Support for FansDB is coming.*

# StashBox Cache
The bot features a full caching feature, to keep a local copy of all performers in a StashBox instance.

This is built to avoid overloading StashBox servers each time the bot runs.

The cache update can take a while, this is *by design*, downloading a full cache can take between 400 and 6000+ API calls. To avoid overloading the StashBox server, each API call is delayed by 5 seconds.

To speed things up, update your cache regularly (at least once a week), to benefit from the **refresh** feature. Which does not re-download all performers on the StahsBox server. It will grab all **Changes** (Edits) applied to performers since the last refresh, and apply them to the existing cache. This requires fewer API calls, making it a lot faster.

## Updating the cache
Updates are executed when you run **Update Mode**

If the cache has not been refreshed in the past 24h, it will update itself. If this value is too high, it can be changed in the code.

If the cache is less than 7 days old, the bot will not re-download all performers on the StahsBox server. It will grab all **Changes** (Edits) applied to performers since the last refresh, and apply them to the existing cache.