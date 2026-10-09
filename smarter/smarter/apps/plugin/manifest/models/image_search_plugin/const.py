"""
Smarter API ImageSearchPlugin Manifest Constants.

.. note::

    **Experimental.** The ImageSearchPlugin was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental.
"""

from smarter.lib.journal.enum import SmarterJournalThings

MANIFEST_KIND = SmarterJournalThings.IMAGE_SEARCH_PLUGIN.value

DEFAULT_API_KEY_SECRET_NAME = "brave_search_api_key"
"""The default name of the Smarter Secret that contains the Brave Search API key.

The WebsearchPlugin's Brave samples use the same Secret.
"""

BRAVE_IMAGE_SEARCH_URL = "https://api.search.brave.com/res/v1/images/search"
"""The Brave Image Search API endpoint.

https://api-dashboard.search.brave.com/app/documentation/image-search/get-started
"""

MAX_QUERY_LENGTH = 400
"""The maximum length of a search query, in characters, which is also the Brave Search API's limit."""
MAX_COUNT = 20
"""The maximum number of images per search.

The Brave Image Search API returns up to 200, but each url is validated with a request of its own.
"""
DEFAULT_COUNT = 10
MAX_DIMENSION = 10_000
"""The maximum value of minWidth and minHeight, in pixels."""
MAX_TIMEOUT = 60
DEFAULT_TIMEOUT = 10
MAX_CACHE_TTL = 86_400
DEFAULT_CACHE_TTL = 900
"""Seconds to cache search results.

15 minutes.
"""

CREDENTIALS_HELP = (
    "An ImageSearchPlugin requires a Brave Search API key, stored in a Smarter Secret. "
    "1) Sign up at https://api-dashboard.search.brave.com, subscribe to a plan that includes image search, "
    "and create an api key at https://api-dashboard.search.brave.com/app/keys. "
    "2) Set SMARTER_BRAVE_SEARCH_API_KEY in .env, and run 'python manage.py initialize_providers', or apply a "
    f"Secret manifest named {DEFAULT_API_KEY_SECRET_NAME}. "
    "See https://api-dashboard.search.brave.com/app/documentation/image-search/get-started"
)
"""Instructions for creating the Brave Search API key, logged when it is missing."""
