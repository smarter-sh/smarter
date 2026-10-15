..
   Generated from the smarter-python SDK's docstrings by its scripts/generate_reference.py.
   Do not edit: change the docstring in https://github.com/smarter-sh/smarter-python, and regenerate.

SAMSqlPlugin
============

``smarter.models.sam.sqlplugin``
--------------------------------

.. py:module:: smarter.models.sam.sqlplugin

SAM model of the ``SqlPlugin`` kind, generated from the Smarter platform's JSON Schema.

Do not edit: run ``scripts/generate_sam_models.py``. See :mod:`smarter.models.sam`.

.. py:class:: ParameterType

   Bases: :class:`enum.Enum`

   Enum for parameter types.


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
      :type: list[smarter.models.sam.sqlplugin.SAMDependency] | None

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



.. py:class:: TestValue

   Bases: :class:`smarter.models.sam.base.SAMModel`

   TestValue class for SqlPlugin and ApiPlugin test values.

   .. py:attribute:: name
      :type: str

      The name of the parameter being tested.


   .. py:attribute:: value
      :type: Any

      The test value for the parameter.



.. py:class:: Parameter

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Parameter class for parameterized Plugins.

   This structure is
   intended to match that which is used in the OpenAPI
   function calling specification.
   It is used to define the parameters that a plugin can accept,
   and also for creating the function calling prompt api.

   .. py:attribute:: default
      :type: Any | None

      The default value of the parameter, if any.


   .. py:attribute:: description
      :type: str | None

      A description of the parameter.


   .. py:attribute:: enum
      :type: list[str] | None

      A list of allowed values for the parameter.

      Example: ['Celsius', 'Fahrenheit']


   .. py:attribute:: name
      :type: str

      The name of the parameter.


   .. py:attribute:: required
      :type: bool | None

      Whether the parameter is required.


   .. py:attribute:: type
      :type: ParameterType

      The data type of the parameter (one of: string, number, integer, boolean, object, array, null).



.. py:class:: SqlData

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API - generic API Connection class.

   .. py:attribute:: limit
      :type: Optional

      The maximum number of rows to return from the query.

      Must be a non-negative integer.


   .. py:attribute:: parameters
      :type: list[smarter.models.sam.sqlplugin.Parameter] | None

      A JSON dict containing parameter names and data types.

      Example: {'unit': {'type': 'string', 'enum': ['Celsius', 'Fahrenheit'], 'description': 'The temperature unit to use.'}}


   .. py:attribute:: sqlQuery
      :type: str

      The SQL query that this plugin will execute when invoked by the user prompt.


   .. py:attribute:: testValues
      :type: list[smarter.models.sam.sqlplugin.TestValue] | None

      A JSON dict containing test values for each parameter.

      Example: {'product_id': 1234}.



.. py:class:: SAMSqlPluginSpec

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API SqlData Connection Manifest SqlConnection.spec.

   .. py:attribute:: connection
      :type: str

      SqlPlugin.spec.selector[obj]: the name of an existing SqlConnector to use for the SqlPlugin.


   .. py:attribute:: prompt
      :type: SAMPluginCommonSpecPrompt

      Plugin.spec.prompt[obj]: the LLM prompt engineering to apply to the Plugin.


   .. py:attribute:: selector
      :type: SAMPluginCommonSpecSelector

      Plugin.spec.selector[obj]: the selector logic to use for the Plugin.


   .. py:attribute:: sqlData
      :type: SqlData

      SqlPlugin.spec.selector[obj]: the SqlData to use for the SqlPlugin.



.. py:class:: SAMSqlPlugin

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Manifest - Sql Connection Model.

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
      :type: SAMSqlPluginSpec

      SqlPlugin.spec[obj]: Required, the SqlPlugin specification.


   .. py:attribute:: status
      :type: smarter.models.sam.sqlplugin.SAMPluginCommonStatus | None

      Plugin.status[obj]: Optional, Read-only.

      Stateful status information about the Plugin.
