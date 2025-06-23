# StashBox Performer Bot
This program is designed to help automate the updating of Performers on StashBox instances.

It is designed to copy Performer info from one StashBox to another, to avoid having to maintain the information in both sources manually.

*The newer versions (>=2.0) are no longer bound to a Stash instance, and will run autonomously using a config.ini file to provide the API key.*

## Requirements
Make sure all required python libraries are installed

You must have BOT rights on TARGET

You must configure the Bot with the config.ini file, give it the target endpoints and API keys. (an example file is provided, rename it to "config.ini" and add your config to it)

## Terms Used
- TARGET (-tsb) : StashBox instance where the performers will be created / updated
- SOURCE (-ssb) : StashBox instance where the performer data will be copied from (generally STASHDB)

## Usual commands

Update mode : `python .\StashBox-PerformerBot.py update -sc -tsb PMVSTASH -ssb STASHDB -c "[PBOT] StashDB Update" -l 5 -o manualcheck_output.csv`

Manual mode : `python .\StashBox-PerformerBot.py manual -tsb PMVSTASH -ssb STASHDB -c "[PBOT] StashDB Update - Manually checked" -i manualcheck_output.csv`

---

# Modes
## Update Mode
In Update mode, the Bot will look at the list of all performers in TARGET, and attempt to update them based on SOURCE.

The Bot only updates data if all the following conditions are met:
- The performer in TARGET has a link to SOURCE
- The performer in TARGET was never changed manually (it is an exact copy of SOURCE at the time of creation)
- There are no ongoing Edits on the performer

## Manual Update Mode
In Manual Update mode, the Bot will take a list of performers from a CSV file (following the output format of Update mode).

For all lines in the file where the last element is True, it will force the update of the performer, even if Update mode has failed it.

**This must only be used after a manual review of the list of performers has been done, to ensure only identical performers have the True flag.**

Because this operation can be destructive, it will not be sent in BOT mode, and will show as a normal Edit in StashBox.

Newer versions of the code have the additional features:
- Images that were manually added to the Target will not be removed
- Terminal mode has been introduced

### Terminal Mode
This is an advanced mode of Manual Update.

A text comparison will be shown in the Terminal for review by the user. If the user confirms it, the performer will be considered as identical, and the update will be sent.

This only applies for lines in the CSV file which do not have the True flag, and where images are identical.


# StashBox Cache
The bot features a full caching feature, to keep a local copy of all performers in a StashBox instance.

This is built to avoid overloading StashBox servers each time the bot runs.

The cache update can take a while, this is *by design*, downloading a full cache can take between 400 and 6000+ API calls. To avoid overloading the StashBox server, each API call is delayed by 5 seconds.

To speed things up, update your cache regularly (at least once a week), to benefit from the **refresh** feature. Which does not re-download all performers on the StahsBox server. It will grab all **Changes** (Edits) applied to performers since the last refresh, and apply them to the existing cache. This requires fewer API calls, making it a lot faster.

*Newer versions of the bot use a compressed file to save the cache, to reduce storage requirements. Running the bot after the update may require a full re-download of the cache.*

## Updating the cache
Updates are executed when you run **Update Mode**

If the cache has not been refreshed in the past 24h, it will update itself. If this value is too high, it can be changed in the code.

If the cache is less than 7 days old, the bot will not re-download all performers on the StahsBox server. It will grab all **Changes** (Edits) applied to performers since the last refresh, and apply them to the existing cache.


## Past features
Support for Stats, Links and Create mode have been removed. If you are interested in them, they are in the Github history.