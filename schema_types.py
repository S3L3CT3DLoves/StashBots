from enum import Enum
from typing import Any, ClassVar, List, Optional, TypedDict, Union


## Scalars

Date = Any

DateTime = Any

Time = Any

Upload = Any

## Union Types

DraftData = Union['SceneDraft', 'PerformerDraft']

EditDetails = Union['PerformerEdit', 'SceneEdit', 'StudioEdit', 'TagEdit']

EditTarget = Union['Performer', 'Scene', 'Studio', 'Tag']

SceneDraftPerformer = Union['Performer', 'DraftEntity']

SceneDraftStudio = Union['Studio', 'DraftEntity']

SceneDraftTag = Union['Tag', 'DraftEntity']

BreastTypeEnum = Enum('BreastTypeEnum', 'NATURAL FAKE NA')


CriterionModifier = Enum('CriterionModifier', 'EQUALS NOT_EQUALS GREATER_THAN LESS_THAN IS_NULL NOT_NULL INCLUDES_ALL INCLUDES EXCLUDES')


DateAccuracyEnum = Enum('DateAccuracyEnum', 'YEAR MONTH DAY')


EditSortEnum = Enum('EditSortEnum', 'CREATED_AT UPDATED_AT CLOSED_AT')


EthnicityEnum = Enum('EthnicityEnum', 'CAUCASIAN BLACK ASIAN INDIAN LATIN MIDDLE_EASTERN MIXED OTHER')


EthnicityFilterEnum = Enum('EthnicityFilterEnum', 'UNKNOWN CAUCASIAN BLACK ASIAN INDIAN LATIN MIDDLE_EASTERN MIXED OTHER')


EyeColorEnum = Enum('EyeColorEnum', 'BLUE BROWN GREY GREEN HAZEL RED')


FavoriteFilter = Enum('FavoriteFilter', 'PERFORMER STUDIO ALL')


FingerprintAlgorithm = Enum('FingerprintAlgorithm', 'MD5 OSHASH PHASH')


GenderEnum = Enum('GenderEnum', 'MALE FEMALE TRANSGENDER_MALE TRANSGENDER_FEMALE INTERSEX NON_BINARY')


GenderFilterEnum = Enum('GenderFilterEnum', 'UNKNOWN MALE FEMALE TRANSGENDER_MALE TRANSGENDER_FEMALE INTERSEX NON_BINARY')


HairColorEnum = Enum('HairColorEnum', 'BLONDE BRUNETTE BLACK RED AUBURN GREY BALD VARIOUS OTHER')


OperationEnum = Enum('OperationEnum', 'CREATE MODIFY DESTROY MERGE')


PerformerSortEnum = Enum('PerformerSortEnum', 'NAME BIRTHDATE SCENE_COUNT CAREER_START_YEAR DEBUT LAST_SCENE CREATED_AT UPDATED_AT')


RoleEnum = Enum('RoleEnum', 'READ VOTE EDIT MODIFY ADMIN INVITE MANAGE_INVITES BOT')


SceneSortEnum = Enum('SceneSortEnum', 'TITLE DATE TRENDING CREATED_AT UPDATED_AT')


SortDirectionEnum = Enum('SortDirectionEnum', 'ASC DESC')


StudioSortEnum = Enum('StudioSortEnum', 'NAME CREATED_AT UPDATED_AT')


TagGroupEnum = Enum('TagGroupEnum', 'PEOPLE SCENE ACTION')


TagSortEnum = Enum('TagSortEnum', 'NAME CREATED_AT UPDATED_AT')


TargetTypeEnum = Enum('TargetTypeEnum', 'SCENE STUDIO PERFORMER TAG')


UserVotedFilterEnum = Enum('UserVotedFilterEnum', 'ABSTAIN ACCEPT REJECT NOT_VOTED')


ValidSiteTypeEnum = Enum('ValidSiteTypeEnum', 'PERFORMER SCENE STUDIO')


VoteStatusEnum = Enum('VoteStatusEnum', 'ACCEPTED REJECTED PENDING IMMEDIATE_ACCEPTED IMMEDIATE_REJECTED FAILED CANCELED')


VoteTypeEnum = Enum('VoteTypeEnum', 'ABSTAIN ACCEPT REJECT IMMEDIATE_ACCEPT IMMEDIATE_REJECT')


BodyModification = TypedDict('BodyModification', {
	'location': str,
	'description': Optional[str],
})


Draft = TypedDict('Draft', {
	'id': str,
	'created': 'Time',
	'expires': 'Time',
	'data': 'DraftData',
})


DraftEntity = TypedDict('DraftEntity', {
	'name': str,
	'id': Optional[str],
})


DraftFingerprint = TypedDict('DraftFingerprint', {
	'hash': str,
	'algorithm': 'FingerprintAlgorithm',
	'duration': int,
})


DraftSubmissionStatus = TypedDict('DraftSubmissionStatus', {
	'id': Optional[str],
})


Edit = TypedDict('Edit', {
	'id': str,
	'user': Optional['User'],
	'target': Optional['EditTarget'],
	'target_type': 'TargetTypeEnum',
	'merge_sources': List['EditTarget'],
	'operation': 'OperationEnum',
	'bot': bool,
	'details': Optional['EditDetails'],
	'old_details': Optional['EditDetails'],
	'options': Optional['PerformerEditOptions'],
	'comments': List['EditComment'],
	'votes': List['EditVote'],
	'vote_count': int,
	'destructive': bool,
	'status': 'VoteStatusEnum',
	'applied': bool,
	'created': 'Time',
	'updated': Optional['Time'],
	'closed': Optional['Time'],
	'expires': Optional['Time'],
})


EditComment = TypedDict('EditComment', {
	'id': str,
	'user': Optional['User'],
	'date': 'Time',
	'comment': str,
})


EditVote = TypedDict('EditVote', {
	'user': Optional['User'],
	'date': 'Time',
	'vote': 'VoteTypeEnum',
})


Fingerprint = TypedDict('Fingerprint', {
	'hash': str,
	'algorithm': 'FingerprintAlgorithm',
	'duration': int,
	'submissions': int,
	'created': 'Time',
	'updated': 'Time',
	'user_submitted': bool,
})


FuzzyDate = TypedDict('FuzzyDate', {
	'date': 'Date',
	'accuracy': 'DateAccuracyEnum',
})


Image = TypedDict('Image', {
	'id': str,
	'url': str,
	'width': int,
	'height': int,
})


Measurements = TypedDict('Measurements', {
	'cup_size': Optional[str],
	'band_size': Optional[int],
	'waist': Optional[int],
	'hip': Optional[int],
})


Mutation = TypedDict('Mutation', {
	'sceneCreate': 'SceneCreateMutationResult',
	'sceneUpdate': 'SceneUpdateMutationResult',
	'sceneDestroy': 'SceneDestroyMutationResult',
	'performerCreate': 'PerformerCreateMutationResult',
	'performerUpdate': 'PerformerUpdateMutationResult',
	'performerDestroy': 'PerformerDestroyMutationResult',
	'studioCreate': 'StudioCreateMutationResult',
	'studioUpdate': 'StudioUpdateMutationResult',
	'studioDestroy': 'StudioDestroyMutationResult',
	'tagCreate': 'TagCreateMutationResult',
	'tagUpdate': 'TagUpdateMutationResult',
	'tagDestroy': 'TagDestroyMutationResult',
	'userCreate': 'UserCreateMutationResult',
	'userUpdate': 'UserUpdateMutationResult',
	'userDestroy': 'UserDestroyMutationResult',
	'imageCreate': 'ImageCreateMutationResult',
	'imageDestroy': 'ImageDestroyMutationResult',
	'newUser': 'NewUserMutationResult',
	'activateNewUser': 'ActivateNewUserMutationResult',
	'generateInviteCode': 'GenerateInviteCodeMutationResult',
	'rescindInviteCode': 'RescindInviteCodeMutationResult',
	'grantInvite': 'GrantInviteMutationResult',
	'revokeInvite': 'RevokeInviteMutationResult',
	'tagCategoryCreate': 'TagCategoryCreateMutationResult',
	'tagCategoryUpdate': 'TagCategoryUpdateMutationResult',
	'tagCategoryDestroy': 'TagCategoryDestroyMutationResult',
	'siteCreate': 'SiteCreateMutationResult',
	'siteUpdate': 'SiteUpdateMutationResult',
	'siteDestroy': 'SiteDestroyMutationResult',
	'regenerateAPIKey': 'RegenerateAPIKeyMutationResult',
	'resetPassword': 'ResetPasswordMutationResult',
	'changePassword': 'ChangePasswordMutationResult',
	'sceneEdit': 'SceneEditMutationResult',
	'performerEdit': 'PerformerEditMutationResult',
	'studioEdit': 'StudioEditMutationResult',
	'tagEdit': 'TagEditMutationResult',
	'sceneEditUpdate': 'SceneEditUpdateMutationResult',
	'performerEditUpdate': 'PerformerEditUpdateMutationResult',
	'studioEditUpdate': 'StudioEditUpdateMutationResult',
	'tagEditUpdate': 'TagEditUpdateMutationResult',
	'editVote': 'EditVoteMutationResult',
	'editComment': 'EditCommentMutationResult',
	'applyEdit': 'ApplyEditMutationResult',
	'cancelEdit': 'CancelEditMutationResult',
	'submitFingerprint': 'SubmitFingerprintMutationResult',
	'submitSceneDraft': 'SubmitSceneDraftMutationResult',
	'submitPerformerDraft': 'SubmitPerformerDraftMutationResult',
	'destroyDraft': 'DestroyDraftMutationResult',
	'favoritePerformer': 'FavoritePerformerMutationResult',
	'favoriteStudio': 'FavoriteStudioMutationResult',
})


SceneCreateParams = TypedDict('SceneCreateParams', {
	'input': 'SceneCreateInput',
})


SceneCreateMutationResult = ClassVar[Optional['Scene']]


SceneUpdateParams = TypedDict('SceneUpdateParams', {
	'input': 'SceneUpdateInput',
})


SceneUpdateMutationResult = ClassVar[Optional['Scene']]


SceneDestroyParams = TypedDict('SceneDestroyParams', {
	'input': 'SceneDestroyInput',
})


SceneDestroyMutationResult = bool


PerformerCreateParams = TypedDict('PerformerCreateParams', {
	'input': 'PerformerCreateInput',
})


PerformerCreateMutationResult = ClassVar[Optional['Performer']]


PerformerUpdateParams = TypedDict('PerformerUpdateParams', {
	'input': 'PerformerUpdateInput',
})


PerformerUpdateMutationResult = ClassVar[Optional['Performer']]


PerformerDestroyParams = TypedDict('PerformerDestroyParams', {
	'input': 'PerformerDestroyInput',
})


PerformerDestroyMutationResult = bool


StudioCreateParams = TypedDict('StudioCreateParams', {
	'input': 'StudioCreateInput',
})


StudioCreateMutationResult = ClassVar[Optional['Studio']]


StudioUpdateParams = TypedDict('StudioUpdateParams', {
	'input': 'StudioUpdateInput',
})


StudioUpdateMutationResult = ClassVar[Optional['Studio']]


StudioDestroyParams = TypedDict('StudioDestroyParams', {
	'input': 'StudioDestroyInput',
})


StudioDestroyMutationResult = bool


TagCreateParams = TypedDict('TagCreateParams', {
	'input': 'TagCreateInput',
})


TagCreateMutationResult = ClassVar[Optional['Tag']]


TagUpdateParams = TypedDict('TagUpdateParams', {
	'input': 'TagUpdateInput',
})


TagUpdateMutationResult = ClassVar[Optional['Tag']]


TagDestroyParams = TypedDict('TagDestroyParams', {
	'input': 'TagDestroyInput',
})


TagDestroyMutationResult = bool


UserCreateParams = TypedDict('UserCreateParams', {
	'input': 'UserCreateInput',
})


UserCreateMutationResult = ClassVar[Optional['User']]


UserUpdateParams = TypedDict('UserUpdateParams', {
	'input': 'UserUpdateInput',
})


UserUpdateMutationResult = ClassVar[Optional['User']]


UserDestroyParams = TypedDict('UserDestroyParams', {
	'input': 'UserDestroyInput',
})


UserDestroyMutationResult = bool


ImageCreateParams = TypedDict('ImageCreateParams', {
	'input': 'ImageCreateInput',
})


ImageCreateMutationResult = ClassVar[Optional['Image']]


ImageDestroyParams = TypedDict('ImageDestroyParams', {
	'input': 'ImageDestroyInput',
})


ImageDestroyMutationResult = bool


NewUserParams = TypedDict('NewUserParams', {
	'input': 'NewUserInput',
})


NewUserMutationResult = str


ActivateNewUserParams = TypedDict('ActivateNewUserParams', {
	'input': 'ActivateNewUserInput',
})


ActivateNewUserMutationResult = ClassVar[Optional['User']]


GenerateInviteCodeMutationResult = str


RescindInviteCodeParams = TypedDict('RescindInviteCodeParams', {
	'code': str,
})


RescindInviteCodeMutationResult = bool


GrantInviteParams = TypedDict('GrantInviteParams', {
	'input': 'GrantInviteInput',
})


GrantInviteMutationResult = int


RevokeInviteParams = TypedDict('RevokeInviteParams', {
	'input': 'RevokeInviteInput',
})


RevokeInviteMutationResult = int


