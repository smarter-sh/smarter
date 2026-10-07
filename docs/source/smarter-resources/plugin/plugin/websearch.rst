Websearch Plugin
======================

.. note::

    **Experimental.** The WebsearchPlugin was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.

Technical References
--------------------

- Class Reference: :py:class:`smarter.apps.plugin.plugin.websearch.WebsearchPlugin`
- Django ORM Model: :py:class:`smarter.apps.plugin.models.PluginDataWebsearch`
- Web search APIs: :py:mod:`smarter.apps.plugin.plugin.websearch_providers`
- Reading web pages: :py:mod:`smarter.apps.plugin.plugin.websearch_fetch`
- Safe HTTP requests: :py:mod:`smarter.apps.plugin.plugin.safe_http`
- :doc:`Tavily web search <../../../smarter-framework/technologies/tavily>`: what Tavily is, and how to set up its API key
- :doc:`SAM Broker <../sam/brokers/websearch-plugin>`
- :doc:`SAM Pydantic Class Reference <../sam/models/websearch-plugin>`

.. automodule:: smarter.apps.plugin.plugin.websearch
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: smarter.apps.plugin.plugin.websearch_providers
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: smarter.apps.plugin.plugin.websearch_fetch
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: smarter.apps.plugin.plugin.safe_http
    :members:
    :undoc-members:
    :show-inheritance:
