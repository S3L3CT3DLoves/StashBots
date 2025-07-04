import math, time, bisect, re, base64
from copy import deepcopy
from datetime import  datetime, timedelta
from enum import Enum
from typing import Dict, List
from stashapi.classes import serialize_dict
from StashBoxCache import StashBoxCache
from StashBoxHelperClasses import PerformerUploadConfig, StashSource
import schema_types as t
import requests
from urllib3 import encode_multipart_formdata
import pycountry
import StashBoxWrapperGQLQueries as GQLQ


class ComparisonReturnCode(Enum):
    IDENTICAL       = 1
    gender          = -1
    ethnicity       = -2
    country         = -3
    eye_color       = -4
    hair_color      = -5
    height          = -6
    cup_size        = -7
    band_size       = -8
    waist_size      = -9
    hip_size        = -10
    breast_type     = -11
    career_start_year = -12
    career_end_year = -13
    name            = -14
    birth_date      = -15
    disambiguation  = -16
    tatoos          = -17
    piercings       = -18
    aliases         = -19
    images          = -20
    urls            = -21
    ERROR = -99

def convertCountry(name):
    if not name or len(name) == 2:
        return name
    STASHBOX_COUNTRY_MAP = {
        "USA": "US",
        "United States": "US",
        "United States of America": "US",
        "America": "US",
        "American": "US",
        "Czechia": "CZ",
        "Czech Republic" : "CZ",
        "England": "GB",
        "United Kingdom": "GB",
        "Russia": "RU",
        "Slovak Republic": "SK",
        "Venezuela" : "VE",
        "English" : "UK",
        "Canadian, French Canadian" : "CA",
        "Canadian" : "CA"
    }
    if name in STASHBOX_COUNTRY_MAP.keys():
        return STASHBOX_COUNTRY_MAP[name]
    else:
        ct = pycountry.countries.get(name=name)
        return ct.alpha_2

def handleGQLResponse(response):
    try:
        if response.status_code == 200:
            jsonData = response.json()
            if "errors" in jsonData and jsonData["errors"] != None:
                print(f'Error in Stash call: {response.text}')
                raise Exception(response.text)
            return jsonData['data']
        else:
            print(f"Error in Stash call: {response.status_code}" )
    except Exception as e:
        print("Other error")
        raise e

def getImgB64(url):
    imageRequest = requests.get(url)
    if imageRequest.status_code != 200:
        print("Error getting image HTTP ", imageRequest.status_code)
        return None
    
    return base64.b64encode(imageRequest.content)

def resolveGQLFragments(gql, fragments):
    requiredFragments = []
    for fragment in fragments.keys():
        if fragment in gql:
            requiredFragments.append(GQLQ.FRAGMENTS[fragment])

            # If the fragment uses fragments
            filteredFragments = deepcopy(fragments)
            filteredFragments.pop(fragment)
            requiredFragments = requiredFragments + resolveGQLFragments(GQLQ.FRAGMENTS[fragment], filteredFragments)
    return list(set(requiredFragments))


def callGraphQL(stashBoxEndpoint, query, variables={}):
    resolvedQuery = query + "\n" + "\n".join(resolveGQLFragments(query, GQLQ.FRAGMENTS))
    json_request = {'query': resolvedQuery}
    
    if variables:
        serialize_dict(variables)
        json_request['variables'] = variables

    headers = {
		"Accept-Encoding": "gzip, deflate",
		"Content-Type": "application/json",
		"Accept": "application/json",
		"Connection": "keep-alive",
		"DNT": "1",
        "ApiKey" : stashBoxEndpoint['api_key']
	}

    response = requests.post(stashBoxEndpoint['endpoint'], json=json_request, headers=headers)
    
    return handleGQLResponse(response)

def upload_image(destinationEndpoint, image_in, existing = {}, excluded = {}):
    b64img_bytes = None
    if re.search(r';base64',image_in):
        m = re.search(r'data:(?P<mime>.+?);base64,(?P<img_data>.+)',image_in)
        mime = m.group("mime")
        b64img_bytes = m.group("img_data").encode("utf-8")
        if not mime:
            # could not determine MIME type defaulting to jpeg
            mime = 'image/jpeg'
    if re.match(r'^http', image_in):
        b64img_bytes = getImgB64(image_in)
        mime = 'image/jpeg'

    if b64img_bytes is None:
        raise Exception("upload_image requires a base64 string or url")
    
    if b64img_bytes in excluded.keys():
        print("Skipping image, removed")
        return

    if b64img_bytes in existing.keys():
        print("Skipping image, already existing")
        return
    
    body, multipart_header = encode_multipart_formdata({
        'operations':'{"operationName":"AddImage","variables":{"imageData":{"file":null}},"query":"mutation AddImage($imageData: ImageCreateInput!) {imageCreate(input: $imageData) {id url}}"}',
        'map':'{"1":["variables.imageData.file"]}',
        '1': ('1.jpg', base64.decodebytes(b64img_bytes), mime)
    })

    request_headers = {
		"Accept-Encoding": "gzip, deflate",
		"Content-Type": multipart_header,
		"Accept": "application/json",
		"Connection": "keep-alive",
		"DNT": "1",
        "ApiKey" : destinationEndpoint['api_key']
	}
    
    response = requests.post(destinationEndpoint['endpoint'], data=body, headers=request_headers)
    return handleGQLResponse(response)["imageCreate"]