TagCategoryCreateParams = TypedDict('TagCategoryCreateParams', {
	'input': 'TagCategoryCreateInput',
})


TagCategoryCreateMutationResult = ClassVar[Optional['TagCategory']]


TagCategoryUpdateParams = TypedDict('TagCategoryUpdateParams', {
	'input': 'TagCategoryUpdateInput',
})


TagCategoryUpdateMutationResult = ClassVar[Optional['TagCategory']]


TagCategoryDestroyParams = TypedDict('TagCategoryDestroyParams', {
	'input': 'TagCategoryDestroyInput',
})


TagCategoryDestroyMutationResult = bool


SiteCreateParams = TypedDict('SiteCreateParams', {
	'input': 'SiteCreateInput',
})


SiteCreateMutationResult = ClassVar[Optional['Site']]


SiteUpdateParams = TypedDict('SiteUpdateParams', {
	'input': 'SiteUpdateInput',
})


SiteUpdateMutationResult = ClassVar[Optional['Site']]


SiteDestroyParams = TypedDict('SiteDestroyParams', {
	'input': 'SiteDestroyInput',
})


SiteDestroyMutationResult = bool


RegenerateAPIKeyParams = TypedDict('RegenerateAPIKeyParams', {
	'userID': Optional[str],
})


RegenerateAPIKeyMutationResult = str


ResetPasswordParams = TypedDict('ResetPasswordParams', {
	'input': 'ResetPasswordInput',
})


ResetPasswordMutationResult = bool


ChangePasswordParams = TypedDict('ChangePasswordParams', {
	'input': 'UserChangePasswordInput',
})


ChangePasswordMutationResult = bool


SceneEditParams = TypedDict('SceneEditParams', {
	'input': 'SceneEditInput',
})


SceneEditMutationResult = ClassVar['Edit']


PerformerEditParams = TypedDict('PerformerEditParams', {
	'input': 'PerformerEditInput',
})


PerformerEditMutationResult = ClassVar['Edit']


StudioEditParams = TypedDict('StudioEditParams', {
	'input': 'StudioEditInput',
})


StudioEditMutationResult = ClassVar['Edit']


TagEditParams = TypedDict('TagEditParams', {
	'input': 'TagEditInput',
})


TagEditMutationResult = ClassVar['Edit']


SceneEditUpdateParams = TypedDict('SceneEditUpdateParams', {
	'id': str,
	'input': 'SceneEditInput',
})


SceneEditUpdateMutationResult = ClassVar['Edit']


PerformerEditUpdateParams = TypedDict('PerformerEditUpdateParams', {
	'id': str,
	'input': 'PerformerEditInput',
})


PerformerEditUpdateMutationResult = ClassVar['Edit']


StudioEditUpdateParams = TypedDict('StudioEditUpdateParams', {
	'id': str,
	'input': 'StudioEditInput',
})


StudioEditUpdateMutationResult = ClassVar['Edit']


TagEditUpdateParams = TypedDict('TagEditUpdateParams', {
	'id': str,
	'input': 'TagEditInput',
})


TagEditUpdateMutationResult = ClassVar['Edit']


EditVoteParams = TypedDict('EditVoteParams', {
	'input': 'EditVoteInput',
})


EditVoteMutationResult = ClassVar['Edit']


EditCommentParams = TypedDict('EditCommentParams', {
	'input': 'EditCommentInput',
})


EditCommentMutationResult = ClassVar['Edit']


ApplyEditParams = TypedDict('ApplyEditParams', {
	'input': 'ApplyEditInput',
})


ApplyEditMutationResult = ClassVar['Edit']


CancelEditParams = TypedDict('CancelEditParams', {
	'input': 'CancelEditInput',
})


CancelEditMutationResult = ClassVar['Edit']


SubmitFingerprintParams = TypedDict('SubmitFingerprintParams', {
	'input': 'FingerprintSubmission',
})


SubmitFingerprintMutationResult = bool


SubmitSceneDraftParams = TypedDict('SubmitSceneDraftParams', {
	'input': 'SceneDraftInput',
})


SubmitSceneDraftMutationResult = ClassVar['DraftSubmissionStatus']


SubmitPerformerDraftParams = TypedDict('SubmitPerformerDraftParams', {
	'input': 'PerformerDraftInput',
})


SubmitPerformerDraftMutationResult = ClassVar['DraftSubmissionStatus']


DestroyDraftParams = TypedDict('DestroyDraftParams', {
	'id': str,
})


DestroyDraftMutationResult = bool


FavoritePerformerParams = TypedDict('FavoritePerformerParams', {
	'id': str,
	'favorite': bool,
})


FavoritePerformerMutationResult = bool


FavoriteStudioParams = TypedDict('FavoriteStudioParams', {
	'id': str,
	'favorite': bool,
})


FavoriteStudioMutationResult = bool


Performer = TypedDict('Performer', {
	'id': str,
	'name': str,
	'disambiguation': Optional[str],
	'aliases': List[str],
	'gender': Optional['GenderEnum'],
	'urls': List['URL'],
	'birthdate': Optional['FuzzyDate'],
	'birth_date': Optional[str],
	'age': Optional[int],
	'ethnicity': Optional['EthnicityEnum'],
	'country': Optional[str],
	'eye_color': Optional['EyeColorEnum'],
	'hair_color': Optional['HairColorEnum'],
	'height': Optional[int],
	'measurements': 'Measurements',
	'cup_size': Optional[str],
	'band_size': Optional[int],
	'waist_size': Optional[int],
	'hip_size': Optional[int],
	'breast_type': Optional['BreastTypeEnum'],
	'career_start_year': Optional[int],
	'career_end_year': Optional[int],
	'tattoos': Optional[List['BodyModification']],
	'piercings': Optional[List['BodyModification']],
	'images': List['Image'],
	'deleted': bool,
	'edits': List['Edit'],
	'scene_count': int,
	'scenes': List['Scene'],
	'merged_ids': List[str],
	'studios': List['PerformerStudio'],
	'is_favorite': bool,
	'created': 'Time',
	'updated': 'Time',
})


PerformerAppearance = TypedDict('PerformerAppearance', {
	'performer': 'Performer',
	'as': Optional[str],
})


PerformerDraft = TypedDict('PerformerDraft', {
	'id': Optional[str],
	'name': str,
	'aliases': Optional[str],
	'gender': Optional[str],
	'birthdate': Optional[str],
	'urls': Optional[List[str]],
	'ethnicity': Optional[str],
	'country': Optional[str],
	'eye_color': Optional[str],
	'hair_color': Optional[str],
	'height': Optional[str],
	'measurements': Optional[str],
	'breast_type': Optional[str],
	'tattoos': Optional[str],
	'piercings': Optional[str],
	'career_start_year': Optional[int],
	'career_end_year': Optional[int],
	'image': Optional['Image'],
})


