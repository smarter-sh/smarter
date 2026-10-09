Image Search Plugin
===================

An ImageSearchPlugin gives the LLM an image search. Its tool takes a search query, and returns
a JSON list of strings: the https urls of the images that it found, for example
``["https://upload.wikimedia.org/.../bald-eagle.jpg"]``. It is powered by the
`Brave Image Search API <https://api-dashboard.search.brave.com/app/documentation/image-search/get-started>`__.

The LLM supplies the search query in each tool call. The manifest's
``spec.imageSearchData.queryTerms``, if set, are appended to it: with ``queryTerms: black and
white photograph``, a query for ``formula 1 race cars`` searches for ``formula 1 race cars black
and white photograph``. ``spec.imageSearchData.searchParams`` map 1:1 to the API's other query
parameters: ``count``, ``country``, ``searchLang``, ``safesearch`` (``strict``, Brave's
default, or ``off``) and ``spellcheck``. Brave cannot filter images by
file type, size or license, so ``spec.imageSearchData.filters`` are applied by Smarter to
Brave's results:

- ``fileType``: only these file types, e.g. ``jpg|png``, judged by each url's file extension,
  or else by the Content-Type of its response.
- ``minWidth`` and ``minHeight``: only images at least this large. Brave reports the size of
  most images; those of unknown size are skipped. Use them to skip thumbnails.
- ``allowedDomains`` and ``blockedDomains``: only, or never, images from web pages on these
  domains. Blocked domains also apply to the image itself, since a website's localized pages,
  e.g. on ``gettyimages.fr``, often serve images from its main domain. The allowed domains are also sent to Brave as ``site:`` operators, so that Brave
  searches them. The blocked domains are not, since Brave returns no results for some queries
  with several ``-site:`` operators. Brave's results are most relevant with one or two
  allowed domains.

Use them to tailor a plugin to one purpose, such as kid-friendly images from Wikimedia Commons,
black and white photographs, technical diagrams or SVG images. The sample manifests in
``smarter/apps/plugin/data/sample-plugins/image-search-*.yaml`` do just that.

Alternatively, let the LLM decide. With ``llmSearchParams: true``, the LLM may set every
search parameter in each tool call: ``count`` (up to 20), ``country``, ``search_lang``,
``safesearch`` and ``spellcheck``, and ``searchParams`` are only the defaults. Invalid values
are ignored, in favor of the defaults. The sample ``image_search``
(``smarter/apps/plugin/data/sample-plugins/image-search.yaml``) does this, and its selector is
``always``, so that its tool is offered with every prompt. It is the image search plugin of the
example LLMClients.

Offering a tool does not make the LLM call it. Unless told otherwise, most models answer from
what they already know and skip an optional image search. So the ``systemRole`` and the
``description`` (which becomes the tool's description) of ``image_search`` are directive: they
tell the LLM to search before answering any question about something that can be seen or drawn,
even when the user did not ask for an image, and to skip the search for arithmetic, code and
short conversational replies. Also check that the LLMClient's own ``defaultSystemRole`` does not
contradict this, for example by allowing only image urls that the user provided. Neither needs to
explain Markdown image syntax, or forbid invented image urls: Smarter appends the chat window's
rendering rules, which say both, to the system prompt of every request.

Only https urls of the original images are returned, never Brave's thumbnails and, unless
``validateUrls`` is false, only those that respond to a request with HTTP 200, and not with a
web page, such as that of a website that blocks hotlinking.

Brave Search API key
--------------------

The plugin needs a Brave Search API key, in the Smarter Secret that the manifest names in
``apiKey``, which defaults to ``brave_search_api_key``. The Brave samples of the
:doc:`Websearch Plugin <websearch>` use the same Secret.

1. Sign up at the `Brave Search API dashboard <https://api-dashboard.search.brave.com>`__,
   subscribe to a plan that includes image search, and create an
   `api key <https://api-dashboard.search.brave.com/app/keys>`__.
2. Set ``SMARTER_BRAVE_SEARCH_API_KEY`` in ``.env``, and run ``manage.py initialize_providers``,
   which ``initialize_platform`` also runs, to store it as the Secret. Alternatively, apply a
   Secret manifest named ``brave_search_api_key``.

If the Secret is missing, the plugin returns an empty list, and logs a warning that explains how
to create it. If Brave rejects the key, or its plan's quota is exceeded, the plugin also returns
an empty list, and logs why.

.. note::

    **Experimental.** The ImageSearchPlugin was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental.

Technical References
--------------------

- Class Reference: :py:class:`smarter.apps.plugin.plugin.image_search.ImageSearchPlugin`
- Django ORM Model: :py:class:`smarter.apps.plugin.models.PluginDataImageSearch`
- Safe HTTP requests: :py:mod:`smarter.apps.plugin.plugin.safe_http`
- :doc:`SAM Broker <../sam/brokers/image-search-plugin>`
- :doc:`SAM Pydantic Class Reference <../sam/models/image-search-plugin>`

.. automodule:: smarter.apps.plugin.plugin.image_search
    :members:
    :undoc-members:
    :show-inheritance:
