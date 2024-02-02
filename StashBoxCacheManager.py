from datetime import datetime, timedelta
import glob
import json
import re
from StashBoxWrapper import StashBoxPerformerHistory, StashSource, getAllEdits, getAllPerformers, stashDateToDateTime
import schema_types as t

STRFTIMEFORMAT = "%Y-%m-%d-%H-%M"

class StashBoxCache:
    performers = []
    stashBoxInstance = ""
    stashBoxConnectionParams = {}
    cacheDate = datetime(2020,1,1,1,1,1)

    def __init__(self, stashBoxConnection : dict, stashBoxInstance : StashSource) -> None:
        self.stashBoxConnectionParams = stashBoxConnection
        self.stashBoxInstance = stashBoxInstance
    
    def getCache(self) -> [t.Performer]:
        return self.performers
    
    def loadCacheFromFile(self):
        globName = f"{self.stashBoxInstance.name}_performers_cache_*.json"
        earliest = datetime(2020,1,1,1,1,1)
        for name in glob.glob(globName):
            dateGrabber = re.compile(".*performers_cache_(\d\d\d\d)-(\d\d)-(\d\d)-(\d\d)-(\d\d).json")
            dateStr = dateGrabber.match(name)
            fileDate = datetime(int(dateStr.group(1)), int(dateStr.group(2)), int(dateStr.group(3)), int(dateStr.group(4)), int(dateStr.group(5)))
            if fileDate > earliest:
                earliest = fileDate
        
        self.cacheDate = earliest
        dateCacheFile = earliest.strftime(STRFTIMEFORMAT)
        filename = f"{self.stashBoxInstance.name}_performers_cache_{dateCacheFile}.json"
        with open(filename, mode='r') as cache:
            self.performers = json.load(cache)

    def loadCacheFromStashBox(self) -> [t.Performer]:
        self.performers = getAllPerformers(self.stashBoxConnectionParams)
        self.cacheDate = datetime.now()
        return self.performers
    
    def getPerformerById(self, performerId) -> t.Performer:
        result = None
        try:
            result = [perf for perf in self.performers if perf.id == performerId][0]
        except:
            pass
        return result
    
    def _getPerformerIdxById(self, performerId) -> t.Performer:
        result = None
        try:
            result = [idx for idx, perf in enumerate(self.performers) if perf.id == performerId][0]
        except:
            pass
        return result
    
    def addPerformer(self, performer : t.Performer):
        self.performers.append(performer)

    def deletePerformerById(self, performerId : str):
        deletedIdx = self._getPerformerIdxById(performerId)
        del self.performers[deletedIdx]

    def updatePerformer(self, performerId : str, editDetails : t.PerformerEdit):
        performerIdx = self._getPerformerIdxById(performerId)
        self.performers[performerIdx] = StashBoxPerformerHistory.applyPerformerUpdate(self.performers[performerIdx], editDetails)

    def saveCacheToFile(self):
        dateNow = datetime.now().strftime(STRFTIMEFORMAT)
        filename = f"{self.stashBoxInstance.name}_performers_cache_{dateNow}.json"
        with open(filename, mode='w') as file:
            json.dump(self.performers, file)

class StashBoxCacheManager:
    cache : StashBoxCache
    saveToFile = True

    def __init__(self, stashBoxConnection : dict, stashBoxInstance : StashSource, saveToFile = True) -> None:
        self.cache = StashBoxCache(stashBoxConnection, stashBoxInstance)
        self.saveToFile = saveToFile
    
    def loadCache(self, useFile = True, limitHours = 24, refreshLimitDays = 7):
        if useFile:
            self.cache.loadCacheFromFile()
            self.updateCache(limitHours, refreshLimitDays)
        else:
            self.cache.loadCacheFromStashBox()

    def updateCache(self, limitHours = 24, refreshLimitDays = 7):
        dateLimit = datetime.now() - timedelta(hours=limitHours)
        dateRefreshLimit = datetime.now() - timedelta(days=refreshLimitDays)

        if self.cache.cacheDate >= dateLimit:
            # Cache is ready up to date
            return
        
        if self.cache.cacheDate < dateRefreshLimit:
            # Cache is too old to refresh, do a full reload
            print("Existing cache file is too old, grabbing a brand new one")
            self.cache.loadCacheFromStashBox()
            if self.saveToFile:
                self.saveCache()
            return
        
        # Cache can be refreshed, load all the recent Edits and apply them
        print("Existing cache file is outdated, updating it with latest changes")
        allEdits = getAllEdits(self.cache.stashBoxConnectionParams, refreshLimitDays)
        allEditsFiltered = list(filter(lambda edit: stashDateToDateTime(edit["closed"]) >= self.cache.cacheDate, allEdits))
        print(f"{len(allEditsFiltered)} changes to process")

        for edit in allEditsFiltered:
            targetPerformerId = edit["target"]["id"]
            print(f"{edit['operation']} on {targetPerformerId}")

            if edit["operation"] == "CREATE":
                self.cache.addPerformer(edit["target"])
            elif edit["operation"] == "DESTROY":
                self.cache.deletePerformerById(targetPerformerId)
            elif edit["operation"] == "MODIFY":
                self.cache.updatePerformer(targetPerformerId, edit["details"])
            elif edit["operation"] == "MERGE":
                mergedIds = list(map( lambda source: source["id"] ,edit["merge_sources"]))
                print(f"Merging {mergedIds}")
                self.cache.updatePerformer(targetPerformerId, edit["details"])
                for id in mergedIds:
                    self.cache.deletePerformerById(id)
        
        if self.saveToFile:
            self.saveCache()

    def saveCache(self):
        self.cache.saveCacheToFile()
