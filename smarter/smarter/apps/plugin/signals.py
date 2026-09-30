"""Signals for plugin app."""

from django.dispatch import Signal

plugin_created = Signal()
"""
Signal sent when a plugin is created.

Arguments:
    plugin: The plugin instance that was created.

Example::

    plugin_created.send(sender=self.__class__, plugin=self)
"""

plugin_cloned = Signal()
"""
Signal sent when a plugin is cloned.

Arguments:
    plugin: The plugin instance that was cloned.

Example::

    plugin_cloned.send(sender=self.__class__, plugin=self)
"""

plugin_updated = Signal()
"""
Signal sent when a plugin is updated.

Example::

    plugin_updated.send(sender=self.__class__, plugin=self)
"""

plugin_deleted = Signal()
"""
Signal sent when a plugin is deleted.

Arguments:
    plugin: The plugin instance that was deleted.
    plugin_meta: The plugin meta information.
    plugin_name: The name of the plugin.

Example::

    plugin_deleted.send(
        sender=self.__class__, plugin=self, plugin_meta=self.plugin_meta, plugin_name=plugin_name
    )
"""
plugin_deleting = Signal()
"""
Signal sent before a plugin is deleted.

Arguments:
    plugin: The plugin instance that is about to be deleted.
    plugin_meta: The plugin meta information.

Example::

    plugin_deleting.send(sender=self.__class__, plugin=self, plugin_meta=self.plugin_meta)
"""

plugin_called = Signal()
"""
Signal sent when a plugin is called.

Arguments:
    plugin: The plugin instance that was called.
    inquiry_type: The type of inquiry made to the plugin.

Example::

        plugin_called.send(
            sender=self.tool_call_fetch_plugin_response,
            plugin=self,
            inquiry_type=inquiry_type,
        )
"""

plugin_responded = Signal()
"""
Signal sent when a plugin responds.

Arguments:
    plugin: The plugin instance that responded.
    inquiry_type: The type of inquiry made to the plugin.
    response: The response returned by the plugin.

Example::

    plugin_responded.send(
        sender=self.tool_call_fetch_plugin_response,
        plugin=self,
        inquiry_type=inquiry_type,
        response=retval,
    )
"""

plugin_ready = Signal()
"""
Signal sent when a plugin achieves a ready state.

Arguments:
    plugin: The plugin instance that is ready.

Example::

    plugin_ready.send(sender=self.__class__, plugin=self)
"""

plugin_selected = Signal()
"""
Signal sent when a plugin is selected for use.

That is, when the Plugin
selection logic results in this Plugin being included in the set of Plugins
to be presented to the LLM for a given text completion request.

Arguments:
    plugin: The plugin instance that was selected.
    user: The user who selected the plugin (optional).
    input_text: The input text provided to the plugin (optional).
    search_term: The search term associated with the plugin selection (optional).

Example::

    plugin_selected.send(
        sender=self.selected,
        plugin=self,
        user=self.user_profile.cached_user if self.user_profile else None,
        input_text=input_text,
        search_term=search_term,
    )
"""

broker_ready = Signal()
"""
Signal sent when a broker achieves a ready state.

Arguments:
    broker: The broker instance that is ready.

Example::

    broker_ready.send(sender=self.__class__, broker=self)
"""

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
