from enum import Enum
from typing import TypedDict
from urllib.parse import urlparse, urlunparse 

StashSource = Enum('StashSource', 'STASHDB PMVSTASH FANSDB')

PerformerUploadConfig = TypedDict('PerformerUploadConfig', {
	'name': str,
	'id': str,
    'comment':str
})

def normalize_url(url):
    # Parse the URL into components
    parsed_url = urlparse(url)
    
    # Normalize the scheme to treat http and https as equivalent
    normalized_scheme = 'https' if parsed_url.scheme in ('http', 'https') else parsed_url.scheme
    
    # Rebuild the normalized URL without changing query or fragment
    normalized_url = urlunparse((
        normalized_scheme,
        parsed_url.hostname,
        parsed_url.path.rstrip('/'),  # Remove any trailing slashes from the path
        parsed_url.params,
        parsed_url.query,
        ""
    ))
    
    return normalized_url