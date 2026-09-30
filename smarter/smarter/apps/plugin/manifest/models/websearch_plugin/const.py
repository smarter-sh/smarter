"""
Smarter API WebsearchPlugin Manifest Constants.

.. note::

    **Experimental.** The WebsearchPlugin was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from smarter.lib.journal.enum import SmarterJournalThings

MANIFEST_KIND = SmarterJournalThings.WEBSEARCH_PLUGIN.value

MAX_QUERY_LENGTH = 400
"""The maximum length of a search query, in characters."""
MAX_URL_LENGTH = 2048
"""The maximum length of a URL to fetch, in characters."""
MAX_RESULTS = 20
"""The maximum number of search results that a plugin can return."""
DEFAULT_MAX_RESULTS = 5
MIN_FETCH_CHARACTERS = 1000
MAX_FETCH_CHARACTERS = 100_000
"""The maximum number of characters of a web page that a plugin can return."""
DEFAULT_FETCH_CHARACTERS = 20_000
MAX_TIMEOUT = 60
DEFAULT_TIMEOUT = 15
MAX_CACHE_TTL = 86_400
DEFAULT_CACHE_TTL = 900
"""Seconds to cache search results and web pages.

15 minutes, as with Claude's own web fetch tool.
"""
MAX_DOMAINS = 100
"""The maximum number of domains in an allow list or a block list."""
