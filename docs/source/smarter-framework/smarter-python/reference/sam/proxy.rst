..
   Generated from the smarter-python SDK's docstrings by its scripts/generate_reference.py.
   Do not edit: change the docstring in https://github.com/smarter-sh/smarter-python, and regenerate.

SAMProxy
========

``smarter.models.sam.proxy``
----------------------------

.. py:module:: smarter.models.sam.proxy

SAM model of the ``Proxy`` kind, generated from the Smarter platform's JSON Schema.

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



.. py:class:: SAMProxyMetadata

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Proxy Manifest - Metadata class.

   .. py:attribute:: annotations
      :type: None | list[dict[str, str | int | float | bool | datetime.date | datetime.datetime | uuid.UUID | bytes | list | dict[str, Any]]]

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



.. py:class:: SAMProxySpecAuth

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Spec.auth: how the provider expects its API key.

   .. py:attribute:: header
      :type: str | None

      Proxy.spec.auth.header[str]: the HTTP header in which the provider expects its API key, e.g. Authorization (OpenAI), x-api-key (Anthropic) or x-goog-api-key (Google Gemini).


   .. py:attribute:: scheme
      :type: str | None

      Proxy.spec.auth.scheme[str]: the prefix of the API key in the header, e.g. Bearer.

      Empty or null for none, e.g. for x-api-key.



.. py:class:: SAMProxyStatus

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Proxy Manifest - Status class.

   Read only. Besides ownership, it reports where the Proxy is, and where it forwards to.

   .. py:attribute:: accountNumber
      :type: str

      Proxy.status.accountNumber: The account owner of this Proxy.

      Read only.


   .. py:attribute:: apiKeySecret
      :type: str | None

      Proxy.status.apiKeySecret: The name of the Secret whose API key is added to requests: spec.apiKey, else the Provider's.

      None if there is none. Read only.


   .. py:attribute:: created
      :type: datetime

      The date in which this resource was created.

      Read only.


   .. py:attribute:: dependencies
      :type: list[smarter.models.sam.proxy.SAMDependency] | None

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


   .. py:attribute:: upstreamUrl
      :type: str | None

      Proxy.status.upstreamUrl: The base URL of the provider's API, to which requests are forwarded: spec.baseUrl, else the Provider's.

      Read only.


   .. py:attribute:: url
      :type: str | None

      Proxy.status.url: The URL of the Proxy's passthrough endpoint, to use as the base URL of the provider's SDK.

      Read only.


   .. py:attribute:: username
      :type: str

      Proxy.status.username: The Smarter user who created this Proxy.

      Read only.



.. py:class:: SAMProxySpec

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Proxy Manifest Proxy.spec.

   .. py:attribute:: allowedPaths
      :type: list[str] | None

      Proxy.spec.allowedPaths[list]: glob patterns of the paths, relative to baseUrl, that callers may use, e.g. chat/completions or models/\*.

      Empty allows every path.


   .. py:attribute:: apiKey
      :type: str | None

      Proxy.spec.apiKey[str]: the name of the Secret that contains the provider's API key.

      It must belong to, or be shared with, the manifest's owner. Defaults to the Provider's API key.


   .. py:attribute:: auth
      :type: smarter.models.sam.proxy.SAMProxySpecAuth | None

      Proxy.spec.auth[object]: how the provider expects its API key.

      Defaults to Authorization: Bearer.


   .. py:attribute:: baseUrl
      :type: str | None

      Proxy.spec.baseUrl[str]: the base URL of the provider's API, e.g. https://api.openai.com/v1/.

      Defaults to the Provider's base URL.


   .. py:attribute:: headers
      :type: dict[str, str] | None

      Proxy.spec.headers[dict]: other HTTP headers that are added to every request, e.g. anthropic-version.

      They replace the caller's headers of the same name.


   .. py:attribute:: isActive
      :type: bool | None

      Proxy.spec.isActive[bool]: inactive Proxy refuse every request.


   .. py:attribute:: provider
      :type: str

      Proxy.spec.provider[str]: the name of the Provider whose API the Proxy forwards to, e.g. openai.

      It must belong to, or be shared with, the manifest's owner.


   .. py:attribute:: timeout
      :type: Optional

      Proxy.spec.timeout[int]: the most seconds to wait for the provider's response.



.. py:class:: SAMProxy

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Manifest - Proxy.

   .. py:attribute:: apiVersion
      :type: str

      ApiVersion[String]: Required.

      The API version of the AbstractSAMBase.


   .. py:attribute:: kind
      :type: str

      Kind[String]: Required.

      The kind of resource described by the manifest.


   .. py:attribute:: metadata
      :type: SAMProxyMetadata

      Proxy.metadata[obj]: Required, the Proxy metadata.


   .. py:attribute:: spec
      :type: SAMProxySpec

      Proxy.spec[obj]: Required, the Proxy specification.


   .. py:attribute:: status
      :type: smarter.models.sam.proxy.SAMProxyStatus | None

      Proxy.status[obj]: Optional, Read-only.

      Stateful status information about the Proxy.