PerformerEdit = TypedDict('PerformerEdit', {
	'name': Optional[str],
	'disambiguation': Optional[str],
	'added_aliases': Optional[List[str]],
	'removed_aliases': Optional[List[str]],
	'gender': Optional['GenderEnum'],
	'added_urls': Optional[List['URL']],
	'removed_urls': Optional[List['URL']],
	'birthdate': Optional[str],
	'ethnicity': Optional['EthnicityEnum'],
	'country': Optional[str],
	'eye_color': Optional['EyeColorEnum'],
	'hair_color': Optional['HairColorEnum'],
	'height': Optional[int],
	'cup_size': Optional[str],
	'band_size': Optional[int],
	'waist_size': Optional[int],
	'hip_size': Optional[int],
	'breast_type': Optional['BreastTypeEnum'],
	'career_start_year': Optional[int],
	'career_end_year': Optional[int],
	'added_tattoos': Optional[List['BodyModification']],
	'removed_tattoos': Optional[List['BodyModification']],
	'added_piercings': Optional[List['BodyModification']],
	'removed_piercings': Optional[List['BodyModification']],
	'added_images': Optional[List['Image']],
	'removed_images': Optional[List['Image']],
	'draft_id': Optional[str],
	'aliases': List[str],
	'urls': List['URL'],
	'images': List['Image'],
	'tattoos': List['BodyModification'],
	'piercings': List['BodyModification'],
})


PerformerEditOptions = TypedDict('PerformerEditOptions', {
	'set_modify_aliases': bool,
	'set_merge_aliases': bool,
})


PerformerStudio = TypedDict('PerformerStudio', {
	'studio': 'Studio',
	'scene_count': int,
})


Query = TypedDict('Query', {
	'findPerformer': 'FindPerformerQueryResult',
	'queryPerformers': 'QueryPerformersQueryResult',
	'findStudio': 'FindStudioQueryResult',
	'queryStudios': 'QueryStudiosQueryResult',
	'findTag': 'FindTagQueryResult',
	'queryTags': 'QueryTagsQueryResult',
	'findTagCategory': 'FindTagCategoryQueryResult',
	'queryTagCategories': 'QueryTagCategoriesQueryResult',
	'findScene': 'FindSceneQueryResult',
	'findSceneByFingerprint': 'FindSceneByFingerprintQueryResult',
	'findScenesByFingerprints': 'FindScenesByFingerprintsQueryResult',
	'findScenesByFullFingerprints': 'FindScenesByFullFingerprintsQueryResult',
	'findScenesBySceneFingerprints': 'FindScenesBySceneFingerprintsQueryResult',
	'queryScenes': 'QueryScenesQueryResult',
	'findSite': 'FindSiteQueryResult',
	'querySites': 'QuerySitesQueryResult',
	'findEdit': 'FindEditQueryResult',
	'queryEdits': 'QueryEditsQueryResult',
	'findUser': 'FindUserQueryResult',
	'queryUsers': 'QueryUsersQueryResult',
	'me': 'MeQueryResult',
	'searchPerformer': 'SearchPerformerQueryResult',
	'searchScene': 'SearchSceneQueryResult',
	'searchTag': 'SearchTagQueryResult',
	'findDraft': 'FindDraftQueryResult',
	'findDrafts': 'FindDraftsQueryResult',
	'queryExistingScene': 'QueryExistingSceneQueryResult',
	'version': 'VersionQueryResult',
	'getConfig': 'GetConfigQueryResult',
})


FindPerformerParams = TypedDict('FindPerformerParams', {
	'id': str,
})


FindPerformerQueryResult = ClassVar[Optional['Performer']]


QueryPerformersParams = TypedDict('QueryPerformersParams', {
	'input': 'PerformerQueryInput',
})


QueryPerformersQueryResult = ClassVar['QueryPerformersResultType']


FindStudioParams = TypedDict('FindStudioParams', {
	'id': Optional[str],
	'name': Optional[str],
})


FindStudioQueryResult = ClassVar[Optional['Studio']]


QueryStudiosParams = TypedDict('QueryStudiosParams', {
	'input': 'StudioQueryInput',
})


QueryStudiosQueryResult = ClassVar['QueryStudiosResultType']


FindTagParams = TypedDict('FindTagParams', {
	'id': Optional[str],
	'name': Optional[str],
})


FindTagQueryResult = ClassVar[Optional['Tag']]


QueryTagsParams = TypedDict('QueryTagsParams', {
	'input': 'TagQueryInput',
})


QueryTagsQueryResult = ClassVar['QueryTagsResultType']


FindTagCategoryParams = TypedDict('FindTagCategoryParams', {
	'id': str,
})


FindTagCategoryQueryResult = ClassVar[Optional['TagCategory']]


QueryTagCategoriesQueryResult = ClassVar['QueryTagCategoriesResultType']


FindSceneParams = TypedDict('FindSceneParams', {
	'id': str,
})


FindSceneQueryResult = ClassVar[Optional['Scene']]


FindSceneByFingerprintParams = TypedDict('FindSceneByFingerprintParams', {
	'fingerprint': 'FingerprintQueryInput',
})


FindSceneByFingerprintQueryResult = ClassVar[List['Scene']]


FindScenesByFingerprintsParams = TypedDict('FindScenesByFingerprintsParams', {
	'fingerprints': List[str],
})


FindScenesByFingerprintsQueryResult = ClassVar[List['Scene']]


FindScenesByFullFingerprintsParams = TypedDict('FindScenesByFullFingerprintsParams', {
	'fingerprints': List['FingerprintQueryInput'],
})


FindScenesByFullFingerprintsQueryResult = ClassVar[List['Scene']]


FindScenesBySceneFingerprintsParams = TypedDict('FindScenesBySceneFingerprintsParams', {
	'fingerprints': List[List['FingerprintQueryInput']],
})


FindScenesBySceneFingerprintsQueryResult = ClassVar[List[List['Scene']]]


QueryScenesParams = TypedDict('QueryScenesParams', {
	'input': 'SceneQueryInput',
})


QueryScenesQueryResult = ClassVar['QueryScenesResultType']


FindSiteParams = TypedDict('FindSiteParams', {
	'id': str,
})


FindSiteQueryResult = ClassVar[Optional['Site']]


QuerySitesQueryResult = ClassVar['QuerySitesResultType']


FindEditParams = TypedDict('FindEditParams', {
	'id': str,
})


FindEditQueryResult = ClassVar[Optional['Edit']]


QueryEditsParams = TypedDict('QueryEditsParams', {
	'input': 'EditQueryInput',
})


QueryEditsQueryResult = ClassVar['QueryEditsResultType']


FindUserParams = TypedDict('FindUserParams', {
	'id': Optional[str],
	'username': Optional[str],
})


