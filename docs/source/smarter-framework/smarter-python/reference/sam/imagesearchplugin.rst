..
   Generated from the smarter-python SDK's docstrings by its scripts/generate_reference.py.
   Do not edit: change the docstring in https://github.com/smarter-sh/smarter-python, and regenerate.

SAMImageSearchPlugin
====================

``smarter.models.sam.imagesearchplugin``
----------------------------------------

.. py:module:: smarter.models.sam.imagesearchplugin

SAM model of the ``ImageSearchPlugin`` kind, generated from the Smarter platform's JSON Schema.

Do not edit: run ``scripts/generate_sam_models.py``. See :mod:`smarter.models.sam`.

.. py:class:: ImageSearchFilters

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API - ImageSearchPlugin.spec.imageSearchData.filters.

   Smarter applies these to the Brave Image Search API's results.

   .. py:attribute:: allowedDomains
      :type: list[str] | None

      ImageSearchPlugin.spec.filters.allowedDomains[list]: if not empty, only images from web pages on these domains, and their subdomains.


   .. py:attribute:: blockedDomains
      :type: list[str] | None

      ImageSearchPlugin.spec.filters.blockedDomains[list]: never images on these domains, nor from web pages on them, including their subdomains.


   .. py:attribute:: fileType
      :type: str | None

      ImageSearchPlugin.spec.filters.fileType[str]: only images of these file types, separated by '\|', e.g. jpg\|png.

      Any of: ['jpg', 'png', 'gif', 'svg', 'webp', 'avif', 'bmp', 'ico']


   .. py:attribute:: minHeight
      :type: Optional

      ImageSearchPlugin.spec.filters.minHeight[int]: only images at least this many pixels high.

      Images whose height Brave does not report are skipped.


   .. py:attribute:: minWidth
      :type: Optional

      ImageSearchPlugin.spec.filters.minWidth[int]: only images at least this many pixels wide. Images whose width Brave does not report are skipped.



.. py:class:: Safesearch

   Bases: :class:`enum.Enum`

   ImageSearchPlugin.spec.searchParams.safesearch[str]: adult content filtering.

   One of: ['off', 'strict']


.. py:class:: ImageSearchParams

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API - ImageSearchPlugin.spec.imageSearchData.searchParams.

   These map 1:1 to the query parameters of the Brave Image Search API, except for ``q``, the
   query itself, which the LLM supplies. See ``imageSearchData.queryTerms``.

   .. py:attribute:: count
      :type: Optional

      ImageSearchPlugin.spec.searchParams.count[int]: the maximum number of images per search, 1 to 20.


   .. py:attribute:: country
      :type: str | None

      ImageSearchPlugin.spec.searchParams.country[str]: a two letter country code, e.g. us, or all for worldwide results.


   .. py:attribute:: safesearch
      :type: smarter.models.sam.imagesearchplugin.Safesearch | None

      ImageSearchPlugin.spec.searchParams.safesearch[str]: adult content filtering.

      One of: ['off', 'strict']


   .. py:attribute:: searchLang
      :type: str | None

      ImageSearchPlugin.spec.searchParams.searchLang[str]: prefer images from content in this language, e.g. en or pt-br.


   .. py:attribute:: spellcheck
      :type: bool | None

      ImageSearchPlugin.spec.searchParams.spellcheck[bool]: whether Brave may correct the spelling of the query.



.. py:class:: SAMDependency

   Bases: :class:`smarter.models.sam.base.SAMModel`

   A resource that depends on the resource that a manifest describes.

   .. py:attribute:: kind
      :type: str

      Kind[String]: The SAM kind of the resource that depends on this resource, e.g. LLMClient.

      Read only.


   .. py:attribute:: name
      :type: str

      Name[String]: The name of the resource that depends on this resource.

      Read only.



