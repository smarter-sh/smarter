..
   Generated from the smarter-python SDK's docstrings by its scripts/generate_reference.py.
   Do not edit: change the docstring in https://github.com/smarter-sh/smarter-python, and regenerate.

SAMApiConnection
================

``smarter.models.sam.apiconnection``
------------------------------------

.. py:module:: smarter.models.sam.apiconnection

SAM model of the ``ApiConnection`` kind, generated from the Smarter platform's JSON Schema.

Do not edit: run ``scripts/generate_sam_models.py``. See :mod:`smarter.models.sam`.

.. py:class:: ApiConnection

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API - generic API Connection class.

   .. py:attribute:: apiKey
      :type: str | None

      The API key for authentication, if required.


   .. py:attribute:: authMethod
      :type: str | None

      The authentication method to use.

      Example: 'Basic Auth', 'Token Auth'.


   .. py:attribute:: baseUrl
      :type: str

      The root domain of the API.

      Example: 'https://api.example.com'.


   .. py:attribute:: proxyHost
      :type: str | None

      The remote host of the proxy connection.


   .. py:attribute:: proxyPassword
      :type: str | None

      The password for the proxy connection.


   .. py:attribute:: proxyPort
      :type: int | None

      The port of the proxy connection.


   .. py:attribute:: proxyProtocol
      :type: str | None

      The protocol of the proxy connection.

      Example: 'http', 'https'.


   .. py:attribute:: proxyUsername
      :type: str | None

      The username for the proxy connection.


   .. py:attribute:: timeout
      :type: Optional

      The timeout for the API request in seconds.

      Default is 30 seconds.



.. py:class:: SAMApiConnectionSpec

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Api Connection Manifest ApiConnection.spec.

   .. py:attribute:: connection
      :type: ApiConnection

      ApiConnection.spec.selector[obj]: the selector logic to use for the ApiConnection.



.. py:class:: SAMConnectionCommonMetadata

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Connection Manifest - common Metadata class.

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



.. py:class:: SAMConnectionCommonStatus

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Connection Manifest - Status class.

   .. py:attribute:: account_number
      :type: str

      Connection.status.account_number: The account owner of this Connection.

      Read only.


   .. py:attribute:: created
      :type: datetime

      The date in which this resource was created.

      Read only.


   .. py:attribute:: dependencies
      :type: list[smarter.models.sam.apiconnection.SAMDependency] | None

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

      Connection.status.username: The Smarter user who created this Connection.

      Read only.



.. py:class:: SAMApiConnection

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Connection Manifest - ApiConnection Model.

   .. py:attribute:: apiVersion
      :type: str

      ApiVersion[String]: Required.

      The API version of the AbstractSAMBase.


   .. py:attribute:: kind
      :type: str

      Kind[String]: Required.

      The kind of resource described by the manifest.


   .. py:attribute:: metadata
      :type: SAMConnectionCommonMetadata

      Connection.metadata[obj]: Required, the Connection metadata.


   .. py:attribute:: spec
      :type: SAMApiConnectionSpec

      ApiConnection.spec[obj]: Required, the ApiConnection specification.


   .. py:attribute:: status
      :type: smarter.models.sam.apiconnection.SAMConnectionCommonStatus | None

      Connection.status[obj]: Optional, Read-only.

      Stateful status information about the Connection.