FindUserQueryResult = ClassVar[Optional['User']]


QueryUsersParams = TypedDict('QueryUsersParams', {
	'input': 'UserQueryInput',
})


QueryUsersQueryResult = ClassVar['QueryUsersResultType']


MeQueryResult = ClassVar[Optional['User']]


SearchPerformerParams = TypedDict('SearchPerformerParams', {
	'term': str,
	'limit': Optional[int],
})


SearchPerformerQueryResult = ClassVar[List['Performer']]


SearchSceneParams = TypedDict('SearchSceneParams', {
	'term': str,
	'limit': Optional[int],
})


SearchSceneQueryResult = ClassVar[List['Scene']]


SearchTagParams = TypedDict('SearchTagParams', {
	'term': str,
	'limit': Optional[int],
})


SearchTagQueryResult = ClassVar[List['Tag']]


FindDraftParams = TypedDict('FindDraftParams', {
	'id': str,
})


FindDraftQueryResult = ClassVar[Optional['Draft']]


FindDraftsQueryResult = ClassVar[List['Draft']]


QueryExistingSceneParams = TypedDict('QueryExistingSceneParams', {
	'input': 'QueryExistingSceneInput',
})


QueryExistingSceneQueryResult = ClassVar['QueryExistingSceneResult']


VersionQueryResult = ClassVar['Version']


GetConfigQueryResult = ClassVar['StashBoxConfig']


QueryEditsResultType = TypedDict('QueryEditsResultType', {
	'count': int,
	'edits': List['Edit'],
})


QueryExistingSceneResult = TypedDict('QueryExistingSceneResult', {
	'edits': List['Edit'],
	'scenes': List['Scene'],
})


QueryPerformersResultType = TypedDict('QueryPerformersResultType', {
	'count': int,
	'performers': List['Performer'],
})


QueryScenesResultType = TypedDict('QueryScenesResultType', {
	'count': int,
	'scenes': List['Scene'],
})


QuerySitesResultType = TypedDict('QuerySitesResultType', {
	'count': int,
	'sites': List['Site'],
})


QueryStudiosResultType = TypedDict('QueryStudiosResultType', {
	'count': int,
	'studios': List['Studio'],
})


QueryTagCategoriesResultType = TypedDict('QueryTagCategoriesResultType', {
	'count': int,
	'tag_categories': List['TagCategory'],
})


QueryTagsResultType = TypedDict('QueryTagsResultType', {
	'count': int,
	'tags': List['Tag'],
})


QueryUsersResultType = TypedDict('QueryUsersResultType', {
	'count': int,
	'users': List['User'],
})


Scene = TypedDict('Scene', {
	'id': str,
	'title': Optional[str],
	'details': Optional[str],
	'date': Optional[str],
	'release_date': Optional[str],
	'urls': List['URL'],
	'studio': Optional['Studio'],
	'tags': List['Tag'],
	'images': List['Image'],
	'performers': List['PerformerAppearance'],
	'fingerprints': List['Fingerprint'],
	'duration': Optional[int],
	'director': Optional[str],
	'code': Optional[str],
	'deleted': bool,
	'edits': List['Edit'],
	'created': 'Time',
	'updated': 'Time',
})


SceneDraft = TypedDict('SceneDraft', {
	'id': Optional[str],
	'title': Optional[str],
	'code': Optional[str],
	'details': Optional[str],
	'director': Optional[str],
	'url': Optional['URL'],
	'date': Optional[str],
	'studio': Optional['SceneDraftStudio'],
	'performers': List['SceneDraftPerformer'],
	'tags': Optional[List['SceneDraftTag']],
	'image': Optional['Image'],
	'fingerprints': List['DraftFingerprint'],
})


SceneEdit = TypedDict('SceneEdit', {
	'title': Optional[str],
	'details': Optional[str],
	'added_urls': Optional[List['URL']],
	'removed_urls': Optional[List['URL']],
	'date': Optional[str],
	'studio': Optional['Studio'],
	'added_performers': Optional[List['PerformerAppearance']],
	'removed_performers': Optional[List['PerformerAppearance']],
	'added_tags': Optional[List['Tag']],
	'removed_tags': Optional[List['Tag']],
	'added_images': Optional[List['Image']],
	'removed_images': Optional[List['Image']],
	'added_fingerprints': Optional[List['Fingerprint']],
	'removed_fingerprints': Optional[List['Fingerprint']],
	'duration': Optional[int],
	'director': Optional[str],
	'code': Optional[str],
	'draft_id': Optional[str],
	'urls': List['URL'],
	'performers': List['PerformerAppearance'],
	'tags': List['Tag'],
	'images': List['Image'],
	'fingerprints': List['Fingerprint'],
})


Site = TypedDict('Site', {
	'id': str,
	'name': str,
	'description': Optional[str],
	'url': Optional[str],
	'regex': Optional[str],
	'valid_types': List['ValidSiteTypeEnum'],
	'icon': str,
	'created': 'Time',
	'updated': 'Time',
})


StashBoxConfig = TypedDict('StashBoxConfig', {
	'host_url': str,
	'require_invite': bool,
	'require_activation': bool,
	'vote_promotion_threshold': Optional[int],
	'vote_application_threshold': int,
	'voting_period': int,
	'min_destructive_voting_period': int,
	'vote_cron_interval': str,
})


Studio = TypedDict('Studio', {
	'id': str,
	'name': str,
	'urls': List['URL'],
	'parent': Optional['Studio'],
	'child_studios': List['Studio'],
	'images': List['Image'],
	'deleted': bool,
	'is_favorite': bool,
	'created': 'Time',
	'updated': 'Time',
	'performers': 'QueryPerformersResultType',
})


StudioEdit = TypedDict('StudioEdit', {
	'name': Optional[str],
	'added_urls': Optional[List['URL']],
	'removed_urls': Optional[List['URL']],
	'parent': Optional['Studio'],
	'added_images': Optional[List['Image']],
	'removed_images': Optional[List['Image']],
	'images': List['Image'],
	'urls': List['URL'],
})


Tag = TypedDict('Tag', {
	'id': str,
	'name': str,
	'description': Optional[str],
	'aliases': List[str],
	'deleted': bool,
	'edits': List['Edit'],
	'category': Optional['TagCategory'],
	'created': 'Time',
	'updated': 'Time',
})


TagCategory = TypedDict('TagCategory', {
	'id': str,
	'name': str,
	'group': 'TagGroupEnum',
	'description': Optional[str],
})


TagEdit = TypedDict('TagEdit', {
	'name': Optional[str],
	'description': Optional[str],
	'added_aliases': Optional[List[str]],
	'removed_aliases': Optional[List[str]],
	'category': Optional['TagCategory'],
	'aliases': List[str],
})