.. py:class:: SAMPluginCommonMetadata

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Plugin Manifest - common Metadata class.

   .. py:attribute:: annotations
      :type: None | list[dict[str, Union[str, int, float, bool, datetime.date, datetime.datetime, Annotated[str, StringConstraints(strip_whitespace=None, to_upper=None, to_lower=None, strict=None, min_length=None, max_length=None, pattern='^(?!^[-+.]*$)[+-]?0*\\d*\\.?\\d*$', ascii_only=None)], uuid.UUID, bytes, list, dict[str, Any]]]]

      The manifest annotations.

      Used for storing arbitrary metadata as
                  key-value pairs. Example: [{'smarter.sh/test-manifest/project-name': 'Scooby dooby do'}]. The
                  key should be a valid url-friendly string. The value accepts
                  multi-line string values (YAML block scalars) and various scalar types including
                  str, int, float, bool, datetime.date, datetime.datetime, decimal.Decimal, uuid.UUID, bytes, list, dict.


   .. py:attribute:: description
      :type: str | None

      The description for this resource.

      Be brief. Keep it under 255 characters.


   .. py:attribute:: name
      :type: str

      The camelCase name of the manifest resource.


   .. py:attribute:: pluginClass
      :type: str

      The class of the plugin.

      one of: ['api', 'imagesearch', 'skill', 'sql', 'static', 'websearch']


   .. py:attribute:: tags
      :type: list[str] | None

      The tags of the manifest.

      Used for generic resource categorization and search. Example: ['tag1', 'tag2']


   .. py:attribute:: version
      :type: str | None

      The semantic version of the manifest.

      Example: 0.1.0



.. py:class:: SAMPluginCommonSpecPrompt

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Plugin Manifest - Spec - Prompt class.

   .. py:attribute:: maxTokens
      :type: Optional

      Plugin.spec.prompt.maxTokens[int].

      Optional. The maxTokens of the Plugin. Defaults to 2048. The maximum number of tokens the LLM should generate in the prompt response.


   .. py:attribute:: model
      :type: str | None

      Plugin.spec.prompt.model[str] Optional.

      The model of the Plugin. Defaults to gpt-6-luna. Must be one of: ['chat-latest', 'gpt-4.1', 'gpt-4.1-2025-04-14', 'gpt-4.1-mini', 'gpt-4.1-mini-2025-04-14', 'gpt-4o', 'gpt-4o-2024-08-06', 'gpt-4o-2024-11-20', 'gpt-4o-mini', 'gpt-4o-mini-2024-07-18', 'gpt-5-search-api', 'gpt-5-search-api-2025-10-14', 'gpt-5.2', 'gpt-5.2-2025-12-11', 'gpt-5.4', 'gpt-5.4-2026-03-05', 'gpt-5.4-mini', 'gpt-5.4-mini-2026-03-17', 'gpt-5.5', 'gpt-5.5-2026-04-23', 'gpt-5.6-luna', 'gpt-5.6-sol', 'gpt-5.6-terra', 'gpt-6-astra', 'gpt-6-luna', 'gpt-6-sol', 'gpt-6.1-sol']


   .. py:attribute:: provider
      :type: str | None

      Plugin.spec.prompt.provider[str].

      Optional. The provider of the LLM. Defaults to openai. The provider is the vendor name for the LLM service that will be used to generate the prompt response.


   .. py:attribute:: systemRole
      :type: str

      Plugin.spec.prompt.systemRole[str].

      Required. The system role that the Plugin will use for the LLM text completion prompt. Be verbose and specific. Ensure that systemRole accurately conveys to the LLM how you want it to use the Plugin data that is returned.


   .. py:attribute:: temperature
      :type: Optional

      Plugin.spec.prompt.temperature[float] Optional.

      The temperature of the Plugin. Defaults to 1.0. Should be between 0 and 1.0. The higher the temperature, the more creative the response. The lower the temperature, the more predictable the response.



.. py:class:: SAMPluginCommonSpecSelector

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Plugin Manifest - Spec - Selector class.

   .. py:attribute:: directive
      :type: str

      Plugin.spec.selector.directive[str]: Required.

      the kind of selector directive to use for the Plugin. Must be one of: ['search_terms', 'always', 'llm']


   .. py:attribute:: searchTerms
      :type: list[str] | None

      Plugin.spec.selector.searchTerms[list].

      Optional. The keyword search terms to use when the Plugin directive is 'search_terms'. Keywords are most effective when constrained to 1 or 2 words each and lists are limited to a few dozen items.



