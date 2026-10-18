"""Signals of ImageSearchPlugin tool calls."""

from django.dispatch import Signal

image_search_plugin_request_started = Signal()
"""
Signal sent when a ImageSearchPlugin tool call begins: an image search.

Arguments:
    plugin: The ImageSearchPlugin instance.
    function_args: The tool call's arguments, as the LLM sent them.

Example::

    image_search_plugin_request_started.send(sender=self.__class__, plugin=self, function_args=function_args)
"""

image_search_plugin_authenticated = Signal()
"""
Signal sent when the Brave Image Search API accepts the plugin's api key, that is, responds with any status other than HTTP 401 or 403.

Not sent when the search results are served from the cache.

Arguments:
    plugin: The ImageSearchPlugin instance.
    provider: The image search API, ``brave``.

Example::

    image_search_plugin_authenticated.send(sender=self.__class__, plugin=self, provider="brave")
"""

image_search_plugin_authentication_failed = Signal()
"""
Signal sent when the plugin's Brave Search API key Secret is missing or unreadable, or the Brave Image Search API rejects the key, with HTTP 401 or 403.

Arguments:
    plugin: The ImageSearchPlugin instance.
    provider: The image search API, ``brave``.
    error: What went wrong. It never contains the api key.

Example::

    image_search_plugin_authentication_failed.send(sender=self.__class__, plugin=self, provider="brave", error="the Brave Search API rejected the api key")
"""

image_search_plugin_responded = Signal()
"""
Signal sent when a ImageSearchPlugin tool call returns its response to the LLM.

Arguments:
    plugin: The ImageSearchPlugin instance.
    response: The image urls returned to the LLM.
    cached: True if the search results were served from the cache. The filters and url validation run either way.
    query: The search query.

Example::

    image_search_plugin_responded.send(sender=self.__class__, plugin=self, response=["https://example.com/eagle.jpg"], cached=False, query="bald eagle")
"""

image_search_plugin_failed = Signal()
"""
Signal sent when a ImageSearchPlugin tool call fails, whether it raises or returns an empty response to the LLM.

Arguments:
    plugin: The ImageSearchPlugin instance.
    error: What went wrong. It never contains credentials.

Example::

    image_search_plugin_failed.send(sender=self.__class__, plugin=self, error="the Brave Search API could not be reached.")
"""

image_search_plugin_request_completed = Signal()
"""
Signal sent when a ImageSearchPlugin tool call ends, successfully or not.

It is always the last signal of the call.

Arguments:
    plugin: The ImageSearchPlugin instance.
    success: False if image_search_plugin_failed was sent.
    duration: The seconds that the tool call took.

Example::

    image_search_plugin_request_completed.send(sender=self.__class__, plugin=self, success=True, duration=0.42)
"""