def stashDateToDateTime(stashDate : str) -> datetime:
    try:
        ret = datetime.strptime(stashDate, "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError:
        ret = datetime.strptime(stashDate, "%Y-%m-%dT%H:%M:%SZ")
    except:
        raise
    return ret

def getAllPerformers(sourceEndpoint : Dict, callback = None):
    returnData = []
    pages = -1
    query = {
        "page" : 1,
        "per_page" : 100
    }

    response = callGraphQL(sourceEndpoint, GQLQ.GET_ALL_PERFORMERS, {"input" : query})["queryPerformers"]
    returnData = response["performers"]
    pages = math.ceil(response["count"] / query["per_page"])
    while query["page"] < pages:
        query["page"] += 1
        print(f"GetAllPerformers page {query['page']} of {pages}")

        # Avoid overloading the server
        time.sleep(5)
        response = callGraphQL(sourceEndpoint, GQLQ.GET_ALL_PERFORMERS, {"input" : query})["queryPerformers"]
        returnData.extend(response["performers"])
        if callback != None:
            callback(response["performers"])
    
    return returnData

def getAllEdits(endpoint : Dict, limit = 7, callback = None):
    dateLimit = datetime.now() - timedelta(days=limit)

    returnData = []
    pages = -1
    query = {
        "applied": True,
        "target_type" : "PERFORMER",
        "page" : 1,
        "per_page" : 100
    }

    print(f"GetAllEdits page 1")
    response = callGraphQL(endpoint, GQLQ.GET_ALL_PERFORMER_EDITS, {"input" : query})["queryEdits"]
    returnData = response["edits"]
    pages = math.ceil(response["count"] / query["per_page"])
    while query["page"] < pages:
        query["page"] += 1
        print(f"GetAllEdits page {query['page']} of {pages}")

        # Avoid overloading the server
        time.sleep(5)
        response = callGraphQL(endpoint, GQLQ.GET_ALL_PERFORMER_EDITS, {"input" : query})["queryEdits"]
        returnData.extend(response["edits"])
        if callback != None:
            callback(response["edits"])

        if stashDateToDateTime(response["edits"][-1]["closed"]) < dateLimit:
            print(f"All edits for past {limit} days loaded, GetAllEdits done")
            break
    
    return returnData

def getOpenEdits(endpoint : Dict):
    returnData = []
    pages = -1
    query = {
        "target_type" : "PERFORMER",
        "status" : "PENDING",
        "page" : 1,
        "per_page" : 100
    }

    print(f"GetOpenEdits page 1")
    response = callGraphQL(endpoint, GQLQ.GET_ALL_PERFORMER_EDITS, {"input" : query})["queryEdits"]
    returnData = response["edits"]
    pages = math.ceil(response["count"] / query["per_page"])
    while query["page"] < pages:
        query["page"] += 1
        print(f"GetOpenEdits page {query['page']} of {pages}")

        # Avoid overloading the server
        time.sleep(5)
        response = callGraphQL(endpoint, GQLQ.GET_ALL_PERFORMER_EDITS, {"input" : query})["queryEdits"]
        returnData.extend(response["edits"])
    
    return returnData

def comparePerformers(performerA : t.Performer, performerB : t.Performer):
    returnCodes = []
    for attr in ["name","gender","ethnicity","hair_color", "eye_color", "height", "breast_type", "disambiguation", "career_end_year", "career_start_year", "cup_size", "band_size", "waist_size", "hip_size"]:
        valueA = performerA.get(attr)
        valueB = performerB.get(attr)
        if valueA and valueB:
            if (isinstance(valueA, str) and valueA.lower() != valueB.lower()) or valueA != valueB:
                # Values are different
                returnCodes.append(ComparisonReturnCode[attr])
        elif valueA or valueB:
            # Only one of the values exists
            returnCodes.append(ComparisonReturnCode[attr])
    
    countryA = convertCountry(performerA.get("country"))
    countryB = convertCountry(performerB.get("country"))
    if countryA and countryB:
        if countryA != countryB:
            # Values are different
            returnCodes.append(ComparisonReturnCode["country"])
    elif countryA or countryB:
        # Only one of the values exists
        returnCodes.append(ComparisonReturnCode["country"])

    
    # Handle birthday separately, it's a mess due to the var change
    valueA = performerA.get("birth_date", performerA.get("birthdate"))
    valueB = performerB.get("birth_date", performerB.get("birthdate"))
    if valueA and valueB:
        if valueA != valueB:
            if len(valueA) != len(valueB):
                # One of the dates is a short date, the other is not
                dateChecker = r"^(\d{4})-01-01"
                if len(valueA) == 4:
                    check = re.match(dateChecker, valueB)
                    if check and valueA != check.group(1):
                        returnCodes.append(ComparisonReturnCode.birth_date)
                elif len(valueB) == 4:
                    check = re.match(dateChecker, valueA)
                    if check and valueB != check.group(1):
                        returnCodes.append(ComparisonReturnCode.birth_date)
            else:
                returnCodes.append(ComparisonReturnCode.birth_date)
    elif valueA and not valueB:
        returnCodes.append(ComparisonReturnCode.birth_date)

    valueA = performerA.get("aliases")
    valueB = performerB.get("aliases")
    # Cleanup Stashbox bug where aliases were not correctly split
    if valueA and len(valueA) == 1 and "," in valueA[0]:
        valueA = [x.strip() for x in valueA[0].split(",")]
    if valueB and len(valueB) == 1 and "," in valueB[0]:
        valueB = [x.strip() for x in valueB[0].split(",")]

    if valueA and valueB:
        if set(valueA) != set(valueB):
            returnCodes.append(ComparisonReturnCode.aliases)
        
    

    if len(returnCodes) == 0:
        returnCodes = [ComparisonReturnCode.IDENTICAL]
    return returnCodes

class StashBoxSitesMapper:
    SITES_MAP = []
    SOURCE_INFOS = {
        StashSource.PMVSTASH : {
            "url" : "https://pmvstash.org/",
            "siteIds" : {},
            "regex" : r"^https?:\/\/pmvstash\.org\/performers\/.+",
            "default_performer_link" : "1cda874a-bab4-44d8-b32b-c1e485e66b6f"
        },
        StashSource.STASHDB: {
            "url" : "https://stashdb.org/",
            "siteIds" : {},
            "regex" : r"^https:\/\/stashdb\.org\/performers\/[a-z0-9]{8}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{12}",
            "default_performer_link" : None
        },
        StashSource.FANSDB : {
            "url" : "https://fansdb.cc/",
            "siteIds" : {},
            "regex" : r"^https?:\/\/(?:www\.)?fansdb\.(?:cc|xyz)\/performers\/.+",
            "default_performer_link" : None
        }
    }
    SOURCE : StashSource
    DESTINATION : StashSource

    def __init__(self, source : StashSource = None, destination: StashSource = None) -> None:
        self.SOURCE = source
        self.DESTINATION = destination

    def mapUrlToID(self, url):
        if url == "":
            return None
        
        for site in self.SITES_MAP:
            if re.match(site['regex'], url):
                return site['id']
        return None

    def mapUrlToEdit(self, url) -> Dict:
        destinationId = self.mapUrlToID(url["url"])
        if destinationId is None and self.SOURCE_INFOS[self.DESTINATION]["default_performer_link"] is not None:
            # If there is a default link type, use it when the link doesn't match anything else
            destinationId = self.SOURCE_INFOS[self.DESTINATION]["default_performer_link"]

        if destinationId is not None:
            return {
                    "url" : url["url"],
                    "site_id" : destinationId
                }
    
    def isTargetStashBoxLink(self, url : str, target : StashSource) -> bool:
        """
        Returns True if the url matches the pattern for target
        """
        return re.match(self.SOURCE_INFOS[target]["regex"], url)
    
    def whichStashBoxLink(self, url : str) -> StashSource:
        """
        If the url is a link to a StashBox page, return the appropriate StashSource
        """
        for source in self.SOURCE_INFOS.keys():
            if self.isTargetStashBoxLink(url, source):
                return source
        
        return None
    
    def getSitesFromDestinationServer(self, destinationEndpoint : Dict) -> None:
        gql = """
        query QuerySites {
            querySites {
                count
                sites {
                    id
                    url
                    name
                    regex
                    valid_types
                }
            }
        }
        """
        siteList = callGraphQL(destinationEndpoint, gql)['querySites']['sites']
        for site in siteList:
            if 'PERFORMER' in site['valid_types']:
                self.SITES_MAP.append(site)
                for source in self.SOURCE_INFOS.keys():
                    if site['url'].startswith(self.SOURCE_INFOS[source]['url']):
                        self.SOURCE_INFOS[self.DESTINATION]['siteIds'][source] = site["id"]
        


class StashBoxFilterManager:
    stashBoxEndpoint : Dict

    def __init__(self, endpoint : Dict) -> None:
        self.stashBoxEndpoint = endpoint
    
    def filterPerformersInQueue(self, performerUploads : List[PerformerUploadConfig], verbose = True):
        """
        Retrieves Edits posted by the current user, and checks if the current uploads are not already in there

        ### Parameters
            - performerUploads ([PerformerUploadConfig]): List of PerformerUploadConfig describing the performers to be uploaded
            - verbose (bool): Should the function print if a dupe Edit is found

        ### Returns
            Returns the list without any duplicates
        """
        gql = """
        query QueryEdits($input: EditQueryInput!) {
            queryEdits(input: $input) {
                edits {
                id
                details {
                    ... on PerformerEdit {
                    name
                    }
                }
                }
            }
        }
        """
        input = {
            "per_page": 100,
            "user_id": "6e0c73cd-fd15-4fa9-9037-7504c32c3744",
            "status": "PENDING",
            "target_type": "PERFORMER",
            "operation" : "CREATE"
        }

        newUpload = performerUploads.copy()

        currentEdits = callGraphQL(self.stashBoxEndpoint, gql, {'input' : input})['queryEdits']['edits']
        if currentEdits != []:
            editNames = list(map(
                lambda edit: edit['details']['name']
                , currentEdits
            ))

            for upload in performerUploads:
                if upload['name'] in editNames:
                    if verbose:
                        print(f"{upload['name']} is already added")
                    newUpload.remove(upload)
        
        return newUpload
    
    def filterPerformersDupes(self, performerUploads : List[PerformerUploadConfig], verbose = True):
        """
        Checks if the performers in performerUploads are not already in the DB

        !!! Only checks based on the main Performer name !!!

        ### Parameters
            - performerUploads ([PerformerUploadConfig]): List of PerformerUploadConfig describing the performers to be uploaded
            - verbose (bool): Should the function print if a dupe Performer is found

        ### Returns
            Returns the list without any duplicates
        """
        gql = """
        query QueryPerformers($input: PerformerQueryInput!) {
            queryPerformers(input: $input) {
                performers {
                id
                name
                }
            }
        }
        """
        newUpload = performerUploads.copy()
        for upload in performerUploads:
            currentPerformers = callGraphQL(self.stashBoxEndpoint, gql, {'input' : {"name" : upload['name']}})['queryPerformers']['performers']
            currentPerformerNames = list(map(
                lambda performer: performer['name'].strip().lower()
                , currentPerformers
            ))
            if upload['name'].strip().lower() in currentPerformerNames:
                if verbose:
                    print(f"{upload['name']} is already in the destination")
                newUpload.remove(upload)
        
        return newUpload

class StashBoxPerformerManager:
    """
    A helper class to interact with StashBox Performers.

    Maintains a copy of the last retrieved performer in self.performer
    """
    performer : t.Performer
    siteMapper : StashBoxSitesMapper
    sourceEndpoint = {}
    destinationEndpoint = {}
    cache : StashBoxCache
    
    def __init__(self, sourceEndpoint, destinationEndpoint, sitesMapper : StashBoxSitesMapper = None, cache : StashBoxCache = None) -> None:
        """
        Initialises the Manager

        ### Parameters
            - siteIdsMapConfig (StashBoxSitesMapper): 
        """
        if sitesMapper is None:
            self.siteMapper = StashBoxSitesMapper()
        else:
            self.siteMapper = sitesMapper
        
        self.sourceEndpoint = sourceEndpoint
        self.destinationEndpoint = destinationEndpoint
        self.cache = cache

    def setPerformer(self, performer : t.Performer):
        self.performer = performer

    def getPerformer(self, performerId : str) -> t.Performer:
        """
        Retrieves the performer, returns it and stores it in the Manager

        ### Parameters
            - performerId (str): The performer's ID in the StashBox instance

        ### Returns
            The performer as a t.Performer
        """
        if self.cache != None:
            self.performer = self.cache.getPerformerById(performerId)
        else:
            self.performer = callGraphQL(self.sourceEndpoint, GQLQ.GET_PERFORMER, {'input' : performerId})['findPerformer']

        return self.performer
    
    def asDraftInput(self, performer : t.Performer = None) -> t.PerformerDraftInput:
        """
        Returns a PerformerDraftInput conversion of the Performer

        ### Parameters
            - performer (t.Performer, optional): The performer that should be converted. (default: the stored performer)
        """
        if performer == None:
            performer = self.performer

        draftPerf : t.PerformerDraftInput = {}

        if performer.get("aliases"):
            aliases = ",".join(performer["aliases"])
            draftPerf["aliases"] = aliases
        
        if performer.get("birth_date"):
            draftPerf["birthdate"] = performer.get("birth_date")

        if performer.get("cup_size") or performer.get("band_size") or performer.get("waist_size") or performer.get("hip_size"):
            measurements = str(performer.get("band_size") or "") + (performer.get("cup_size") or "") + "-" + str(performer.get("waist_size") or "") + "-" + str(performer.get("hip_size") or "")
            draftPerf["measurements"] = measurements

        # Autocopy items which don't need to be mapped
        for attr in ["name", "gender", "ethnicity", "country", "eye_color", "hair_color", "height", "breast_type", "career_start_year", "career_end_year"]:
            if performer.get(attr):
                draftPerf[attr] = performer[attr]

        return draftPerf
    
    def asPerformerEditDetailsInput(self, performer : t.Performer = None) -> t.PerformerEditDetailsInput:
        """
        Returns a PerformerEditDetailsInput conversion of the Performer

        Uploads the images of the performer

        ### Parameters
            - performer (t.Performer, optional): The performer that should be converted. (default: the stored performer)
        """
        if performer == None:
            performer = self.performer

        draftCreate : t.PerformerEditDetailsInput = {}

        for attr in ["name","disambiguation","aliases", "gender", "ethnicity", "eye_color", "hair_color", "height", "cup_size", "band_size", "waist_size", "hip_size", "breast_type", "career_start_year", "career_end_year", "piercings", "tattoos"]:
            if performer.get(attr):
                draftCreate[attr] = performer[attr]
        
        birthdate = performer.get("birthdate", performer.get("birth_date"))
        if type(birthdate) is dict:
            birthdate = birthdate["date"]
        draftCreate["birthdate"] = birthdate if birthdate != '' else None

        if performer.get("country"):
            draftCreate["country"] = convertCountry(performer.get("country"))



        draftCreate["urls"] = performer.get("urls",[])
        draftCreate["urls"] = list(filter(lambda url: url is not None, map(lambda url: self.siteMapper.mapUrlToEdit(url), draftCreate["urls"])))
        draftCreate["urls"] = list(filter(lambda url: url["url"] != "", draftCreate["urls"]))

        return draftCreate
    
    def uploadPerformerImages(self, performer : t.Performer = None, existing : List[t.Image] = [], removed : List[t.Image] = []) -> List[str]:
        """
        Uploads the images stored in performer['images'] to the destination StashBox instance

        Returns an array of image IDs

        ### Parameters
            - performer (t.Performer, optional): The performer that should be converted. (default: the stored performer)
            - existing ([t.Image], optional): List of already uploaded images, to keep all existing
            - existing ([t.Image], optional): List of images that were removed from the source, to remove them too
        """
        if performer == None:
            performer = self.performer

        imageIds = []
        counter = 0
        sourceImgs = performer.get("images", [])
        
        print("Loading existing images")
        existingImgs = {}
        for img in existing:
            existingImgs[getImgB64(img["url"])] = img["id"]
        
        removedImgs = {}
        for img in removed:
            if img:
                removedImgs[getImgB64(img["url"])] = img["id"]

        # Start with existing images
        for imgB64, id in existingImgs.items():
            if imgB64 not in removedImgs.keys():
                imageIds.append(id)

        for image in sourceImgs:
            counter +=1
            print(f"Uploading image {counter} of {len(sourceImgs)}")
            try:
                imageId = upload_image(self.destinationEndpoint, image['url'], existingImgs)
                if imageId:
                    imageIds.append(imageId["id"])
            except Exception as e:
                print("Error uploading image")
        
        return imageIds
    
    def submitPerformerCreate(self, performerInput : t.PerformerEditDetailsInput, comment : str) -> t.Edit:
        """
        """

        gql = """
            mutation PerformerEdit($input: PerformerEditInput!) {
                performerEdit(input: $input) {
                    id
                }
            }
        """
        edit : t.EditInput = {
            'operation' : 'CREATE',
            'comment' : comment,
            'bot' : False
        }

        input = {
            "details" : performerInput,
            "edit" : edit
        }

        return callGraphQL(self.destinationEndpoint, gql, {'input' : input})['performerEdit']
    
    def submitPerformerUpdate(self, performerId : str, performerInput : t.PerformerEditDetailsInput, comment : str, bot : bool = True) -> t.Edit:
        """
        """

        gql = """
            mutation PerformerEdit($input: PerformerEditInput!) {
                performerEdit(input: $input) {
                    id
                }
            }
        """
        edit : t.EditInput = {
            'operation' : 'MODIFY',
            'id' : performerId,
            'comment' : comment,
            'bot' : bot
        }

        input = {
            "details" : performerInput,
            "edit" : edit,
            "options": {
                "set_modify_aliases" : True
            }
        }

        return callGraphQL(self.destinationEndpoint, gql, {'input' : input})['performerEdit']

class StashBoxPerformerHistory:
    performer : t.Performer
    performerEdits : List[t.PerformerEdit]
    performerStates : List[t.Performer]
    cache : StashBoxCache
    siteMapper : StashBoxSitesMapper
    removedImages : List[t.Image]
    removedAliases : List[str]

    def __init__(self, stashBoxEndpoint : Dict, performerId : str, cache : StashBoxCache = None, siteMapper : StashBoxSitesMapper = None) -> None:
        self.endpoint = stashBoxEndpoint
        self.performerEdits = []
        self.performerStates = {}
        self.cache = cache
        self.siteMapper = siteMapper if siteMapper != None else StashBoxSitesMapper()
        self.removedImages = []
        self.removedAliases = []
        self._getPerformerWithHistory(performerId)
        
    def _getPerformerWithHistory(self, performerId : str) -> t.Performer:
        if self.cache != None:
            try:
                self.performer = self.cache.getPerformerById(performerId)
            except Exception as e:
                print("Error - Performer not in cache")
                raise(e)
        else:
            perfData : t.Performer = callGraphQL(self.endpoint,GQLQ.GET_PERFORMER, {'input' : performerId})['findPerformer']
            self.performer = perfData

        edits = self.performer.get("edits", [])

        if len(edits) == 0:
            # There are no Edits, an issue when the DB was imported initially // Create a fake Edit for the initial submit
            self.performerStates[stashDateToDateTime(self.performer["created"])] = {
                "details" : self.performer,
                "closed" : self.performer["created"]
            }
        else:
            createEdit = [edit for edit in edits if edit['operation'] == "CREATE"]
            self.performerEdits = [edit for edit in edits if edit['operation'] in ["MODIFY", "MERGE"] and edit['applied'] == True]
            self.performerEdits.sort(key=lambda edit: stashDateToDateTime(edit['closed']))
            if len(createEdit) > 0 and createEdit[0]["details"] != None:
                initial = createEdit[0]
            else:
                # There is no CREATE edit, a known StashDB issue... Need to reverse the entire Edit chain
                initial = self._getInitialState(self.performerEdits)
            
            self.performerStates[stashDateToDateTime(initial['closed'])] = StashBoxPerformerHistory.applyPerformerUpdate({"aliases" : [], "tattoos" : [], "piercings" : [], "images" : [], "urls" : []}, initial)

            prevState = self.performerStates[stashDateToDateTime(initial['closed'])] 
            self.performerEdits.sort(key=lambda edit: stashDateToDateTime(edit['closed']))
            for state in self.performerEdits:
                if self._checkStateChange(state):
                    prevState = StashBoxPerformerHistory.applyPerformerUpdate(prevState,state)
                    self.performerStates[stashDateToDateTime(state['closed'])] = prevState
            

            # Grab list of images which have been removed from the performer
            for state in self.performerEdits:
                if self._checkStateChange(state):
                    removedImagesAtState = state['details'].get("removed_images")
                    if removedImagesAtState is not None:
                        self.removedImages.extend(removedImagesAtState)

            # Grab list of aliases which have been removed from the performer
            for state in self.performerEdits:
                if self._checkStateChange(state):
                    removedAliasAtState = state['details'].get("removed_aliases")
                    if removedAliasAtState is not None:
                        self.removedAliases.extend(removedAliasAtState)
        
        return

    def _checkStateChange(self, changes : t.PerformerEdit) -> bool:
        if changes["details"] == None:
            return True
        # Checks if there are **applicable** changes in the Edit
        for attr in ["name","disambiguation","gender","birthdate", "birth_date","ethnicity","country","eye_color","hair_color","height","cup_size","band_size","waist_size","hip_size","breast_type","career_start_year","career_end_year"]:
            if changes['details'].get(attr) and changes['details'].get(attr) != "":
                return True

        for attr in ["added_aliases", "added_tattoos", "added_piercings", "added_images"]:
            if changes['details'].get(attr) and changes['details'].get(attr) != "":
                return True

        for attr in ["removed_aliases", "removed_tattoos", "removed_piercings", "removed_images"]:
            if changes['details'].get(attr) and changes['details'].get(attr) != "":
                return True
            
        for attr in ["removed_urls", "added_urls"]:
            if changes['details'].get(attr) and len(changes['details'].get(attr)) > 0:
                for url in changes['details'].get(attr):
                    if self.siteMapper.mapUrlToID((url["url"])) is not None:
                        return True
        
        # Should return False if the only change is affecting URLs which are not mapped in the destination StashBox
        return False

    def _getInitialState(self, allEdits : List[t.PerformerEdit]):
        firstState = deepcopy(self.performer)
        firstState.pop('merged_ids')
        allEdits.reverse()

        # Init arrays if they are "None"
        for attr in ["aliases", "tattoos", "piercings", "images", "urls"]:
            if firstState[attr] == None:
                firstState[attr] = []

        for edit in allEdits:
            if edit["details"] == None:
                # Some Edits don't have any changes except a MERGE action
                continue

            # Reverse the Edit actions
            for attr in ["created","closed","name","disambiguation","gender","birthdate","ethnicity","country","eye_color","hair_color","height","cup_size","band_size","waist_size","hip_size","breast_type","career_start_year","career_end_year"]:
                if edit['details'].get(attr):
                    # This attribute has changed
                    firstState[attr] = edit['old_details'][attr]

            for attr in ["added_aliases", "added_tattoos", "added_piercings", "added_images", "added_urls"]:
                if edit['details'].get(attr):
                    for x in edit['details'].get(attr):
                        if x in firstState[attr.split('_')[1]] :
                            firstState[attr.split('_')[1]].remove(x)

            for attr in ["removed_aliases", "removed_tattoos", "removed_piercings", "removed_images", "removed_urls"]:
                if edit['details'].get(attr):
                    for x in edit['details'].get(attr):
                        if x != None:
                            firstState[attr.split('_')[1]].append(x)
        
        for attr in ["removed_aliases", "removed_tattoos", "removed_piercings", "removed_images", "removed_urls"]:
            firstState[attr] = []

        for attr in ["added_aliases", "added_tattoos", "added_piercings", "added_images", "added_urls"]:
            firstState[attr] = firstState[attr.split('_')[1]]

        allEdits.reverse()

        return {
            "details": firstState,
            "closed": "2000-01-01T01:01:01Z"
        }
    
    def getByDateTime(self, targetDate : datetime) -> t.Performer:
        dates = list(self.performerStates.keys())
        dates.sort()
        id = bisect.bisect_left(dates,targetDate)

        if id == 0:
            # Performer didn't exist yet
            return {}
        
        return self.performerStates[dates[id-1]]

    def compareAtDateTime(self, targetDate : datetime, compareTo : t.Performer) -> List[ComparisonReturnCode]:
        """
        Returns a list of differences between the Performer at targetDate, and the compareTo performer. Only returns a difference code if a data change is detected, not if data is missing.
        """
        returnCodes = []
        localPerf = self.getByDateTime(targetDate)

        for attr in ["name","gender","ethnicity","eye_color","hair_color","height","hip_size","breast_type","career_start_year","career_end_year"]:
            valueA = compareTo.get(attr)
            historicalValue = localPerf.get(attr)
            if valueA and historicalValue:
                if (isinstance(valueA, str) and valueA.lower() != historicalValue.lower()) or valueA != historicalValue:
                    # Values are different
                    returnCodes.append(ComparisonReturnCode[attr])
            elif valueA and not historicalValue:
                # There was no value but one was added, return diff
                returnCodes.append(ComparisonReturnCode[attr])
        
        # Handle countries separately due to Full text / Country codes
        countryA = convertCountry(compareTo.get("country"))
        countryB = convertCountry(localPerf.get("country"))
        if countryA and countryB:
            if countryA != countryB:
                # Values are different
                returnCodes.append(ComparisonReturnCode["country"])
        elif countryA or countryB:
            # Only one of the values exists
            returnCodes.append(ComparisonReturnCode["country"])
        
        # Handle birthday separately, it's a mess due to the var change
        valueA = compareTo.get("birth_date", compareTo.get("birthdate"))
        historicalValue = localPerf.get("birth_date", localPerf.get("birthdate"))
        if valueA and historicalValue:
            if valueA != historicalValue:
                if len(valueA) != len(historicalValue):
                    # One of the dates is a short date, the other is not
                    dateChecker = r"^(\d{4})-01-01"
                    if len(valueA) == 4:
                        check = re.match(dateChecker, historicalValue)
                        if check and valueA != check.group(1):
                            returnCodes.append(ComparisonReturnCode.birth_date)
                    elif len(historicalValue) == 4:
                        check = re.match(dateChecker, valueA)
                        if check and historicalValue != check.group(1):
                            returnCodes.append(ComparisonReturnCode.birth_date)
                else:
                    returnCodes.append(ComparisonReturnCode.birth_date)
        elif valueA and not historicalValue:
            # There was no value but one was added, return diff
            returnCodes.append(ComparisonReturnCode.birth_date)
            
        for attr in ["disambiguation","cup_size","band_size","waist_size"]:
            # These are not properly passed when scraping & uploading, so not taking them into account if one is missing
            valueA = compareTo.get(attr)
            historicalValue = localPerf.get(attr)
            if valueA and historicalValue:
                if (isinstance(valueA, str) and valueA.lower() != historicalValue.lower()) or valueA != historicalValue:
                    # Values are different
                    returnCodes.append(ComparisonReturnCode[attr])
            elif valueA and not historicalValue:
                # There was no value but one was added, return diff
                returnCodes.append(ComparisonReturnCode[attr])
        
        for attr in ["tatoos", "piercings"]:
            # These are not properly passed when scraping & uploading, so not taking them into account for now
            pass
            

        # Compare aliases
        valueA = compareTo.get("aliases")
        historicalValue = localPerf.get("aliases")
        if valueA and historicalValue:
            valueASet = set(valueA)
            historicalValueSet = set(historicalValue)
            if len(historicalValueSet) > len(valueASet):
                # Some aliases were removed, return diff
                returnCodes.append(ComparisonReturnCode.aliases)
            elif len(valueASet) > len(historicalValueSet) and historicalValueSet.issubset(valueASet):
                # Some aliases were added, and some were removed
                returnCodes.append(ComparisonReturnCode.aliases)
            elif len(valueASet) == len(historicalValueSet) and valueASet != historicalValueSet:
                returnCodes.append(ComparisonReturnCode.aliases)

        
        localImgs = localPerf.get("images", [])
        compareImgs = compareTo.get("images", [])
        if len(compareImgs) > 1 and len(localImgs) != len(compareImgs):
            # The list of images has been edited
            returnCodes.append(ComparisonReturnCode.images)

        if len(returnCodes) == 0:
            returnCodes = [ComparisonReturnCode.IDENTICAL]
        return returnCodes
    
    def isIncomplete(self, targetDate : datetime, compareTo : t.Performer) -> bool:
        # Due to Stash / StashBox incompatibilities, some values are not properly parsed when creating performers manually. Try to detect if the performer needs to be fixed
        localPerf = self.getByDateTime(targetDate)

        for attr in ["disambiguation","tatoos", "piercings","cup_size","band_size","waist_size"]:
            valueA = compareTo.get(attr)
            valueB = localPerf.get(attr)
            if valueB and not valueA:
                # Value is missing
                print(f"Missing: {attr}")
                return True

        localBirthdate = localPerf.get("birthdate", localPerf.get("birth_date"))
        compareBirthdate = compareTo.get("birthdate", compareTo.get("birth_date"))
        if type(localBirthdate) is dict:
            localBirthdate = localBirthdate["date"]
        if type(compareBirthdate) is dict:
            compareBirthdate = compareBirthdate["date"]
        if localBirthdate and not compareBirthdate:
                print(f"Missing: birthday")
                return True
        
        localImgs = localPerf.get("images", [])
        compareImgs = compareTo.get("images", [])
        if len(localImgs) <= 1 and len(localImgs) > len(compareImgs):
            print(f"Missing: images")
            return True

        
        return False

    def hasUpdate(self, targetDate : datetime, performer : t.Performer = None) -> bool:
        # Cannot simply use the Update value due to not replicating some changes (see _checkStateChange)
        dates = list(self.performerStates.keys())
        dates.sort()
        id = bisect.bisect_right(dates,targetDate)
        return id < len(dates)
    
    @staticmethod
    def applyPerformerUpdate(currentPerformer : t.Performer, editChanges : t.PerformerEdit) -> t.Performer:
        newState = deepcopy(currentPerformer)

        if "details" not in editChanges.keys() or editChanges["details"] == None:
            return newState

        for attr in ["name","disambiguation","gender","birthdate", "birth_date","ethnicity","country","eye_color","hair_color","height","cup_size","band_size","waist_size","hip_size","breast_type","career_start_year","career_end_year", "created", "updated", "deleted"]:
            if editChanges['details'].get(attr):
                newState[attr] = editChanges['details'][attr]

        for attr in ["added_aliases", "added_tattoos", "added_piercings", "added_images", "added_urls"]:
            if editChanges['details'].get(attr):
                for x in editChanges['details'].get(attr):
                    key = attr.split('_')[1]
                    if key not in newState or newState[key] == None:
                        newState[key] = []
                    newState[key].append(x)

        for attr in ["removed_aliases", "removed_tattoos", "removed_piercings", "removed_urls"]:
            if editChanges['details'].get(attr):
                for x in editChanges['details'].get(attr):
                    if x in newState[attr.split('_')[1]]:
                        newState[attr.split('_')[1]].remove(x)
        
        if editChanges['details'].get("removed_images"):
            for x in editChanges['details'].get("removed_images"):
                    if x == None:
                        continue
                    existingImg = [img for img in newState["images"] if img and img["id"] == x["id"]][0]
                    newState["images"].remove(existingImg)
        
        return newState
    
class StashBoxCacheManager:
    cache : StashBoxCache
    saveToFile = True
    stashBoxConnectionParams = {}
    

    def __init__(self, stashBoxConnection : dict, saveToFile = True) -> None:
        self.cache = StashBoxCache(stashBoxConnection['name'])
        self.saveToFile = saveToFile
        self.stashBoxConnectionParams = stashBoxConnection
    
    def loadCache(self, useFile = True, limitHours = 24, refreshLimitDays = 7):
        if useFile:
            self.cache.loadCacheFromFile()
            self.updateCache(limitHours, refreshLimitDays)
        else:
            self.loadCacheFromStashBox()

    def loadCacheFromStashBox(self):
        self.cache.performers = getAllPerformers(self.stashBoxConnectionParams)
        self.cache.cacheDate = datetime.now()

    def updateCache(self, limitHours = 24, refreshLimitDays = 7):
        dateLimit = datetime.now() - timedelta(hours=limitHours)
        dateRefreshLimit = datetime.now() - timedelta(days=refreshLimitDays)

        if self.cache.cacheDate >= dateLimit:
            # Cache is already up to date
            print("Cache is up to date")
            return
        
        if self.cache.cacheDate < dateRefreshLimit:
            # Cache is too old to refresh, do a full reload
            print("Existing cache file is too old, grabbing a brand new one")
            self.loadCacheFromStashBox()
            if self.saveToFile:
                self.cache.saveCacheToFile()
            return
        
        # Cache can be refreshed, load all the recent Edits and apply them
        print("Existing cache file is outdated, updating it with latest changes")
        allEdits = getAllEdits(self.stashBoxConnectionParams, refreshLimitDays)
        allEditsFiltered = list(filter(lambda edit: stashDateToDateTime(edit["closed"]) >= self.cache.cacheDate, allEdits))
        allEditsFiltered.reverse()
        print(f"{len(allEditsFiltered)} changes to process")

        for edit in allEditsFiltered:
            targetPerformerId = edit["target"]["id"]
            print(f"{edit['operation']} on {targetPerformerId}")

            if edit["operation"] == "CREATE":
                perf = StashBoxPerformerHistory.applyPerformerUpdate({}, edit)
                perf["id"] = edit["target"]["id"]
                perf["updated"] = edit["closed"]
                perf["created"] = edit["target"]["created"]
                perf["deleted"] = False
                self.cache.performers.append(perf)
            elif edit["operation"] == "DESTROY":
                self.cache.deletePerformerById(targetPerformerId)
            elif edit["operation"] == "MODIFY" or edit["operation"] == "MERGE":
                performerIdx = self.cache._getPerformerIdxById(targetPerformerId)
                if performerIdx == None:
                    # Perf can be None if it was recently merged / deleted and an Edit was already in the queue for it. In that case, ignore it
                    continue
                self.cache.performers[performerIdx] = StashBoxPerformerHistory.applyPerformerUpdate(self.cache.performers[performerIdx], edit)
                perf = self.cache.performers[performerIdx]
                perf["updated"] = edit["closed"]

                if edit["operation"] == "MERGE":
                    mergedIds = list(map( lambda source: source["id"] ,edit["merge_sources"]))
                    for id in mergedIds:
                        self.cache.deletePerformerById(id)
        
        if self.saveToFile:
            self.cache.saveCacheToFile()

    def saveCache(self):
        self.cache.saveCacheToFile()