.. py:class:: SAMPluginCommonStatus

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Plugin Manifest - Status class.

   .. py:attribute:: accountNumber
      :type: str

      Plugin.status.account_number: The account owner of this Plugin.

      Read only.


   .. py:attribute:: created
      :type: datetime

      The date in which this resource was created.

      Read only.


   .. py:attribute:: dependencies
      :type: list[smarter.models.sam.imagesearchplugin.SAMDependency] | None

      Dependencies[List]: The resources that depend on this resource, and that must be deleted, or stop referring to it, before it can be deleted.

      Lists only the resources that you can read. Read only.


   .. py:attribute:: modified
      :type: datetime

      The date in which this resource was most recently changed.

      Read only.


   .. py:attribute:: recordLocator
      :type: str

      RecordLocator[String]: An optional identifier used to locate the resource record associated with this manifest.

      Read only.


   .. py:attribute:: username
      :type: str

      Plugin.status.account_number: The Smarter user who created this Plugin.

      Read only.



.. py:class:: ImageSearchData

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API - ImageSearchPlugin.spec.imageSearchData.

   .. py:attribute:: apiKey
      :type: str | None

      ImageSearchPlugin.spec.apiKey[str]: the name of the Smarter Secret that contains a Brave Search API key.

      The api key itself is never included in the manifest.


   .. py:attribute:: cacheTtl
      :type: Optional

      ImageSearchPlugin.spec.cacheTtl[int]: seconds to cache search results.

      0 disables caching.


   .. py:attribute:: filters
      :type: smarter.models.sam.imagesearchplugin.ImageSearchFilters | None

      ImageSearchPlugin.spec.filters[obj]: the filters that Smarter applies to the search results.


   .. py:attribute:: llmSearchParams
      :type: bool | None

      ImageSearchPlugin.spec.llmSearchParams[bool]: whether the LLM may set every Brave Image Search API parameter in each tool call: count (up to 20), country, search_lang, safesearch and spellcheck.

      searchParams are then the defaults. If false, the LLM may only lower the count.


   .. py:attribute:: queryTerms
      :type: Optional

      ImageSearchPlugin.spec.queryTerms[str]: optional search terms appended to every query that the LLM sends, e.g. 'black and white photograph'.

      The LLM always supplies the query itself, e.g. 'formula 1 race cars', so that Brave searches for 'formula 1 race cars black and white photograph'.


   .. py:attribute:: searchParams
      :type: smarter.models.sam.imagesearchplugin.ImageSearchParams | None

      ImageSearchPlugin.spec.searchParams[obj]: the Brave Image Search API query parameters.


   .. py:attribute:: timeout
      :type: Optional

      ImageSearchPlugin.spec.timeout[int]: seconds to wait for each web request, 1 to 60.


   .. py:attribute:: validateUrls
      :type: bool | None

      ImageSearchPlugin.spec.validateUrls[bool]: only return image urls that respond to a request with HTTP 200, and not with a web page.

      Urls are always https.



.. py:class:: SAMImageSearchPluginSpec

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Manifest - ImageSearchPlugin.spec.

   .. py:attribute:: imageSearchData
      :type: smarter.models.sam.imagesearchplugin.ImageSearchData | None

      ImageSearchPlugin.spec.imageSearchData[obj]: the image search configuration of the ImageSearchPlugin.


   .. py:attribute:: prompt
      :type: SAMPluginCommonSpecPrompt

      Plugin.spec.prompt[obj]: the LLM prompt engineering to apply to the Plugin.


   .. py:attribute:: selector
      :type: SAMPluginCommonSpecSelector

      Plugin.spec.selector[obj]: the selector logic to use for the Plugin.



.. py:class:: SAMImageSearchPlugin

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Manifest - ImageSearchPlugin Model.

   .. py:attribute:: apiVersion
      :type: str

      ApiVersion[String]: Required.

      The API version of the AbstractSAMBase.


   .. py:attribute:: kind
      :type: str

      Kind[String]: Required.

      The kind of resource described by the manifest.


   .. py:attribute:: metadata
      :type: SAMPluginCommonMetadata

      Plugin.metadata[obj]: Required, the Plugin metadata.


   .. py:attribute:: spec
      :type: SAMImageSearchPluginSpec

      ImageSearchPlugin.spec[obj]: Required, the ImageSearchPlugin specification.


   .. py:attribute:: status
      :type: smarter.models.sam.imagesearchplugin.SAMPluginCommonStatus | None

      Plugin.status[obj]: Optional, Read-only.

      Stateful status information about the Plugin.
