..
   Generated from the smarter-python SDK's docstrings by its scripts/generate_reference.py.
   Do not edit: change the docstring in https://github.com/smarter-sh/smarter-python, and regenerate.

SAMMCPClient
============

``smarter.models.sam.mcpclient``
--------------------------------

.. py:module:: smarter.models.sam.mcpclient

SAM model of the ``MCPClient`` kind, generated from the Smarter platform's JSON Schema.

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



.. py:class:: SAMMCPClientMetadata

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API MCPClient Manifest - Metadata class.

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



.. py:class:: SAMMCPClientSpecConfig

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API MCPClient Manifest MCPClient.spec.config.

   .. py:attribute:: allowedResources
      :type: list[str] | None

      MCPClient.spec.config.allowedResources[list]: glob patterns of the resource URIs that the LLM may read, e.g. docs://example.com/\* .

      Empty means none.


   .. py:attribute:: allowedTools
      :type: list[str] | None

      MCPClient.spec.config.allowedTools[list]: glob patterns of the tool names to offer the LLM, e.g. search\_\* .

      Empty means all of the tools that the server advertises.


   .. py:attribute:: apiKeyHeader
      :type: str | None

      MCPClient.spec.config.apiKeyHeader[str]: the HTTP header that carries an api_key credential.


   .. py:attribute:: authType
      :type: str | None

      MCPClient.spec.config.authType[str]: how to authenticate with the MCP server.

      One of: ['none', 'api_key', 'bearer_token', 'oauth2']. oauth2 sends an OAuth access token, obtained elsewhere, as a bearer token.


   .. py:attribute:: cacheTtl
      :type: Optional

      MCPClient.spec.config.cacheTtl[int]: seconds to cache the MCP server's tools, instructions and capabilities.

      0 disables caching.


   .. py:attribute:: credentials
      :type: str | None

      MCPClient.spec.config.credentials[str]: the name of the Smarter Secret containing the credential.

      Required unless authType is none.


   .. py:attribute:: endpointUrl
      :type: str

      MCPClient.spec.config.endpointUrl[str]: the https URL of the MCP server's endpoint.


   .. py:attribute:: headers
      :type: dict[str, str] | None

      MCPClient.spec.config.headers[dict]: optional, non-secret HTTP headers to send to the MCP server.

      Credentials belong in a Smarter Secret, via credentials.


   .. py:attribute:: includeInstructions
      :type: bool | None

      MCPClient.spec.config.includeInstructions[bool]: add the MCP server's instructions to the system prompt.


   .. py:attribute:: isActive
      :type: bool | None

      MCPClient.spec.config.isActive[bool]: whether LLMClients use this MCPClient.


   .. py:attribute:: priority
      :type: Optional

      MCPClient.spec.config.priority[int]: the order in which an LLMClient's MCPClients are offered to the LLM.

      Lower runs first.


   .. py:attribute:: timeout
      :type: Optional

      MCPClient.spec.config.timeout[int]: seconds to wait for the MCP server to connect and respond.


   .. py:attribute:: transport
      :type: str | None

      MCPClient.spec.config.transport[str]: the MCP transport.

      One of: ['http', 'sse']. http is Streamable HTTP, and sse is the legacy HTTP+SSE transport.



.. py:class:: SAMMCPClientStatus

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API MCPClient Manifest - Status class.

   Read only. Besides ownership, it reports the result of the last connection to the MCP server.

   .. py:attribute:: accountNumber
      :type: str

      MCPClient.status.account_number: The account owner of this MCPClient.

      Read only.


   .. py:attribute:: connectionStatus
      :type: str | None

      MCPClient.status.connectionStatus: the result of the last connection to the MCP server: unconfigured, connected, disconnected or error.

      Read only.


   .. py:attribute:: created
      :type: datetime

      The date in which this resource was created.

      Read only.


   .. py:attribute:: dependencies
      :type: list[smarter.models.sam.mcpclient.SAMDependency] | None

      Dependencies[List]: The resources that depend on this resource, and that must be deleted, or stop referring to it, before it can be deleted.

      Lists only the resources that you can read. Read only.


   .. py:attribute:: lastConnected
      :type: datetime.datetime | None

      MCPClient.status.lastConnected: when Smarter last connected to the MCP server.

      Read only.


   .. py:attribute:: lastError
      :type: str | None

      MCPClient.status.lastError: the error of the last failed connection, if any.

      Read only.


   .. py:attribute:: modified
      :type: datetime

      The date in which this resource was most recently changed.

      Read only.


   .. py:attribute:: protocolVersion
      :type: str | None

      MCPClient.status.protocolVersion: the MCP protocol version negotiated with the server.

      Read only.


   .. py:attribute:: recordLocator
      :type: str

      RecordLocator[String]: An optional identifier used to locate the resource record associated with this manifest.

      Read only.


   .. py:attribute:: serverName
      :type: str | None

      MCPClient.status.serverName: the name that the MCP server reported.

      Read only.


   .. py:attribute:: serverVersion
      :type: str | None

      MCPClient.status.serverVersion: the version that the MCP server reported.

      Read only.


   .. py:attribute:: tools
      :type: list[str] | None

      MCPClient.status.tools: the names of the MCP server's tools that this MCPClient offers the LLM, as of the last connection.

      Read only.


   .. py:attribute:: username
      :type: str

      MCPClient.status.username: The Smarter user who created this MCPClient.

      Read only.



.. py:class:: SAMMCPClientSpec

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API MCPClient Manifest MCPClient.spec.

   .. py:attribute:: config
      :type: SAMMCPClientSpecConfig

      MCPClient.spec.config[object].

      The configuration for the MCPClient.



.. py:class:: SAMMCPClient

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Manifest - MCPClient.

   .. py:attribute:: apiVersion
      :type: str

      ApiVersion[String]: Required.

      The API version of the AbstractSAMBase.


   .. py:attribute:: kind
      :type: str

      Kind[String]: Required.

      The kind of resource described by the manifest.


   .. py:attribute:: metadata
      :type: SAMMCPClientMetadata

      MCPClient.metadata[obj]: Required, the MCPClient metadata.


   .. py:attribute:: spec
      :type: SAMMCPClientSpec

      MCPClient.spec[obj]: Required, the MCPClient specification.


   .. py:attribute:: status
      :type: smarter.models.sam.mcpclient.SAMMCPClientStatus | None

      MCPClient.status[obj]: Optional, Read-only.

      Stateful status information about the MCPClient.
