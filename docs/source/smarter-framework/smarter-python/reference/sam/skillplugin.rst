..
   Generated from the smarter-python SDK's docstrings by its scripts/generate_reference.py.
   Do not edit: change the docstring in https://github.com/smarter-sh/smarter-python, and regenerate.

SAMSkillPlugin
==============

``smarter.models.sam.skillplugin``
----------------------------------

.. py:module:: smarter.models.sam.skillplugin

SAM model of the ``SkillPlugin`` kind, generated from the Smarter platform's JSON Schema.

Do not edit: run ``scripts/generate_sam_models.py``. See :mod:`smarter.models.sam`.

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
      :type: None | list[dict[str, Union[str, int, float, bool, datetime.date, datetime.datetime, Annotated[str, StringConstraints(strip_whitespace=None, to_upper=None, to_lower=None, strict=None, min_length=None, max_length=None, pattern='^(?!^[-+.]*$)[+-]?0*\\d*\\.?\\d*$')], uuid.UUID, bytes, list, dict[str, Any]]]]

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
      :type: list[smarter.models.sam.skillplugin.SAMDependency] | None

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



.. py:class:: SkillSource

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API - SkillPlugin.spec.skillData.source: the remote location of a skill.

   .. py:attribute:: url
      :type: str

      SkillPlugin.spec.source.url[str]: the https URL of the skill.

      Either a GitHub URL of a skill directory (e.g. https://github.com/anthropics/skills/tree/main/skills/pdf) or of a SKILL.md file, or any https URL of a SKILL.md file. The skill and its bundled files are retrieved when the manifest is applied.



.. py:class:: SkillData

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API - SkillPlugin.spec.skillData: an Agent Skill.

   Exactly one of ``skill`` or ``source`` is required.

   .. py:attribute:: resources
      :type: dict[str, str | None] | None

      SkillPlugin.spec.resources[obj]: the skill's bundled files, e.g. references/, scripts/ and assets/, keyed by their path relative to the skill root, as SKILL.md refers to them.

      Only valid with 'skill'.


   .. py:attribute:: skill
      :type: str | None

      SkillPlugin.spec.skill[str]: the verbatim contents of a SKILL.md file: YAML frontmatter, containing at least 'name' and 'description', followed by Markdown instructions.

      Use a YAML literal block scalar (\|) to preserve the Markdown exactly. See https://agentskills.io/specification


   .. py:attribute:: source
      :type: smarter.models.sam.skillplugin.SkillSource | None

      SkillPlugin.spec.source[obj]: the remote location of the skill, in lieu of 'skill'.



.. py:class:: SAMSkillPluginSpec

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Manifest - SkillPlugin.spec.

   .. py:attribute:: prompt
      :type: SAMPluginCommonSpecPrompt

      Plugin.spec.prompt[obj]: the LLM prompt engineering to apply to the Plugin.


   .. py:attribute:: selector
      :type: SAMPluginCommonSpecSelector

      Plugin.spec.selector[obj]: the selector logic to use for the Plugin.


   .. py:attribute:: skillData
      :type: SkillData

      SkillPlugin.spec.skillData[obj]: the Agent Skill that the SkillPlugin provides to the LLM.



.. py:class:: SAMSkillPlugin

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Manifest - Skill Connection Model.

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
      :type: SAMSkillPluginSpec

      SkillPlugin.spec[obj]: Required, the SkillPlugin specification.


   .. py:attribute:: status
      :type: smarter.models.sam.skillplugin.SAMPluginCommonStatus | None

      Plugin.status[obj]: Optional, Read-only.

      Stateful status information about the Plugin.
