import math, time, bisect, csv, re, base64
from copy import deepcopy
from datetime import datetime
from enum import Enum
from typing import TypedDict
from stashapi.classes import serialize_dict
from stashapi.stashapp import StashInterface
import schema_types as t
import requests
from urllib3 import encode_multipart_formdata
import pycountry

StashSource = Enum('StashSource', 'STASHDB PMVSTASH FANSDB')

PerformerUploadConfig = TypedDict('PerformerUploadConfig', {
	'name': str,
	'id': str,
    'comment':str
})



def convertCountry(name):
    if len(name) == 2:
        return name
    STASHBOX_COUNTRY_MAP = {
        "USA": "US",
        "United States": "US",
        "United States of America": "US",
        "America": "US",
        "American": "US",
        "Czechia": "CZ",
        "England": "GB",
        "United Kingdom": "GB",
        "Russia": "RU",
        "Slovak Republic": "SK"
    }
    if name in STASHBOX_COUNTRY_MAP.keys():
        return STASHBOX_COUNTRY_MAP[name]
    else:
        ct = pycountry.countries.get(name=name)
        return ct.alpha_2

def handleGQLResponse(response):
    try:
        if response.status_code == 200:
            return response.json()['data']
        else:
            print(f"Error in Stash call: {response.status_code}" )
    except Exception as e:
        print("Other error")
        raise

def getImgB64(url):
    return base64.b64encode(requests.get(url).content)

def callGraphQL(stashBoxEndpoint, query, variables={}):
    json_request = {'query': query}
    
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

def upload_image(destinationEndpoint, image_in, exclude = []):
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

    if not b64img_bytes:
        raise Exception("upload_image requires a base64 string or url")
    
    if b64img_bytes in exclude:
        print("Skipping image, already existing")
        return None
    
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

def getAllPerformers(sourceEndpoint : {}, callback = None):
    gql = """
    query QueryPerformers($input: PerformerQueryInput!) {
        queryPerformers(input: $input) {
            count
            performers {
            band_size
            aliases
            birth_date
            birthdate {
                date
            }
            breast_type
            career_end_year
            career_start_year
            country
            created
            cup_size
            deleted
            disambiguation
            ethnicity
            eye_color
            gender
            hair_color
            height
            hip_size
            id
            images {
                id
                url
            }
            merged_ids
            name
            piercings {
                description
                location
            }
            tattoos {
                description
                location
            }
            updated
            urls {
                url
                site {
                id
                }
            }
            waist_size
            }
        }
    }
    """

    returnData = []
    pages = -1
    query = {
        "page" : 1,
        "per_page" : 100
    }

    response = callGraphQL(sourceEndpoint, gql, {"input" : query})["queryPerformers"]
    returnData = response["performers"]
    pages = math.ceil(response["count"] / query["per_page"])
    while query["page"] < pages:
        query["page"] += 1
        print(f"GetAllPerformers page {query['page']} of {pages}")

        # Avoid overloading the server
        time.sleep(5)
        response = callGraphQL(sourceEndpoint, gql, {"input" : query})["queryPerformers"]
        returnData.extend(response["performers"])
        if callback != None:
            callback(response["performers"])
    
    return returnData



class StashBoxSitesMapper:
    SITE_IDS_MAP = []
    SOURCE_INFOS = {
        StashSource.PMVSTASH : {
            "url" : "https://pmvstash.org/",
            "siteIds" : {
                StashSource.STASHDB : "60e7e1f2-239c-4e33-97f2-9cc7e7e41d92",
                StashSource.FANSDB : "dd3dedb1-74dd-416e-afb9-c3e67c7ea077"
            }
        },
        StashSource.STASHDB: {
            "url" : "https://stashdb.org/",
            "siteIds" : {}
        },
        StashSource.FANSDB : {
            "url" : "https://fansdb.xyz/",
            "siteIds" : {
                StashSource.STASHDB : "0117e0d2-bb12-48f2-902b-d9eff99ab03f"
            }
        }
    }

    def __init__(self, configFile : str = "site_ids_map.csv") -> None:
        with open(configFile, mode='r') as file:
            csvFile = csv.DictReader(file)
            for line in csvFile:
                self.SITE_IDS_MAP.append(line)

    def mapUrlToEdit(self, url, source : StashSource, destination : StashSource):
        destinationId = [element[destination.name] for element in self.SITE_IDS_MAP if element[source.name] == url["site"]["id"]]
        if destinationId != []:
            return {
                    "url" : url["url"],
                    "site_id" : destinationId[0]
                }

class StashBoxFilterManager:
    stashBoxEndpoint : {}

    def __init__(self, endpoint : {}) -> None:
        self.stashBoxEndpoint = endpoint
    
    def filterPerformersInQueue(self, performerUploads : [PerformerUploadConfig], verbose = True):
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
    
    def filterPerformersDupes(self, performerUploads : [PerformerUploadConfig], verbose = True):
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
    source : StashSource
    destination : StashSource
    stash : StashInterface
    sourceEndpoint = {}
    destinationEndpoint = {}
    
    def __init__(self, stash : StashInterface, source : StashSource, destination : StashSource,   sitesMapper : StashBoxSitesMapper = None) -> None:
        """
        Initialises the Manager

        ### Parameters
            - siteIdsMapConfig (StashBoxSitesMapper): 
        """
        if sitesMapper is None:
            self.siteMapper = StashBoxSitesMapper()
        else:
            self.siteMapper = sitesMapper
        
        self.source = source
        self.destination = destination
        self.stash = stash
        self.sourceEndpoint = stash.get_stashbox_connection(StashBoxSitesMapper.SOURCE_INFOS[source]['url'])
        self.destinationEndpoint = stash.get_stashbox_connection(StashBoxSitesMapper.SOURCE_INFOS[destination]['url'])

    def setPerformer(self, performer : t.Performer):
        self.performer = performer

    def setSource(self, source : StashSource):
        self.source = source

    def setDestination(self, source : StashSource):
        self.destination

    def getPerformer(self, performerId : str) -> t.Performer:
        """
        Retrieves the performer from the specified stashBox, returns it and stores it in the Manager

        ### Parameters
            - stashBoxEndpoint: Object describing the connection to the destination StashBox (obtained by calling StashInterface.get_stashbox_connection)
            - performerId (str): The performer's ID in the StashBox instance

        ### Returns
            The performer as a t.Performer
        """
        gql = """
        query FindPerformer($input: ID!) {
            findPerformer(id: $input) {
                id
                name
                disambiguation
                aliases
                gender
                urls {
                    url
                    site {
                        id
                    }
                }
                birth_date
                age
                ethnicity
                country
                eye_color
                hair_color
                height
                cup_size
                band_size
                waist_size
                hip_size
                breast_type
                career_start_year
                career_end_year
                tattoos {
                    description
                    location
                }
                piercings {
                    description
                    location
                }
                images {
                    id
                    url
                }
                deleted
                merged_ids
                updated
            }
        }
        """
        self.performer = callGraphQL(self.sourceEndpoint, gql, {'input' : performerId})['findPerformer']
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
        draftCreate["birthdate"] = birthdate

        draftCreate["country"] = convertCountry(performer.get("country"))



        draftCreate["urls"] = performer.get("urls",[])
        draftCreate["urls"] = list(filter(lambda url: url is not None, map(lambda url: self.siteMapper.mapUrlToEdit(url, self.source, self.destination), draftCreate["urls"])))

        return draftCreate
    
    def uploadPerformerImages(self, performer : t.Performer = None, exclude : [str] = []) -> [str]:
        """
        Uploads the images stored in performer['images'] to the destination StashBox instance

        Returns an array of image IDs

        ### Parameters
            - performer (t.Performer, optional): The performer that should be converted. (default: the stored performer)
        """
        if performer == None:
            performer = self.performer

        imageIds = []
        counter = 0
        allImgs = performer.get("images", [])
        for image in allImgs:
            if image['url'] not in exclude:
                counter +=1
                print(f"Uploading image {counter} of {len(allImgs)}")
                imageId = upload_image(self.destinationEndpoint, image['url'], exclude)
                if imageId:
                    imageIds.append(imageId["id"])
        
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
            'bot' : True
        }

        input = {
            "details" : performerInput,
            "edit" : edit
        }

        return callGraphQL(self.destinationEndpoint, gql, {'input' : input})['performerEdit']
    
    def submitPerformerUpdate(self, performerId : str, performerInput : t.PerformerEditDetailsInput, comment : str) -> t.Edit:
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
            'bot' : True
        }

        input = {
            "details" : performerInput,
            "edit" : edit,
            "options": {
                "set_modify_aliases" : True
            }
        }

        return callGraphQL(self.destinationEndpoint, gql, {'input' : input})['performerEdit']

    def hasOpenDrafts(self, performer : t.Performer = None, stashBoxEndpoint : {} = None) -> bool:
        gql = """
            query Query($input: ID!) {
                findPerformer(id: $input) {
                    edits {
                    id
                    status
                    operation
                    }
                }
            }
        """

        if performer == None:
            performer = self.performer
        
        if stashBoxEndpoint == None:
            stashBoxEndpoint = self.sourceEndpoint
        
        openDrafts = callGraphQL(stashBoxEndpoint, gql, {'input' : performer['id']})['findPerformer']['edits']
        openDrafts = list(filter(
            lambda draft: draft["status"] == "PENDING"
            ,openDrafts
        ))
        return len(openDrafts) > 0

