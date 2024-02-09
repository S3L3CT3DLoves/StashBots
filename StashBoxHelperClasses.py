from enum import Enum
from typing import TypedDict


StashSource = Enum('StashSource', 'STASHDB PMVSTASH FANSDB')

PerformerUploadConfig = TypedDict('PerformerUploadConfig', {
	'name': str,
	'id': str,
    'comment':str
})