URL = TypedDict('URL', {
	'url': str,
	'type': str,
	'site': 'Site',
})


User = TypedDict('User', {
	'id': str,
	'name': str,
	'roles': Optional[List['RoleEnum']],
	'email': Optional[str],
	'api_key': Optional[str],
	'vote_count': 'UserVoteCount',
	'edit_count': 'UserEditCount',
	'api_calls': int,
	'invited_by': Optional['User'],
	'invite_tokens': Optional[int],
	'active_invite_codes': Optional[List[str]],
})


UserEditCount = TypedDict('UserEditCount', {
	'accepted': int,
	'rejected': int,
	'pending': int,
	'immediate_accepted': int,
	'immediate_rejected': int,
	'failed': int,
	'canceled': int,
})


UserVoteCount = TypedDict('UserVoteCount', {
	'abstain': int,
	'accept': int,
	'reject': int,
	'immediate_accept': int,
	'immediate_reject': int,
})


Version = TypedDict('Version', {
	'hash': str,
	'build_time': str,
	'build_type': str,
	'version': str,
})


ActivateNewUserInput = TypedDict('ActivateNewUserInput', {
	'name': str,
	'email': str,
	'activation_key': str,
	'password': str,
})


ApplyEditInput = TypedDict('ApplyEditInput', {
	'id': str,
})


BodyModificationCriterionInput = TypedDict('BodyModificationCriterionInput', {
	'location': Optional[str],
	'description': Optional[str],
	'modifier': 'CriterionModifier',
})


BodyModificationInput = TypedDict('BodyModificationInput', {
	'location': str,
	'description': Optional[str],
})


BreastTypeCriterionInput = TypedDict('BreastTypeCriterionInput', {
	'value': Optional['BreastTypeEnum'],
	'modifier': 'CriterionModifier',
})


CancelEditInput = TypedDict('CancelEditInput', {
	'id': str,
})


DateCriterionInput = TypedDict('DateCriterionInput', {
	'value': 'Date',
	'modifier': 'CriterionModifier',
})


DraftEntityInput = TypedDict('DraftEntityInput', {
	'name': str,
	'id': Optional[str],
})


EditCommentInput = TypedDict('EditCommentInput', {
	'id': str,
	'comment': str,
})


EditInput = TypedDict('EditInput', {
	'id': Optional[str],
	'operation': 'OperationEnum',
	'merge_source_ids': Optional[List[str]],
	'comment': Optional[str],
	'bot': Optional[bool],
})


EditQueryInput = TypedDict('EditQueryInput', {
	'user_id': Optional[str],
	'status': Optional['VoteStatusEnum'],
	'operation': Optional['OperationEnum'],
	'vote_count': Optional['IntCriterionInput'],
	'applied': Optional[bool],
	'target_type': Optional['TargetTypeEnum'],
	'target_id': Optional[str],
	'is_favorite': Optional[bool],
	'voted': Optional['UserVotedFilterEnum'],
	'is_bot': Optional[bool],
	'page': int,
	'per_page': int,
	'direction': 'SortDirectionEnum',
	'sort': 'EditSortEnum',
})


EditVoteInput = TypedDict('EditVoteInput', {
	'id': str,
	'vote': 'VoteTypeEnum',
})


EyeColorCriterionInput = TypedDict('EyeColorCriterionInput', {
	'value': Optional['EyeColorEnum'],
	'modifier': 'CriterionModifier',
})


FingerprintEditInput = TypedDict('FingerprintEditInput', {
	'user_ids': Optional[List[str]],
	'hash': str,
	'algorithm': 'FingerprintAlgorithm',
	'duration': int,
	'created': 'Time',
	'submissions': Optional[int],
	'updated': Optional['Time'],
})


FingerprintInput = TypedDict('FingerprintInput', {
	'user_ids': Optional[List[str]],
	'hash': str,
	'algorithm': 'FingerprintAlgorithm',
	'duration': int,
})


FingerprintQueryInput = TypedDict('FingerprintQueryInput', {
	'hash': str,
	'algorithm': 'FingerprintAlgorithm',
})


FingerprintSubmission = TypedDict('FingerprintSubmission', {
	'scene_id': str,
	'fingerprint': 'FingerprintInput',
	'unmatch': Optional[bool],
})


GrantInviteInput = TypedDict('GrantInviteInput', {
	'user_id': str,
	'amount': int,
})


HairColorCriterionInput = TypedDict('HairColorCriterionInput', {
	'value': Optional['HairColorEnum'],
	'modifier': 'CriterionModifier',
})


IDCriterionInput = TypedDict('IDCriterionInput', {
	'value': List[str],
	'modifier': 'CriterionModifier',
})


ImageCreateInput = TypedDict('ImageCreateInput', {
	'url': Optional[str],
	'file': Optional['Upload'],
})


ImageDestroyInput = TypedDict('ImageDestroyInput', {
	'id': str,
})


ImageUpdateInput = TypedDict('ImageUpdateInput', {
	'id': str,
	'url': Optional[str],
})


IntCriterionInput = TypedDict('IntCriterionInput', {
	'value': int,
	'modifier': 'CriterionModifier',
})


MultiIDCriterionInput = TypedDict('MultiIDCriterionInput', {
	'value': Optional[List[str]],
	'modifier': 'CriterionModifier',
})


MultiStringCriterionInput = TypedDict('MultiStringCriterionInput', {
	'value': List[str],
	'modifier': 'CriterionModifier',
})


NewUserInput = TypedDict('NewUserInput', {
	'email': str,
	'invite_key': Optional[str],
})


PerformerAppearanceInput = TypedDict('PerformerAppearanceInput', {
	'performer_id': str,
	'as': Optional[str],
})


PerformerCreateInput = TypedDict('PerformerCreateInput', {
	'name': str,
	'disambiguation': Optional[str],
	'aliases': Optional[List[str]],
	'gender': Optional['GenderEnum'],
	'urls': Optional[List['URLInput']],
	'birthdate': Optional[str],
	'ethnicity': Optional['EthnicityEnum'],
	'country': Optional[str],
	'eye_color': Optional['EyeColorEnum'],
	'hair_color': Optional['HairColorEnum'],
	'height': Optional[int],
	'cup_size': Optional[str],
	'band_size': Optional[int],
	'waist_size': Optional[int],
	'hip_size': Optional[int],
	'breast_type': Optional['BreastTypeEnum'],
	'career_start_year': Optional[int],
	'career_end_year': Optional[int],
	'tattoos': Optional[List['BodyModificationInput']],
	'piercings': Optional[List['BodyModificationInput']],
	'image_ids': Optional[List[str]],
	'draft_id': Optional[str],
})


PerformerDestroyInput = TypedDict('PerformerDestroyInput', {
	'id': str,
})


