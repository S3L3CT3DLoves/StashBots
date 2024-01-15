# StashBox Performer Bot
This program is designed to help automate the creation and updating of Performers on StashBox instances.
It is designed to copy Performer info from one StashBox to another, to avoid having to maintain the information in both sources manually.

## Requirements
Make sure all required python libraries are installed
You must have a (running) Stash instance, with working credentials for the StashBox instances you want to connect to (StashDB, PMVStash, ...)
You must have BOT rights on TARGET

## Currently supported
PMVSTASH and STASHDB are currently implemented, FANSDB will be added soon

*Using STASHDB as a TARGET is not recommended, because it does not have a link type for PMVSTASH, which will prevent updating in the future.*

## Terms Used
- TARGET (-tsb) : StashBox instance where the performers will be created / updated
- SOURCE (-ssb) : StashBox instance where the performer data will be copied from (generally STASHDB)
- STASH (-s) : Your local Stash instance, used to get credentials for StashBoxes (and as a data source for Create mode)

## Usual commands

Create mode : `python .\PerfCrossUpload.py -m c -ssb STASHDB -tsb PMVSTASH -s http://localhost:9999/`
Update mode : `python .\PerfCrossUpload.py -m u -tsb PMVSTASH -ssb STASHDB -s http://localhost:9999/`

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