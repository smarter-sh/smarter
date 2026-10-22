"""Signals of the lifecycle of every plugin: create, clone, update, delete, select and call."""

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

search_term_matched = Signal()
"""
Signal sent when :func:`smarter.apps.llmtool.nlp.does_refer_to` finds that a prompt refers to a search term.

Plugin selectors use it to decide whether to select a plugin, so this reports why each
plugin was selected, and how often each kind of matching (exact, typo tolerant, thesaurus)
succeeds.

Arguments:
    prompt: The prompt, as given to does_refer_to().
    search_term: The search term that the prompt refers to.
    method: How it matched, a :class:`smarter.apps.llmtool.nlp.MatchMethod`: exact, fuzzy or thesaurus.
    matched_text: For thesaurus matches, the words of the prompt that matched, e.g. a synonym. Otherwise None.

Example::

    search_term_matched.send(
        sender=does_refer_to,
        prompt="I want to buy an automobile",
        search_term="car",
        method="thesaurus",
        matched_text="automobile",
    )
"""

broker_ready = Signal()
"""
Signal sent when a broker achieves a ready state.

Arguments:
    broker: The broker instance that is ready.

Example::

    # a broker sends it once, from its ready property
    self.send_broker_ready(broker_ready)
"""