class StashBoxPerformerHistory:
    performer : t.Performer
    performerEdits : [t.PerformerEdit]
    performerStates : [t.Performer]

    def __init__(self, stashBoxEndpoint : {}, performerId : str) -> None:
        self.endpoint = stashBoxEndpoint
        self._getPerformerWithHistory(performerId)
        
    def _getPerformerWithHistory(self, performerId : str) -> t.Performer:
        gql = """
        query Query($input: ID!) {
            findPerformer(id: $input) {
                id
                name
                edits {
                applied
                closed
                details {
                    ... on PerformerEdit {
                    name
                    disambiguation
                    added_aliases
                    removed_aliases
                    gender
                    added_urls {
                        url
                        site {
                        id
                        }
                    }
                    removed_urls {
                        url
                        site {
                        id
                        }
                    }
                    birthdate
                    ethnicity
                    country
                    eye_color
                    hair_color
                    height
                    cup_size
                    band_size
                    waist_size
                    hip_size
                    breast_type
                    career_start_year
                    career_end_year
                    added_tattoos {
                        description
                        location
                    }
                    removed_tattoos {
                        description
                        location
                    }
                    added_piercings {
                        description
                        location
                    }
                    removed_piercings {
                        description
                        location
                    }
                    added_images {
                        url
                        id
                    }
                    removed_images {
                        id
                        url
                    }
                    draft_id
                    aliases
                    urls {
                        url
                        site {
                        id
                        }
                    }
                    images {
                        id
                        url
                    }
                    tattoos {
                        description
                        location
                    }
                    piercings {
                        description
                        location
                    }
                    }
                }
                operation
                old_details {
                    ... on PerformerEdit {
                    aliases
                    band_size
                    birthdate
                    breast_type
                    career_end_year
                    career_start_year
                    country
                    cup_size
                    disambiguation
                    ethnicity
                    eye_color
                    gender
                    hair_color
                    height
                    hip_size
                    images {
                        id
                        url
                    }
                    name
                    piercings {
                        description
                        location
                    }
                    tattoos {
                        description
                        location
                    }
                    urls {
                        url
                        site {
                        id
                        }
                    }
                    waist_size
                    }
                }
                }
                age
                aliases
                band_size
                birth_date
                breast_type
                career_end_year
                career_start_year
                country
                created
                cup_size
                deleted
                disambiguation
                ethnicity
                eye_color
                gender
                hair_color
                height
                hip_size
                images {
                id
                url
                }
                merged_ids
                piercings {
                description
                location
                }
                tattoos {
                description
                location
                }
                updated
                urls {
                url
                site {
                    id
                }
                }
                waist_size
            }
        }
        """
        
        perfData : t.Performer = callGraphQL(self.endpoint,gql, {'input' : performerId})['findPerformer']
        self.performer = perfData

        self.performerEdits : [t.PerformerEdit] = list(filter(
            lambda edit: edit['applied'] == True
            ,self.performer.pop("edits")
            ))
        self.performerEdits.sort(key=lambda edit: stashDateToDateTime(edit['closed']))
        self.performerStates = {}

        self.performerEdits = [edit for edit in self.performerEdits if edit['operation'] in ["MODIFY", "CREATE", "MERGE"]]
        initial = self._getInitialState(self.performerEdits)
        self.performerStates[stashDateToDateTime(initial['closed'])] = self._processPerformerEdit({"aliases" : [], "tattoos" : [], "piercings" : [], "images" : [], "urls" : []}, initial)

        prevState = self.performerStates[stashDateToDateTime(initial['closed'])]
        for state in self.performerEdits:
            prevState = self._processPerformerEdit(prevState,state)
            self.performerStates[stashDateToDateTime(state['closed'])] = prevState

    def _processPerformerEdit(self, currentState : t.Performer, editChanges : t.PerformerEdit) -> t.Performer:
        prevState = deepcopy(currentState)

        for attr in ["name","disambiguation","gender","birthdate", "birth_date","ethnicity","country","eye_color","hair_color","height","cup_size","band_size","waist_size","hip_size","breast_type","career_start_year","career_end_year"]:
            if editChanges['details'].get(attr):
                prevState[attr] = editChanges['details'][attr]

        for attr in ["added_aliases", "added_tattoos", "added_piercings", "added_images", "added_urls"]:
            if editChanges['details'].get(attr):
                for x in editChanges['details'].get(attr):
                    prevState[attr.split('_')[1]].append(x)

        for attr in ["removed_aliases", "removed_tattoos", "removed_piercings", "removed_images", "removed_urls"]:
            if editChanges['details'].get(attr):
                for x in editChanges['details'].get(attr):
                    prevState[attr.split('_')[1]].remove(x)

        return prevState
    
    def _getInitialState(self, edits : [t.PerformerEdit]):
        easyMode = [edit for edit in edits if edit['operation'] == "CREATE"]
        if len(easyMode) > 0:
            return easyMode[0]
        
        # There is no CREATE edit, a known StashDB issue... Need to reverse the entire Edit chain
        firstState = deepcopy(self.performer)
        firstState.pop('merged_ids')

        edits.reverse()

        for edit in edits:
            # Reverse the Edit actions
            for attr in ["created","closed","name","disambiguation","gender","birthdate","ethnicity","country","eye_color","hair_color","height","cup_size","band_size","waist_size","hip_size","breast_type","career_start_year","career_end_year"]:
                if edit['details'].get(attr):
                    # This attribute has changed
                    firstState[attr] = edit['old_details'][attr]

            for attr in ["added_aliases", "added_tattoos", "added_piercings", "added_images", "added_urls"]:
                if edit['details'].get(attr):
                    for x in edit['details'].get(attr):
                        firstState[attr.split('_')[1]].remove(x)

            for attr in ["removed_aliases", "removed_tattoos", "removed_piercings", "removed_images", "removed_urls"]:
                if edit['details'].get(attr):
                    for x in edit['details'].get(attr):
                        firstState[attr.split('_')[1]].append(x)
        
        for attr in ["removed_aliases", "removed_tattoos", "removed_piercings", "removed_images", "removed_urls"]:
            firstState[attr] = []

        for attr in ["added_aliases", "added_tattoos", "added_piercings", "added_images", "added_urls"]:
            firstState[attr] = firstState[attr.split('_')[1]]

        edits.reverse()

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

    def compareAtDateTime(self, targetDate : datetime, compareTo : t.Performer) -> bool:
        """
        Returns True if the performer history at the target time is identical to compareTo
        """
        localPerf = self.getByDateTime(targetDate)

        for attr in ["name","gender","ethnicity","country","eye_color","hair_color","height","cup_size","band_size","waist_size","hip_size","breast_type","career_start_year","career_end_year"]:
            compareValue = compareTo.get(attr)
            localValue = localPerf.get(attr)


            if compareValue and localValue:
                if compareValue != localValue:
                    print(f"Compare {attr}: SOURCE:{localValue} and TARGET:{compareValue}")
                    return False
            elif compareValue or localValue:
                print(f"Only one {attr} exists !")
                return False
        
        # Handle birthday separately, it's a mess due to the var change
        compareValue = compareTo.get("birth_date", compareTo.get("birthdate"))
        localValue = localPerf.get("birth_date", localPerf.get("birthdate"))
        if compareValue and localValue:
            if compareValue != localValue:
                print(f"Compare birthday: SOURCE:{localValue} and TARGET:{compareValue}")
                return False
        elif compareValue and not localValue:
            print("Birthdate has been added to TARGET !")
            return False
            
        for attr in ["disambiguation","tatoos", "piercings"]:
            # These are not properly passed when scraping & uploading, so not taking them into account
            pass

        # Compare aliases
        compareValue = compareTo.get("aliases")
        localValue = localPerf.get("aliases")
        if compareValue and localValue:
            if set(compareValue) != set(localValue):
                print(f"Compare aliases: SOURCE:{localValue} and TARGET:{compareValue}")
                return False
        elif compareValue and not localValue:
            print(f"Alias has been added to TARGET !")
            return False
        
        localImgs = localPerf.get("images", [])
        compareImgs = compareTo.get("images", [])
        if len(compareImgs) > 1 and len(localImgs) != len(compareImgs):
            print("The list of images has been edited")
            return False

        return True
    
    def isIncomplete(self, targetDate : datetime, compareTo : t.Performer) -> bool:
        # Due to Stash / StashBox incompatibilities, some values are not properly parsed when creating performers manually. Try to detect if the performer needs to be fixed
        localPerf = self.getByDateTime(targetDate)

        for attr in ["disambiguation","tatoos", "piercings"]:
            compareValue = compareTo.get(attr)
            localValue = localPerf.get(attr)
            if localValue and not compareValue:
                # Value is missing
                return True

        localBirthdate = localPerf.get("birthdate", localPerf.get("birth_date"))
        compareBirthdate = compareTo.get("birthdate", compareTo.get("birth_date"))
        if type(localBirthdate) is dict:
            localBirthdate = localBirthdate["date"]
        if type(compareBirthdate) is dict:
            compareBirthdate = compareBirthdate["date"]
        if localBirthdate and not compareBirthdate:
                return True
        
        localImgs = localPerf.get("images", [])
        compareImgs = compareTo.get("images", [])
        if len(localImgs) > len(compareImgs):
            return True

        
        return False

    def hasUpdate(self, targetDate : datetime) -> bool:
        dates = list(self.performerStates.keys())
        dates.sort()
        id = bisect.bisect_right(dates,targetDate)

        return id < len(dates)