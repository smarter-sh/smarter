"""
Enumeration classes for the WebsearchPlugin manifest models.

.. note::

    **Experimental.** The WebsearchPlugin was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from smarter.common.enum import SmarterEnumAbstract


class WebsearchProvider(SmarterEnumAbstract):
    """The web search APIs that a WebsearchPlugin can use."""

    BRAVE = "brave"
    """Brave Search API.

    https://brave.com/search/api/
    """

    TAVILY = "tavily"
    """Tavily Search API, which is designed for LLMs.

    https://tavily.com
    """


class WebsearchSafeSearch(SmarterEnumAbstract):
    """Filtering of adult content from search results."""

    OFF = "off"
    MODERATE = "moderate"
    STRICT = "strict"


class WebsearchFreshness(SmarterEnumAbstract):
    """Restricts search results to those published within a period."""

    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


class WebsearchOperation(SmarterEnumAbstract):
    """The operations that a WebsearchPlugin's tool performs."""

    SEARCH = "search"
    FETCH = "fetch"
