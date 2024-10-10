from datetime import datetime
import glob
import json
import os
import re
import time
from typing import List
import zlib
from StashBoxHelperClasses import StashSource
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
    
    def getCache(self) -> List[t.Performer]:
        return self.performers
    
    def loadCacheFromFile(self):
        globName = f"{self.stashBoxInstance.name}_performers_cache_*.json.zlib"
        earliest = datetime(2020,1,1,1,1,1)
        toCleanup = []
        for name in glob.glob(globName):
            dateGrabber = re.compile(r".*performers_cache_(\d\d\d\d)-(\d\d)-(\d\d)-(\d\d)-(\d\d).json.zlib")
            dateStr = dateGrabber.match(name)
            fileDate = datetime(int(dateStr.group(1)), int(dateStr.group(2)), int(dateStr.group(3)), int(dateStr.group(4)), int(dateStr.group(5)))
            if fileDate > earliest:
                earliest = fileDate
            else:
                toCleanup.append(name)
        
        self.cacheDate = earliest
        if earliest == datetime(2020,1,1,1,1,1):
            # There is no cache file yet
            return
        
        dateCacheFile = earliest.strftime(STRFTIMEFORMAT)
        filename = f"{self.stashBoxInstance.name}_performers_cache_{dateCacheFile}.json.zlib"
        with open(filename, mode='rb') as cache:
            fileData = zlib.decompress(cache.read(), zlib.MAX_WBITS|32).decode()
            self.performers = json.loads(fileData)
        
        # Cleanup old cache files
        for filename in toCleanup:
            os.remove(filename)

        print(f"Cache contains {len(self.performers)} entries")

    def getPerformerById(self, performerId) -> t.Performer:
        result = None
        try:
            result = [perf for perf in self.performers if perf["id"] == performerId][0]
        except:
            pass
        return result
    
    def _getPerformerIdxById(self, performerId) -> t.Performer:
        result = None
        for idx, perf in enumerate(self.performers):
            if perf['id'] == performerId:
                return idx
        
        #result = [idx for idx, perf in enumerate(self.performers) if perf.id == performerId][0]
        return result
    
    def deletePerformerById(self, performerId : str):
        deletedIdx = self._getPerformerIdxById(performerId)
        del self.performers[deletedIdx]

    def saveCacheToFile(self):
        dateNow = datetime.now().strftime(STRFTIMEFORMAT)
        filename = f"{self.stashBoxInstance.name}_performers_cache_{dateNow}.json.zlib"
        print(f"Saving cache to file: {filename}")
        with open(filename, mode='wb') as file:
            encoded = json.dumps(self.performers).encode()
            compressed = zlib.compress(encoded)
            file.write(compressed)