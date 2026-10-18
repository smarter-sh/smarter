"""Signals of WebsearchPlugin searches and page reads."""

from django.dispatch import Signal

websearch_searched = Signal()
"""
Signal sent when a WebsearchPlugin searches the web.

Experimental.

Arguments:
    plugin: The WebsearchPlugin instance.
    query: The search query.
    provider: The web search API, e.g. ``brave``.
    result_count: The number of results returned to the LLM.
    cached: True if the results were served from the cache.

Example::

    websearch_searched.send(sender=self.__class__, plugin=self, query=query, provider="brave", result_count=5, cached=False)
"""

websearch_fetched = Signal()
"""
Signal sent when a WebsearchPlugin reads a web page.

Experimental.

Arguments:
    plugin: The WebsearchPlugin instance.
    url: The requested URL.
    final_url: The URL of the page that was read, after any redirects.
    characters: The number of characters of content returned to the LLM.
    truncated: True if the content was truncated.
    cached: True if the page was served from the cache.

Example::

    websearch_fetched.send(sender=self.__class__, plugin=self, url=url, final_url=final_url, characters=1234, truncated=False, cached=False)
"""

websearch_failed = Signal()
"""
Signal sent when a WebsearchPlugin cannot perform a search or read a web page.

Experimental.

Arguments:
    plugin: The WebsearchPlugin instance.
    operation: ``search`` or ``fetch``.
    target: The search query or URL.
    error: A description of the error, which is also returned to the LLM.

Example::

    websearch_failed.send(sender=self.__class__, plugin=self, operation="fetch", target=url, error="HTTP 404")
"""