PerformerDraftInput = TypedDict('PerformerDraftInput', {
	'id': Optional[str],
	'name': str,
	'aliases': Optional[str],
	'gender': Optional['GenderEnum'],
	'birthdate': Optional[str],
	'urls': Optional[List['URLInput']],
	'ethnicity': Optional['EthnicityEnum'],
	'country': Optional[str],
	'eye_color': Optional['EyeColorEnum'],
	'hair_color': Optional[str],
	'height': Optional[str],
	'measurements': Optional[str],
	'breast_type': Optional['BreastTypeEnum'],
	'tattoos': Optional[List['BodyModificationInput']],
	'piercings': Optional[List['BodyModificationInput']],
	'career_start_year': Optional[int],
	'career_end_year': Optional[int],
	'image': Optional['Upload'],
})


PerformerEditDetailsInput = TypedDict('PerformerEditDetailsInput', {
	'name': Optional[str],
	'disambiguation': Optional[str],
	'aliases': Optional[List[str]],
	'gender': Optional['GenderEnum'],
	'urls': Optional[List['URLInput']],
	'birthdate': Optional[str],
	'ethnicity': Optional['EthnicityEnum'],
	'country': Optional[str],
	'eye_color': Optional['EyeColorEnum'],
	'hair_color': Optional['HairColorEnum'],
	'height': Optional[int],
	'cup_size': Optional[str],
	'band_size': Optional[int],
	'waist_size': Optional[int],
	'hip_size': Optional[int],
	'breast_type': Optional['BreastTypeEnum'],
	'career_start_year': Optional[int],
	'career_end_year': Optional[int],
	'tattoos': Optional[List['BodyModificationInput']],
	'piercings': Optional[List['BodyModificationInput']],
	'image_ids': Optional[List[str]],
	'draft_id': Optional[str],
})


PerformerEditInput = TypedDict('PerformerEditInput', {
	'edit': 'EditInput',
	'details': Optional['PerformerEditDetailsInput'],
	'options': Optional['PerformerEditOptionsInput'],
})


PerformerEditOptionsInput = TypedDict('PerformerEditOptionsInput', {
	'set_modify_aliases': Optional[bool],
	'set_merge_aliases': Optional[bool],
})


PerformerQueryInput = TypedDict('PerformerQueryInput', {
	'names': Optional[str],
	'name': Optional[str],
	'alias': Optional[str],
	'disambiguation': Optional['StringCriterionInput'],
	'gender': Optional['GenderFilterEnum'],
	'url': Optional[str],
	'birthdate': Optional['DateCriterionInput'],
	'birth_year': Optional['IntCriterionInput'],
	'age': Optional['IntCriterionInput'],
	'ethnicity': Optional['EthnicityFilterEnum'],
	'country': Optional['StringCriterionInput'],
	'eye_color': Optional['EyeColorCriterionInput'],
	'hair_color': Optional['HairColorCriterionInput'],
	'height': Optional['IntCriterionInput'],
	'cup_size': Optional['StringCriterionInput'],
	'band_size': Optional['IntCriterionInput'],
	'waist_size': Optional['IntCriterionInput'],
	'hip_size': Optional['IntCriterionInput'],
	'breast_type': Optional['BreastTypeCriterionInput'],
	'career_start_year': Optional['IntCriterionInput'],
	'career_end_year': Optional['IntCriterionInput'],
	'tattoos': Optional['BodyModificationCriterionInput'],
	'piercings': Optional['BodyModificationCriterionInput'],
	'is_favorite': Optional[bool],
	'performed_with': Optional[str],
	'studio_id': Optional[str],
	'page': int,
	'per_page': int,
	'direction': 'SortDirectionEnum',
	'sort': 'PerformerSortEnum',
})


PerformerScenesInput = TypedDict('PerformerScenesInput', {
	'performed_with': Optional[str],
	'studio_id': Optional[str],
	'tags': Optional['MultiIDCriterionInput'],
})


PerformerUpdateInput = TypedDict('PerformerUpdateInput', {
	'id': str,
	'name': Optional[str],
	'disambiguation': Optional[str],
	'aliases': Optional[List[str]],
	'gender': Optional['GenderEnum'],
	'urls': Optional[List['URLInput']],
	'birthdate': Optional[str],
	'ethnicity': Optional['EthnicityEnum'],
	'country': Optional[str],
	'eye_color': Optional['EyeColorEnum'],
	'hair_color': Optional['HairColorEnum'],
	'height': Optional[int],
	'cup_size': Optional[str],
	'band_size': Optional[int],
	'waist_size': Optional[int],
	'hip_size': Optional[int],
	'breast_type': Optional['BreastTypeEnum'],
	'career_start_year': Optional[int],
	'career_end_year': Optional[int],
	'tattoos': Optional[List['BodyModificationInput']],
	'piercings': Optional[List['BodyModificationInput']],
	'image_ids': Optional[List[str]],
})


QueryExistingSceneInput = TypedDict('QueryExistingSceneInput', {
	'title': Optional[str],
	'studio_id': Optional[str],
	'fingerprints': List['FingerprintInput'],
})


ResetPasswordInput = TypedDict('ResetPasswordInput', {
	'email': str,
})


RevokeInviteInput = TypedDict('RevokeInviteInput', {
	'user_id': str,
	'amount': int,
})


RoleCriterionInput = TypedDict('RoleCriterionInput', {
	'value': List['RoleEnum'],
	'modifier': 'CriterionModifier',
})


SceneCreateInput = TypedDict('SceneCreateInput', {
	'title': Optional[str],
	'details': Optional[str],
	'urls': Optional[List['URLInput']],
	'date': str,
	'studio_id': Optional[str],
	'performers': Optional[List['PerformerAppearanceInput']],
	'tag_ids': Optional[List[str]],
	'image_ids': Optional[List[str]],
	'fingerprints': List['FingerprintEditInput'],
	'duration': Optional[int],
	'director': Optional[str],
	'code': Optional[str],
})


SceneDestroyInput = TypedDict('SceneDestroyInput', {
	'id': str,
})


SceneDraftInput = TypedDict('SceneDraftInput', {
	'id': Optional[str],
	'title': Optional[str],
	'code': Optional[str],
	'details': Optional[str],
	'director': Optional[str],
	'url': Optional[str],
	'date': Optional[str],
	'studio': Optional['DraftEntityInput'],
	'performers': List['DraftEntityInput'],
	'tags': Optional[List['DraftEntityInput']],
	'image': Optional['Upload'],
	'fingerprints': List['FingerprintInput'],
})


