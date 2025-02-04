"""
url helper functions
"""

from urllib.parse import parse_qs, urlparse

from smarter.common.const import SMARTER_CHAT_SESSION_KEY_NAME
from smarter.lib.django.validators import SmarterValidator


def clean_url(url: str) -> str:
    """
    Clean the url of any query strings.
    """
    parsed_url = urlparse(url)
    retval = parsed_url._replace(query="").geturl()
    return retval


def session_key_from_url(url: str) -> str:
    """
    Extract the session key from a URL.

    Args:
        url: The URL to extract the session key from.

    Returns:
        The session key.
    """
    if not url:
        return None
    SmarterValidator.validate_url(url)
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    session_key = query_params.get(SMARTER_CHAT_SESSION_KEY_NAME, [None])[0]

    return session_key
