..
   Generated from the smarter-python SDK's docstrings by its scripts/generate_reference.py.
   Do not edit: change the docstring in https://github.com/smarter-sh/smarter-python, and regenerate.

SAMPrompt
=========

``smarter.models.sam.prompt``
-----------------------------

.. py:module:: smarter.models.sam.prompt

SAM model of the ``Prompt`` kind, generated from the Smarter platform's JSON Schema.

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



.. py:class:: SAMPromptMetadata

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Prompt Manifest - Metadata class.

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


   .. py:attribute:: tags
      :type: list[str] | None

      The tags of the manifest.

      Used for generic resource categorization and search. Example: ['tag1', 'tag2']


   .. py:attribute:: version
      :type: str | None

      The semantic version of the manifest.

      Example: 0.1.0



.. py:class:: SAMPromptSpecConfig

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Prompt Manifest Prompt.spec.config.

   .. py:attribute:: ipAddress
      :type: str | None

      Prompt.spec.configuration.ipAddress[str].

      Read only. The IP address of the client that started the chat session.


   .. py:attribute:: llmclient
      :type: str | None

      Prompt.spec.configuration.llmclient[str].

      Read only. The name of the LLMClient of the chat session.


   .. py:attribute:: sessionKey
      :type: str | None

      Prompt.spec.configuration.sessionKey[str].

      Read only. The session key of the Prompt's chat session.


   .. py:attribute:: url
      :type: str | None

      Prompt.spec.configuration.url[str].

      Read only. The url at which the chat session was started.


   .. py:attribute:: userAgent
      :type: str | None

      Prompt.spec.configuration.userAgent[str].

      Read only. The user agent of the client that started the chat session.



.. py:class:: SAMPromptStatus

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Prompt Manifest - Status class.

   .. py:attribute:: created
      :type: datetime

      The date in which this resource was created.

      Read only.


   .. py:attribute:: dependencies
      :type: list[smarter.models.sam.prompt.SAMDependency] | None

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



.. py:class:: SAMPrompt

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Manifest - Prompt.

   .. py:attribute:: apiVersion
      :type: str

      ApiVersion[String]: Required.

      The API version of the AbstractSAMBase.


   .. py:attribute:: kind
      :type: str

      Kind[String]: Required.

      The kind of resource described by the manifest.


   .. py:attribute:: metadata
      :type: SAMPromptMetadata

      Prompt.metadata[obj]: Required, the Prompt metadata.


   .. py:attribute:: spec
      :type: SAMPromptSpecConfig

      Prompt.spec[obj]: Required, the Prompt specification.


   .. py:attribute:: status
      :type: smarter.models.sam.prompt.SAMPromptStatus | None

      Prompt.status[obj]: Optional, Read-only.

      Stateful status information about the Prompt.