SceneEditDetailsInput = TypedDict('SceneEditDetailsInput', {
	'title': Optional[str],
	'details': Optional[str],
	'urls': Optional[List['URLInput']],
	'date': Optional[str],
	'studio_id': Optional[str],
	'performers': Optional[List['PerformerAppearanceInput']],
	'tag_ids': Optional[List[str]],
	'image_ids': Optional[List[str]],
	'duration': Optional[int],
	'director': Optional[str],
	'code': Optional[str],
	'fingerprints': Optional[List['FingerprintInput']],
	'draft_id': Optional[str],
})


SceneEditInput = TypedDict('SceneEditInput', {
	'edit': 'EditInput',
	'details': Optional['SceneEditDetailsInput'],
})


SceneQueryInput = TypedDict('SceneQueryInput', {
	'text': Optional[str],
	'title': Optional[str],
	'url': Optional[str],
	'date': Optional['DateCriterionInput'],
	'studios': Optional['MultiIDCriterionInput'],
	'parentStudio': Optional[str],
	'tags': Optional['MultiIDCriterionInput'],
	'performers': Optional['MultiIDCriterionInput'],
	'alias': Optional['StringCriterionInput'],
	'fingerprints': Optional['MultiStringCriterionInput'],
	'favorites': Optional['FavoriteFilter'],
	'has_fingerprint_submissions': Optional[bool],
	'page': int,
	'per_page': int,
	'direction': 'SortDirectionEnum',
	'sort': 'SceneSortEnum',
})


SceneUpdateInput = TypedDict('SceneUpdateInput', {
	'id': str,
	'title': Optional[str],
	'details': Optional[str],
	'urls': Optional[List['URLInput']],
	'date': Optional[str],
	'studio_id': Optional[str],
	'performers': Optional[List['PerformerAppearanceInput']],
	'tag_ids': Optional[List[str]],
	'image_ids': Optional[List[str]],
	'fingerprints': Optional[List['FingerprintEditInput']],
	'duration': Optional[int],
	'director': Optional[str],
	'code': Optional[str],
})


SiteCreateInput = TypedDict('SiteCreateInput', {
	'name': str,
	'description': Optional[str],
	'url': Optional[str],
	'regex': Optional[str],
	'valid_types': List['ValidSiteTypeEnum'],
})


SiteDestroyInput = TypedDict('SiteDestroyInput', {
	'id': str,
})


SiteUpdateInput = TypedDict('SiteUpdateInput', {
	'id': str,
	'name': str,
	'description': Optional[str],
	'url': Optional[str],
	'regex': Optional[str],
	'valid_types': List['ValidSiteTypeEnum'],
})


StringCriterionInput = TypedDict('StringCriterionInput', {
	'value': str,
	'modifier': 'CriterionModifier',
})


StudioCreateInput = TypedDict('StudioCreateInput', {
	'name': str,
	'urls': Optional[List['URLInput']],
	'parent_id': Optional[str],
	'image_ids': Optional[List[str]],
})


StudioDestroyInput = TypedDict('StudioDestroyInput', {
	'id': str,
})


StudioEditDetailsInput = TypedDict('StudioEditDetailsInput', {
	'name': Optional[str],
	'urls': Optional[List['URLInput']],
	'parent_id': Optional[str],
	'image_ids': Optional[List[str]],
})


StudioEditInput = TypedDict('StudioEditInput', {
	'edit': 'EditInput',
	'details': Optional['StudioEditDetailsInput'],
})


StudioQueryInput = TypedDict('StudioQueryInput', {
	'name': Optional[str],
	'names': Optional[str],
	'url': Optional[str],
	'parent': Optional['IDCriterionInput'],
	'has_parent': Optional[bool],
	'is_favorite': Optional[bool],
	'page': int,
	'per_page': int,
	'direction': 'SortDirectionEnum',
	'sort': 'StudioSortEnum',
})


StudioUpdateInput = TypedDict('StudioUpdateInput', {
	'id': str,
	'name': Optional[str],
	'urls': Optional[List['URLInput']],
	'parent_id': Optional[str],
	'image_ids': Optional[List[str]],
})


TagCategoryCreateInput = TypedDict('TagCategoryCreateInput', {
	'name': str,
	'group': 'TagGroupEnum',
	'description': Optional[str],
})


TagCategoryDestroyInput = TypedDict('TagCategoryDestroyInput', {
	'id': str,
})


TagCategoryUpdateInput = TypedDict('TagCategoryUpdateInput', {
	'id': str,
	'name': Optional[str],
	'group': Optional['TagGroupEnum'],
	'description': Optional[str],
})


TagCreateInput = TypedDict('TagCreateInput', {
	'name': str,
	'description': Optional[str],
	'aliases': Optional[List[str]],
	'category_id': Optional[str],
})


TagDestroyInput = TypedDict('TagDestroyInput', {
	'id': str,
})


TagEditDetailsInput = TypedDict('TagEditDetailsInput', {
	'name': Optional[str],
	'description': Optional[str],
	'aliases': Optional[List[str]],
	'category_id': Optional[str],
})


TagEditInput = TypedDict('TagEditInput', {
	'edit': 'EditInput',
	'details': Optional['TagEditDetailsInput'],
})


TagQueryInput = TypedDict('TagQueryInput', {
	'text': Optional[str],
	'names': Optional[str],
	'name': Optional[str],
	'category_id': Optional[str],
	'page': int,
	'per_page': int,
	'direction': 'SortDirectionEnum',
	'sort': 'TagSortEnum',
})


TagUpdateInput = TypedDict('TagUpdateInput', {
	'id': str,
	'name': Optional[str],
	'description': Optional[str],
	'aliases': Optional[List[str]],
	'category_id': Optional[str],
})


URLInput = TypedDict('URLInput', {
	'url': str,
	'site_id': str,
})


UserChangePasswordInput = TypedDict('UserChangePasswordInput', {
	'existing_password': Optional[str],
	'new_password': str,
	'reset_key': Optional[str],
})


UserCreateInput = TypedDict('UserCreateInput', {
	'name': str,
	'password': str,
	'roles': List['RoleEnum'],
	'email': str,
	'invited_by_id': Optional[str],
})


UserDestroyInput = TypedDict('UserDestroyInput', {
	'id': str,
})


UserQueryInput = TypedDict('UserQueryInput', {
	'name': Optional[str],
	'email': Optional[str],
	'roles': Optional['RoleCriterionInput'],
	'apiKey': Optional[str],
	'successful_edits': Optional['IntCriterionInput'],
	'unsuccessful_edits': Optional['IntCriterionInput'],
	'successful_votes': Optional['IntCriterionInput'],
	'unsuccessful_votes': Optional['IntCriterionInput'],
	'api_calls': Optional['IntCriterionInput'],
	'invited_by': Optional[str],
	'page': int,
	'per_page': int,
})


UserUpdateInput = TypedDict('UserUpdateInput', {
	'id': str,
	'name': Optional[str],
	'password': Optional[str],
	'roles': Optional[List['RoleEnum']],
	'email': Optional[str],
})


