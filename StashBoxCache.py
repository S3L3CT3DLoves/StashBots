from datetime import datetime
import glob
import json
import re
from typing import List
import zlib
import schema_types as t

STRFTIMEFORMAT = "%Y-%m-%d-%H-%M"

class StashBoxCache:
    performers = []
    stashBoxInstance = ""
    cacheDate = datetime(2020,1,1,1,1,1)

    def __init__(self, stashBoxInstance : str) -> None:
        self.stashBoxInstance = stashBoxInstance
    
    def getCache(self) -> List[t.Performer]:
        return self.performers
    
    def loadCacheFromFile(self):
        globName = f"Cache/{self.stashBoxInstance}_performers_cache_*.json.zlib"
        earliest = datetime(2020,1,1,1,1,1)
        for name in glob.glob(globName):
            dateGrabber = re.compile(r".*performers_cache_(\d\d\d\d)-(\d\d)-(\d\d)-(\d\d)-(\d\d).json.zlib")
            dateStr = dateGrabber.match(name)
            fileDate = datetime(int(dateStr.group(1)), int(dateStr.group(2)), int(dateStr.group(3)), int(dateStr.group(4)), int(dateStr.group(5)))
            if fileDate > earliest:
                earliest = fileDate
        
        self.cacheDate = earliest
        if earliest == datetime(2020,1,1,1,1,1):
            # There is no cache file yet
            return
        
        dateCacheFile = earliest.strftime(STRFTIMEFORMAT)
        filename = f"Cache/{self.stashBoxInstance}_performers_cache_{dateCacheFile}.json.zlib"
        with open(filename, mode='rb') as cache:
            fileData = zlib.decompress(cache.read(), zlib.MAX_WBITS|32).decode()
            self.performers = json.loads(fileData)

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
        filename = f"Cache/{self.stashBoxInstance}_performers_cache_{dateNow}.json.zlib"
        print(f"Saving cache to file: {filename}")
        with open(filename, mode='wb') as file:
            encoded = json.dumps(self.performers).encode()
            compressed = zlib.compress(encoded)
            file.write(compressed)