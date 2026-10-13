..
   Generated from the smarter-python SDK's docstrings by its scripts/generate_reference.py.
   Do not edit: change the docstring in https://github.com/smarter-sh/smarter-python, and regenerate.

Models
======

``smarter.models.base``
-----------------------

.. py:module:: smarter.models.base

The base classes of the SDK's response models.

Every model allows extra fields. The Smarter platform adds fields to its responses in minor
releases, and an SDK that rejected them would break whenever the platform is upgraded. Extra fields
are kept, and are available as attributes and in :meth:`SmarterModel.to_dict`.

.. py:class:: SmarterModel

   Bases: :class:`pydantic.main.BaseModel`

   The base class of the SDK's models: a Pydantic model that keeps unknown fields.

   Pydantic's ``model_`` namespace isn't protected, because the api has fields such as an LLMHost's
   ``modelTask``, which older Pydantic versions would warn about.

   .. py:method:: to_dict() -> dict[str, typing.Any]

      The model as a JSON-compatible dict, with the api's own field names.

      :returns: The fields that the api returned, or that were set.


   .. py:method:: to_json(indent: Optional[int] = 2) -> str

      The model as JSON text, with the api's own field names.

      :param indent: The indentation, or None for compact JSON.
      :returns: The JSON text.



.. py:class:: SmarterCamelModel

   Bases: :class:`smarter.models.base.SmarterModel`

   A model of a response whose field names are camelCase, e.g. ``hashedId``.

   Its attributes are snake_case (``hashed_id``), and it accepts either spelling.


.. py:class:: SmarterUserRef

   Bases: :class:`smarter.models.base.SmarterCamelModel`

   The user of a resource's owner.

   .. py:attribute:: username
      :type: str


   .. py:attribute:: email
      :type: Optional



.. py:class:: SmarterAccountRef

   Bases: :class:`smarter.models.base.SmarterCamelModel`

   The account of a resource's owner.

   .. py:attribute:: account_number
      :type: str
      :value: alias ``accountNumber``



.. py:class:: SmarterOwner

   Bases: :class:`smarter.models.base.SmarterCamelModel`

   The owner of a resource: its user profile, as the user and the account.

   .. py:attribute:: user
      :type: Optional


   .. py:attribute:: account
      :type: Optional



.. py:class:: SmarterResource

   Bases: :class:`smarter.models.base.SmarterCamelModel`

   The fields that every Smarter resource shares, as the REST api returns them.

   The api's resources are Django rows with the same metadata as a manifest's ``metadata``: a name,
   description, version, tags and annotations. Each resource's model adds its own fields.

   .. py:attribute:: id
      :type: int


   .. py:attribute:: hashed_id
      :type: Optional
      :value: alias ``hashedId``


   .. py:attribute:: name
      :type: str


   .. py:attribute:: description
      :type: Optional


   .. py:attribute:: version
      :type: Optional


   .. py:attribute:: tags
      :type: list


   .. py:attribute:: annotations
      :type: list


   .. py:attribute:: created_at
      :type: Optional
      :value: alias ``createdAt``


   .. py:attribute:: updated_at
      :type: Optional
      :value: alias ``updatedAt``


   .. py:attribute:: user_profile
      :type: Optional
      :value: alias ``userProfile``


   .. py:attribute:: can_delete
      :type: Optional
      :value: alias ``canDelete``


   .. py:attribute:: manifest_url
      :type: Optional
      :value: alias ``manifestUrl``


   .. py:attribute:: ready
      :type: Optional



``smarter.models.manifest``
---------------------------

.. py:module:: smarter.models.manifest

Models of Smarter Application Manifests (SAM): the YAML documents that declare every Smarter resource.

A manifest has the same four sections as a Kubernetes manifest: ``apiVersion``, ``kind``,
``metadata`` and ``spec``. ``describe`` adds a read-only ``status``. The shape of ``spec`` depends on
the kind and the platform's version, so it is a JSON object here. The platform publishes the
complete JSON Schema of each kind: see :meth:`smarter.resources.manifests.Manifests.json_schema`.

.. py:data:: SMARTER_API_VERSION

   The ``apiVersion`` of every Smarter manifest.

.. py:class:: ManifestMetadata

   Bases: :class:`smarter.models.base.SmarterModel`

   A manifest's ``metadata``: the resource's name, and descriptive information about it.

   .. py:attribute:: name
      :type: str

      The resource's name, unique per account and kind, in snake_case.


   .. py:attribute:: description
      :type: Optional


   .. py:attribute:: version
      :type: Optional

      The resource's semantic version, e.g. 1.0.0.


   .. py:attribute:: tags
      :type: list


   .. py:attribute:: annotations
      :type: list

      Key-value pairs, as a list of single-key objects.



.. py:class:: Manifest

   Bases: :class:`smarter.models.base.SmarterModel`

   A Smarter Application Manifest.

   .. code-block:: python

       manifest = Manifest.from_yaml(open("llmclient.yaml").read())
       manifest.metadata.name
       manifest.spec["config"]["provider"]

   .. py:attribute:: apiVersion
      :type: str


   .. py:attribute:: kind
      :type: str

      The resource kind, e.g. LLMClient. See Smarter.kinds().


   .. py:attribute:: metadata
      :type: ManifestMetadata


   .. py:attribute:: spec
      :type: dict

      The resource's specification.


   .. py:attribute:: status
      :type: Optional

      Read-only state, returned by describe.


   .. py:method:: from_yaml(text: str) -> 'Manifest'
      :classmethod:

      Parse a manifest from YAML (or JSON) text.

      :param text: The manifest's text.
      :returns: The manifest.
      :raises SmarterValueError: If the text is not a YAML object.


   .. py:method:: from_file(path: Union[str, pathlib.Path]) -> 'Manifest'
      :classmethod:

      Read a manifest from a YAML or JSON file.

      :param path: The file's path.
      :returns: The manifest.


   .. py:method:: to_sam() -> 'SAMModel'

      The manifest as its kind's typed SAM model, e.g. a :class:`~smarter.models.sam.SAMGuardrail`.

      .. code-block:: python

          guardrail = client.guardrails.describe("pii_redactor").to_sam()
          print(guardrail.spec.config.action)

      :returns: The typed manifest.
      :raises SmarterValueError: If the SDK has no model of the manifest's kind.
      :raises pydantic.ValidationError: If the manifest does not match its kind's model.


   .. py:method:: to_yaml() -> str

      The manifest as YAML text, without its read-only ``status``, ready to apply.

      :returns: The YAML text.



.. py:class:: ManifestListTitle

   Bases: :class:`smarter.models.base.SmarterModel`

   A column of a ``get`` result: the field's name, and its Django field type.

   .. py:attribute:: name
      :type: str


   .. py:attribute:: type
      :type: str



.. py:class:: ManifestListData

   Bases: :class:`smarter.models.base.SmarterModel`

   The table of a ``get`` result.

   .. py:attribute:: titles
      :type: list


   .. py:attribute:: items
      :type: list



.. py:class:: ManifestListMetadata

   Bases: :class:`smarter.models.base.SmarterModel`

   The ``metadata`` of a ``get`` result.

   .. py:attribute:: count
      :type: int



.. py:class:: ManifestList

   Bases: :class:`smarter.models.base.SmarterModel`

   The result of ``get``: the resources of one kind, as a table.

   ``data.items`` are the rows, and ``data.titles`` their columns. The columns depend on the kind.

   .. py:attribute:: apiVersion
      :type: str


   .. py:attribute:: kind
      :type: str


   .. py:attribute:: name
      :type: Optional


   .. py:attribute:: metadata
      :type: ManifestListMetadata


   .. py:attribute:: data
      :type: ManifestListData


   .. py:property:: items

      The rows.


   .. py:property:: names

      The names of the resources: each row's ``name``, or its ``username`` for the User kind.



.. py:class:: KindInfo

   Bases: :class:`smarter.models.base.SmarterCamelModel`

   A resource kind that the platform supports, as ``/api/v1/cli/resources/`` describes it.

   .. py:attribute:: singular
      :type: str
      :value: alias ``Singular``


   .. py:attribute:: plural
      :type: str
      :value: alias ``Plural``


   .. py:attribute:: api_kind
      :type: str
      :value: alias ``APIKind``

      The kind, as it appears in a manifest.


   .. py:attribute:: display
      :type: Optional
      :value: alias ``Display``


   .. py:attribute:: display_plural
      :type: Optional
      :value: alias ``DisplayPlural``


   .. py:attribute:: deployable
      :type: bool
      :value: alias ``Deployable``

      True if the kind can be deployed.



``smarter.models.platform``
---------------------------

.. py:module:: smarter.models.platform

Models of the platform's own endpoints: ``whoami``, ``version`` and ``status``.

.. py:class:: WhoAmI

   Bases: :class:`smarter.models.base.SmarterModel`

   The owner of the api key: the user, their account, and the platform's environment.

   .. py:attribute:: user
      :type: User


   .. py:attribute:: account
      :type: Account


   .. py:attribute:: environment
      :type: Optional

      The platform's environment, e.g. local or prod.



.. py:class:: ApiVersion

   Bases: :class:`smarter.models.base.SmarterModel`

   The platform's version, and the versions of its main Python packages.

   .. py:attribute:: version
      :type: str

      The Smarter platform's semantic version.


   .. py:attribute:: python
      :type: dict

      Python package versions, by package.



.. py:class:: CliVersion

   Bases: :class:`smarter.models.base.SmarterModel`

   The version of the smarter cli that the platform recommends.

   .. py:attribute:: version
      :type: Optional



.. py:class:: PlatformVersion

   Bases: :class:`smarter.models.base.SmarterModel`

   The response of ``version``.

   .. py:attribute:: api
      :type: ApiVersion


   .. py:attribute:: cli
      :type: Optional



.. py:class:: PlatformStatus

   Bases: :class:`smarter.models.base.SmarterCamelModel`

   The response of ``status``: the state of the platform's infrastructure and compute.

   The sections' contents depend on how the platform is hosted, so they are JSON objects.

   .. py:attribute:: infrastructures
      :type: dict


   .. py:attribute:: compute
      :type: dict



``smarter.models.account``
--------------------------

.. py:module:: smarter.models.account

Models of accounts, users, user profiles and account contacts, as ``/api/v1/accounts/`` returns them.

.. py:class:: Account

   Bases: :class:`smarter.models.base.SmarterResource`

   A Smarter account: the tenant that owns users and resources.

   .. py:attribute:: account_number
      :type: str
      :value: alias ``accountNumber``


   .. py:attribute:: is_default_account
      :type: Optional
      :value: alias ``isDefaultAccount``


   .. py:attribute:: company_name
      :type: Optional
      :value: alias ``companyName``


   .. py:attribute:: phone_number
      :type: Optional
      :value: alias ``phoneNumber``


   .. py:attribute:: address1
      :type: Optional


   .. py:attribute:: address2
      :type: Optional


   .. py:attribute:: city
      :type: Optional


   .. py:attribute:: state
      :type: Optional


   .. py:attribute:: postal_code
      :type: Optional
      :value: alias ``postalCode``


   .. py:attribute:: country
      :type: Optional


   .. py:attribute:: language
      :type: Optional


   .. py:attribute:: timezone
      :type: Optional


   .. py:attribute:: currency
      :type: Optional


   .. py:attribute:: is_active
      :type: Optional
      :value: alias ``isActive``



.. py:class:: User

   Bases: :class:`smarter.models.base.SmarterCamelModel`

   A user of the platform.

   .. py:attribute:: id
      :type: int


   .. py:attribute:: username
      :type: str


   .. py:attribute:: first_name
      :type: Optional
      :value: alias ``firstName``


   .. py:attribute:: last_name
      :type: Optional
      :value: alias ``lastName``


   .. py:attribute:: email
      :type: Optional


   .. py:attribute:: is_staff
      :type: Optional
      :value: alias ``isStaff``


   .. py:attribute:: is_superuser
      :type: Optional
      :value: alias ``isSuperuser``



.. py:class:: UserProfile

   Bases: :class:`smarter.models.base.SmarterResource`

   A user's membership of an account, which owns the resources that the user creates in it.

   .. py:attribute:: user
      :type: User


   .. py:attribute:: account
      :type: SmarterAccountRef


   .. py:attribute:: profile_image_url
      :type: Optional
      :value: alias ``profileImageUrl``


   .. py:attribute:: is_test
      :type: Optional
      :value: alias ``isTest``



.. py:class:: AccountContact

   Bases: :class:`smarter.models.base.SmarterCamelModel`

   A contact of an account, who receives its notices.

   .. py:attribute:: id
      :type: int


   .. py:attribute:: account
      :type: Optional


   .. py:attribute:: created_at
      :type: Optional
      :value: alias ``createdAt``


   .. py:attribute:: updated_at
      :type: Optional
      :value: alias ``updatedAt``


   .. py:attribute:: first_name
      :type: Optional
      :value: alias ``firstName``


   .. py:attribute:: last_name
      :type: Optional
      :value: alias ``lastName``


   .. py:attribute:: email
      :type: Optional


   .. py:attribute:: phone
      :type: Optional


   .. py:attribute:: is_primary
      :type: Optional
      :value: alias ``isPrimary``


   .. py:attribute:: is_test
      :type: Optional
      :value: alias ``isTest``


   .. py:attribute:: welcomed
      :type: Optional



``smarter.models.llmclient``
----------------------------

.. py:module:: smarter.models.llmclient

Models of LLMClients and their plugins, built-in functions, api keys and custom domains.

.. py:class:: LLMClientPluginRef

   Bases: :class:`smarter.models.base.SmarterCamelModel`

   A plugin of an LLMClient, by its id and name.

   .. py:attribute:: id
      :type: int


   .. py:attribute:: name
      :type: Optional



.. py:class:: LLMClientFunction

   Bases: :class:`smarter.models.base.SmarterCamelModel`

   A built-in function of an LLMClient, e.g. ``calculator``.

   .. py:attribute:: id
      :type: int


   .. py:attribute:: name
      :type: Optional


   .. py:attribute:: llmclient
      :type: Optional


   .. py:attribute:: created_at
      :type: Optional
      :value: alias ``createdAt``


   .. py:attribute:: updated_at
      :type: Optional
      :value: alias ``updatedAt``



.. py:class:: LLMClientPlugin

   Bases: :class:`smarter.models.base.SmarterCamelModel`

   The association of a plugin with an LLMClient.

   .. py:attribute:: id
      :type: int


   .. py:attribute:: plugin_meta
      :type: Plugin
      :value: alias ``pluginMeta``


   .. py:attribute:: llmclient
      :type: Optional



.. py:class:: LLMClientApiKey

   Bases: :class:`smarter.models.base.SmarterCamelModel`

   An api key that may call an LLMClient that requires authentication.

   .. py:attribute:: id
      :type: int


   .. py:attribute:: llmclient
      :type: Optional


   .. py:attribute:: api_key
      :type: Optional
      :value: alias ``apiKey``

      The api key's public key_id, a UUID. Never the key itself.


   .. py:attribute:: created_at
      :type: Optional
      :value: alias ``createdAt``


   .. py:attribute:: updated_at
      :type: Optional
      :value: alias ``updatedAt``



.. py:class:: LLMClientCustomDomain

   Bases: :class:`smarter.models.base.SmarterCamelModel`

   A custom domain on which an LLMClient is deployed: the domain itself, and its verification.

   .. py:attribute:: id
      :type: int


   .. py:attribute:: name
      :type: Optional


   .. py:attribute:: description
      :type: Optional


   .. py:attribute:: version
      :type: Optional


   .. py:attribute:: domain_name
      :type: Optional
      :value: alias ``domainName``

      The domain, e.g. example.com.


   .. py:attribute:: verification_status
      :type: Optional
      :value: alias ``verificationStatus``

      Not Verified, Verifying, Verified or Failed.


   .. py:attribute:: verified_at
      :type: Optional
      :value: alias ``verifiedAt``


   .. py:attribute:: verification_message
      :type: Optional
      :value: alias ``verificationMessage``


   .. py:attribute:: user_profile
      :type: Optional
      :value: alias ``userProfile``

      The owner's user profile id.


   .. py:attribute:: created_at
      :type: Optional
      :value: alias ``createdAt``


   .. py:attribute:: updated_at
      :type: Optional
      :value: alias ``updatedAt``



.. py:class:: LLMClient

   Bases: :class:`smarter.models.base.SmarterResource`

   An LLMClient: a deployable AI agent, built from an LLM provider and model, a system prompt, plugins and functions.

   Prompt it with :meth:`smarter.resources.llmclients.LLMClients.prompt`, or start a chat with
   :meth:`smarter.resources.llmclients.LLMClients.chat`.

   .. py:attribute:: can_delete
      :type: Optional
      :value: alias ``canDelete``

      Whether the api key's user may delete the LLMClient now.


   .. py:attribute:: ready
      :type: Optional

      Whether the LLMClient can be prompted.


   .. py:attribute:: rfc1034_compliant_name
      :type: Optional
      :value: alias ``rfc1034CompliantName``


   .. py:attribute:: provider
      :type: Optional


   .. py:attribute:: default_model
      :type: Optional
      :value: alias ``defaultModel``


   .. py:attribute:: default_system_role
      :type: Optional
      :value: alias ``defaultSystemRole``

      The system prompt of a new chat session.


   .. py:attribute:: deployed
      :type: Optional


   .. py:attribute:: default_host
      :type: Optional
      :value: alias ``defaultHost``


   .. py:attribute:: default_url
      :type: Optional
      :value: alias ``defaultUrl``


   .. py:attribute:: custom_host
      :type: Optional
      :value: alias ``customHost``


   .. py:attribute:: custom_url
      :type: Optional
      :value: alias ``customUrl``


   .. py:attribute:: sandbox_host
      :type: Optional
      :value: alias ``sandboxHost``


   .. py:attribute:: sandbox_url
      :type: Optional
      :value: alias ``sandboxUrl``


   .. py:attribute:: url_llmclient
      :type: Optional
      :value: alias ``urlLlmclient``

      Where to send prompts: the chat api's prompt url.


   .. py:attribute:: url_chat_config
      :type: Optional
      :value: alias ``urlChatConfig``

      The chat api's configuration url.


   .. py:attribute:: is_authentication_required
      :type: Optional
      :value: alias ``isAuthenticationRequired``

      Whether prompting the LLMClient requires an api key.


   .. py:attribute:: functions
      :type: list


   .. py:attribute:: plugins
      :type: list


   .. py:attribute:: api_keys
      :type: list
      :value: alias ``apiKeys``


   .. py:attribute:: custom_domains
      :type: list
      :value: alias ``customDomains``



``smarter.models.plugin``
-------------------------

.. py:module:: smarter.models.plugin

Models of plugins: the tools that an LLMClient's LLM can call.

.. py:class:: Plugin

   Bases: :class:`smarter.models.base.SmarterResource`

   A plugin's metadata.

   Its ``kind`` is the manifest kind, e.g. ``ApiPlugin`` or ``SqlPlugin``, and its ``plugin_class``
   the implementation: api, skill, sql, static, websearch or imagesearch.

   .. py:attribute:: plugin_class
      :type: Optional
      :value: alias ``pluginClass``

      api, skill, sql, static, websearch or imagesearch.


   .. py:attribute:: kind
      :type: Optional

      The manifest kind, e.g. ApiPlugin.



``smarter.models.guardrail``
----------------------------

.. py:module:: smarter.models.guardrail

Models of guardrails, their evaluations, and their events.

.. py:class:: Guardrail

   Bases: :class:`smarter.models.base.SmarterResource`

   A guardrail: a check that the platform runs on prompts (``input``) or on the LLM's replies (``output``).

   .. py:attribute:: stage
      :type: Optional

      input or output.


   .. py:attribute:: category
      :type: Optional


   .. py:attribute:: strategy
      :type: Optional

      e.g. regex, detector, classifier or llm.


   .. py:attribute:: pattern
      :type: Optional


   .. py:attribute:: config
      :type: Optional


   .. py:attribute:: threshold
      :type: Optional


   .. py:attribute:: action
      :type: Optional

      e.g. block, redact or flag.


   .. py:attribute:: replacement
      :type: Optional


   .. py:attribute:: message
      :type: Optional


   .. py:attribute:: severity
      :type: Optional


   .. py:attribute:: mode
      :type: Optional

      enforce or monitor.


   .. py:attribute:: fail_closed
      :type: Optional
      :value: alias ``failClosed``


   .. py:attribute:: priority
      :type: Optional


   .. py:attribute:: is_active
      :type: Optional
      :value: alias ``isActive``



.. py:class:: GuardrailMatch

   Bases: :class:`smarter.models.base.SmarterModel`

   A span of the text that a guardrail matched.

   .. py:attribute:: start
      :type: int


   .. py:attribute:: end
      :type: int


   .. py:attribute:: text
      :type: str


   .. py:attribute:: label
      :type: Optional



.. py:class:: GuardrailFinding

   Bases: :class:`smarter.models.base.SmarterModel`

   One finding of a guardrail evaluation.

   .. py:attribute:: confidence
      :type: Optional


   .. py:attribute:: rationale
      :type: Optional


   .. py:attribute:: matches
      :type: list



.. py:class:: GuardrailEvaluation

   Bases: :class:`smarter.models.base.SmarterCamelModel`

   The result of a guardrail's dry run on a text.

   Nothing is saved: an evaluation does not create an event.

   .. py:attribute:: guardrail
      :type: str


   .. py:attribute:: stage
      :type: str


   .. py:attribute:: triggered
      :type: bool


   .. py:attribute:: disposition
      :type: Optional

      e.g. passed, blocked, redacted or flagged.


   .. py:attribute:: text
      :type: Optional

      The text after the guardrail's action, e.g. redacted.


   .. py:attribute:: message
      :type: Optional


   .. py:attribute:: error
      :type: Optional


   .. py:attribute:: duration_ms
      :type: Optional
      :value: alias ``durationMs``


   .. py:attribute:: findings
      :type: list



.. py:class:: GuardrailEvent

   Bases: :class:`smarter.models.base.SmarterCamelModel`

   A guardrail's finding in a real prompt, saved for review.

   .. py:attribute:: id
      :type: int


   .. py:attribute:: created_at
      :type: Optional
      :value: alias ``createdAt``


   .. py:attribute:: llmclient
      :type: Optional

      The name of the LLMClient whose prompt triggered it.


   .. py:attribute:: stage
      :type: Optional


   .. py:attribute:: disposition
      :type: Optional


   .. py:attribute:: reviewed
      :type: Optional



.. py:class:: GuardrailEvents

   Bases: :class:`smarter.models.base.SmarterModel`

   The latest events of a guardrail.

   .. py:attribute:: guardrail
      :type: str


   .. py:attribute:: events
      :type: list



``smarter.models.mcpclient``
----------------------------

.. py:module:: smarter.models.mcpclient

Models of MCPClients: connections to Model Context Protocol servers, whose tools an LLMClient's LLM can call.

.. py:class:: MCPClient

   Bases: :class:`smarter.models.base.SmarterResource`

   An MCPClient: an MCP server, how to reach it, and which of its tools the LLM may call.

   .. py:attribute:: transport
      :type: Optional

      http, sse or stdio.


   .. py:attribute:: endpoint_url
      :type: Optional
      :value: alias ``endpointUrl``


   .. py:attribute:: command
      :type: Optional


   .. py:attribute:: timeout
      :type: Optional


   .. py:attribute:: auth_type
      :type: Optional
      :value: alias ``authType``


   .. py:attribute:: allowed_tools
      :type: list
      :value: alias ``allowedTools``


   .. py:attribute:: allowed_resources
      :type: list
      :value: alias ``allowedResources``


   .. py:attribute:: include_instructions
      :type: Optional
      :value: alias ``includeInstructions``


   .. py:attribute:: cache_ttl
      :type: Optional
      :value: alias ``cacheTtl``


   .. py:attribute:: is_active
      :type: Optional
      :value: alias ``isActive``


   .. py:attribute:: status
      :type: Optional

      e.g. connected or error.


   .. py:attribute:: priority
      :type: Optional


   .. py:attribute:: protocol_version
      :type: Optional
      :value: alias ``protocolVersion``


   .. py:attribute:: server_name
      :type: Optional
      :value: alias ``serverName``


   .. py:attribute:: server_version
      :type: Optional
      :value: alias ``serverVersion``


   .. py:attribute:: tools
      :type: list

      The names of every tool that the server offers.


   .. py:attribute:: last_connected_at
      :type: Optional
      :value: alias ``lastConnectedAt``


   .. py:attribute:: last_error
      :type: Optional
      :value: alias ``lastError``



.. py:class:: MCPClientStatus

   Bases: :class:`smarter.models.base.SmarterCamelModel`

   The connection state of an MCPClient.

   .. py:attribute:: name
      :type: str


   .. py:attribute:: status
      :type: Optional


   .. py:attribute:: protocol_version
      :type: Optional
      :value: alias ``protocolVersion``


   .. py:attribute:: server_name
      :type: Optional
      :value: alias ``serverName``


   .. py:attribute:: server_version
      :type: Optional
      :value: alias ``serverVersion``


   .. py:attribute:: last_connected
      :type: Optional
      :value: alias ``lastConnected``


   .. py:attribute:: last_error
      :type: Optional
      :value: alias ``lastError``


   .. py:attribute:: error
      :type: Optional

      The error of a failed refresh.



.. py:class:: MCPTool

   Bases: :class:`smarter.models.base.SmarterCamelModel`

   A tool of an MCP server, which the MCPClient allows the LLM to call.

   .. py:attribute:: name
      :type: str


   .. py:attribute:: title
      :type: Optional


   .. py:attribute:: description
      :type: Optional


   .. py:attribute:: input_schema
      :type: Optional
      :value: alias ``inputSchema``

      The tool's arguments, as a JSON Schema.


   .. py:attribute:: read_only
      :type: Optional
      :value: alias ``readOnly``


   .. py:attribute:: destructive
      :type: Optional



.. py:class:: MCPClientTools

   Bases: :class:`smarter.models.mcpclient.MCPClientStatus`

   An MCPClient's allowed tools, and the server's instructions.

   .. py:attribute:: instructions
      :type: Optional


   .. py:attribute:: tools
      :type: list



.. py:class:: MCPToolResult

   Bases: :class:`smarter.models.base.SmarterCamelModel`

   The result of a tool call.

   .. py:attribute:: name
      :type: str

      The MCPClient's name.


   .. py:attribute:: tool
      :type: str


   .. py:attribute:: is_error
      :type: bool
      :value: alias ``isError``


   .. py:attribute:: content
      :type: Optional

      The tool's result, as text.



``smarter.models.vectorstore``
------------------------------

.. py:module:: smarter.models.vectorstore

Models of vectorstores, their documents and snapshots, and search results.

.. py:class:: Vectorstore

   Bases: :class:`smarter.models.base.SmarterResource`

   A vectorstore: a vector database, hosted by Smarter or by a provider, for retrieval-augmented generation.

   .. py:attribute:: backend
      :type: Optional

      e.g. qdrant or pinecone.


   .. py:attribute:: hosting
      :type: Optional

      self_hosted or managed.


   .. py:attribute:: is_active
      :type: Optional
      :value: alias ``isActive``


   .. py:attribute:: dimension
      :type: Optional


   .. py:attribute:: metric
      :type: Optional


   .. py:attribute:: embeddings_provider
      :type: Optional
      :value: alias ``embeddingsProvider``


   .. py:attribute:: embeddings_model
      :type: Optional
      :value: alias ``embeddingsModel``


   .. py:attribute:: status
      :type: Optional

      e.g. pending, ready or error.


   .. py:attribute:: status_message
      :type: Optional
      :value: alias ``statusMessage``


   .. py:attribute:: index_name
      :type: Optional
      :value: alias ``indexName``


   .. py:attribute:: endpoint_url
      :type: Optional
      :value: alias ``endpointUrl``


   .. py:attribute:: vector_count
      :type: Optional
      :value: alias ``vectorCount``


   .. py:attribute:: document_count
      :type: Optional
      :value: alias ``documentCount``


   .. py:attribute:: snapshot_count
      :type: Optional
      :value: alias ``snapshotCount``


   .. py:attribute:: spec
      :type: Optional


   .. py:attribute:: deployed_at
      :type: Optional
      :value: alias ``deployedAt``



.. py:class:: VectorstoreStatus

   Bases: :class:`smarter.models.base.SmarterCamelModel`

   A vectorstore's state, checked now.

   .. py:attribute:: vectorstore
      :type: str


   .. py:attribute:: status
      :type: str


   .. py:attribute:: message
      :type: Optional


   .. py:attribute:: vector_count
      :type: Optional
      :value: alias ``vectorCount``


   .. py:attribute:: stats
      :type: dict



.. py:class:: VectorstoreDocument

   Bases: :class:`smarter.models.base.SmarterCamelModel`

   A document of a vectorstore: a file, a text or a url, split into chunks and embedded.

   .. py:attribute:: id
      :type: int


   .. py:attribute:: name
      :type: str


   .. py:attribute:: created_at
      :type: Optional
      :value: alias ``createdAt``


   .. py:attribute:: updated_at
      :type: Optional
      :value: alias ``updatedAt``


   .. py:attribute:: source
      :type: Optional

      upload, text or url.


   .. py:attribute:: content_type
      :type: Optional
      :value: alias ``contentType``


   .. py:attribute:: status
      :type: Optional

      e.g. pending, loaded, error or deleting.


   .. py:attribute:: chunk_count
      :type: Optional
      :value: alias ``chunkCount``


   .. py:attribute:: metadata
      :type: Optional



.. py:class:: VectorstoreDocuments

   Bases: :class:`smarter.models.base.SmarterCamelModel`

   A vectorstore's documents.

   .. py:attribute:: documents
      :type: list



.. py:class:: VectorstoreDocumentsAdded

   Bases: :class:`smarter.models.base.SmarterCamelModel`

   The result of adding documents.

   Documents are loaded asynchronously, and only once the vectorstore is deployed: see ``queued``.

   .. py:attribute:: documents
      :type: list


   .. py:attribute:: duplicates
      :type: list

      Documents that already existed.


   .. py:attribute:: queued
      :type: bool


   .. py:attribute:: message
      :type: Optional



.. py:class:: VectorstoreDocumentDeleted

   Bases: :class:`smarter.models.base.SmarterCamelModel`

   A document that is being deleted, with its chunks.

   .. py:attribute:: document
      :type: str


   .. py:attribute:: status
      :type: str



.. py:class:: VectorstoreSearchResult

   Bases: :class:`smarter.models.base.SmarterCamelModel`

   A chunk that matched a search.

   .. py:attribute:: id
      :type: Optional


   .. py:attribute:: text
      :type: str


   .. py:attribute:: metadata
      :type: Optional


   .. py:attribute:: score
      :type: Optional



.. py:class:: VectorstoreSearchResults

   Bases: :class:`smarter.models.base.SmarterCamelModel`

   The chunks that matched a search, best first.

   .. py:attribute:: vectorstore
      :type: str


   .. py:attribute:: results
      :type: list



.. py:class:: VectorstoreSnapshot

   Bases: :class:`smarter.models.base.SmarterCamelModel`

   A snapshot of a vectorstore's data.

   .. py:attribute:: id
      :type: int


   .. py:attribute:: name
      :type: Optional


   .. py:attribute:: created_at
      :type: Optional
      :value: alias ``createdAt``


   .. py:attribute:: status
      :type: Optional


   .. py:attribute:: scheduled
      :type: Optional


   .. py:attribute:: size_bytes
      :type: Optional
      :value: alias ``sizeBytes``



.. py:class:: VectorstoreSnapshots

   Bases: :class:`smarter.models.base.SmarterCamelModel`

   A vectorstore's snapshots.

   .. py:attribute:: snapshots
      :type: list



.. py:class:: VectorstoreRestored

   Bases: :class:`smarter.models.base.SmarterCamelModel`

   The result of restoring a snapshot.

   .. py:attribute:: vectorstore
      :type: str


   .. py:attribute:: restored
      :type: str


   .. py:attribute:: vector_count
      :type: Optional
      :value: alias ``vectorCount``



``smarter.models.llmhost``
--------------------------

.. py:module:: smarter.models.llmhost

Models of LLMHosts: open-weight models that Smarter serves on its own Kubernetes cluster.

.. py:class:: LLMHost

   Bases: :class:`smarter.models.base.SmarterResource`

   An LLMHost: a model, the inference engine that serves it, and the compute it runs on.

   .. py:attribute:: spec
      :type: Optional


   .. py:attribute:: model_source
      :type: Optional
      :value: alias ``modelSource``


   .. py:attribute:: model_repository
      :type: Optional
      :value: alias ``modelRepository``


   .. py:attribute:: model_revision
      :type: Optional
      :value: alias ``modelRevision``


   .. py:attribute:: model_task
      :type: Optional
      :value: alias ``modelTask``

      e.g. chat, completion or embedding.


   .. py:attribute:: inference_engine
      :type: Optional
      :value: alias ``inferenceEngine``

      e.g. vllm, tgi, tei, ollama or llama_cpp.


   .. py:attribute:: api_format
      :type: Optional
      :value: alias ``apiFormat``


   .. py:attribute:: compute
      :type: Optional

      The id of the LLMHostCompute that the LLMHost runs on.


   .. py:attribute:: gpu_count
      :type: Optional
      :value: alias ``gpuCount``


   .. py:attribute:: gpu_type
      :type: Optional
      :value: alias ``gpuType``


   .. py:attribute:: replicas
      :type: Optional


   .. py:attribute:: ready_replicas
      :type: Optional
      :value: alias ``readyReplicas``


   .. py:attribute:: status
      :type: Optional


   .. py:attribute:: status_message
      :type: Optional
      :value: alias ``statusMessage``


   .. py:attribute:: endpoint_url
      :type: Optional
      :value: alias ``endpointUrl``


   .. py:attribute:: public_url
      :type: Optional
      :value: alias ``publicUrl``


   .. py:attribute:: served_model_name
      :type: Optional
      :value: alias ``servedModelName``


   .. py:attribute:: is_active
      :type: Optional
      :value: alias ``isActive``


   .. py:attribute:: deployed_at
      :type: Optional
      :value: alias ``deployedAt``


   .. py:attribute:: cost_per_hour
      :type: Optional
      :value: alias ``costPerHour``



.. py:class:: LLMHostStatus

   Bases: :class:`smarter.models.base.SmarterCamelModel`

   An LLMHost's state, read from Kubernetes now.

   .. py:attribute:: llmhost
      :type: str


   .. py:attribute:: status
      :type: str


   .. py:attribute:: message
      :type: Optional


   .. py:attribute:: replicas
      :type: Optional


   .. py:attribute:: ready_replicas
      :type: Optional
      :value: alias ``readyReplicas``


   .. py:attribute:: healthy
      :type: Optional


   .. py:attribute:: endpoint
      :type: Optional


   .. py:attribute:: public_url
      :type: Optional
      :value: alias ``publicUrl``


   .. py:attribute:: pods
      :type: list


   .. py:attribute:: checked_at
      :type: Optional
      :value: alias ``checkedAt``



.. py:class:: LLMHostLogs

   Bases: :class:`smarter.models.base.SmarterCamelModel`

   The latest log lines of an LLMHost's pods.

   .. py:attribute:: llmhost
      :type: str


   .. py:attribute:: logs
      :type: JsonValue



.. py:class:: LLMHostPlan

   Bases: :class:`smarter.models.base.SmarterCamelModel`

   The Kubernetes resources that deploying an LLMHost would create, without creating them.

   .. py:attribute:: llmhost
      :type: str


   .. py:attribute:: resources
      :type: list



.. py:class:: LLMHostReport

   Bases: :class:`smarter.models.base.SmarterCamelModel`

   A report of every LLMHost that the user may read: counts, and estimated costs.

   .. py:attribute:: totals
      :type: dict


   .. py:attribute:: by_status
      :type: dict
      :value: alias ``byStatus``


   .. py:attribute:: by_engine
      :type: dict
      :value: alias ``byEngine``


   .. py:attribute:: llmhosts
      :type: list



.. py:class:: DiscoveredModel

   Bases: :class:`smarter.models.base.SmarterModel`

   A model found in a public catalog, e.g. Hugging Face, with the LLMHost manifest that would serve it.

   .. py:attribute:: catalog
      :type: Optional


   .. py:attribute:: source
      :type: Optional


   .. py:attribute:: repository
      :type: str


   .. py:attribute:: task
      :type: Optional


   .. py:attribute:: description
      :type: Optional


   .. py:attribute:: license
      :type: Optional


   .. py:attribute:: gated
      :type: Optional


   .. py:attribute:: downloads
      :type: Optional


   .. py:attribute:: likes
      :type: Optional


   .. py:attribute:: tags
      :type: list


   .. py:attribute:: manifest
      :type: Optional



.. py:class:: DiscoveredManifest

   Bases: :class:`smarter.models.base.SmarterModel`

   The response of ``discover/manifest/``: a drafted LLMHost manifest.

   .. py:attribute:: manifest
      :type: dict



.. py:class:: DiscoveredModels

   Bases: :class:`smarter.models.base.SmarterModel`

   The models that a catalog search found.

   .. py:attribute:: models
      :type: list



``smarter.models.misc``
-----------------------

.. py:module:: smarter.models.misc

Models of secrets, prompt history, proxies, orchestrators and vectorsearches.

.. py:class:: Secret

   Bases: :class:`smarter.models.base.SmarterResource`

   A secret's metadata.

   The api never returns a secret's value.

   .. py:attribute:: expires_at
      :type: Optional
      :value: alias ``expiresAt``


   .. py:attribute:: last_accessed
      :type: Optional
      :value: alias ``lastAccessed``



.. py:class:: Orchestrator

   Bases: :class:`smarter.models.base.SmarterResource`

   An orchestrator: a multi-agent workflow that composes LLMClients.


.. py:class:: Vectorsearch

   Bases: :class:`smarter.models.base.SmarterResource`

   A vectorsearch: a retrieval pipeline over one or more vectorstores.


.. py:class:: PromptSession

   Bases: :class:`smarter.models.base.SmarterModel`

   A chat session: one conversation with an LLMClient, by its session key.

   .. py:attribute:: id
      :type: int


   .. py:attribute:: created_at
      :type: Optional


   .. py:attribute:: updated_at
      :type: Optional


   .. py:attribute:: name
      :type: Optional


   .. py:attribute:: description
      :type: Optional


   .. py:attribute:: session_key
      :type: Optional


   .. py:attribute:: ip_address
      :type: Optional


   .. py:attribute:: user_agent
      :type: Optional


   .. py:attribute:: url
      :type: Optional


   .. py:attribute:: user_profile
      :type: Optional


   .. py:attribute:: llmclient
      :type: Optional



.. py:class:: PromptToolCall

   Bases: :class:`smarter.models.base.SmarterModel`

   A tool call that the LLM made in a chat session.

   .. py:attribute:: id
      :type: int


   .. py:attribute:: prompt
      :type: Union


   .. py:attribute:: created_at
      :type: Optional


   .. py:attribute:: updated_at
      :type: Optional


   .. py:attribute:: plugin
      :type: Optional

      The id of the plugin that the tool belongs to, if any.


   .. py:attribute:: function_name
      :type: Optional


   .. py:attribute:: function_args
      :type: Optional


   .. py:attribute:: request
      :type: JsonValue


   .. py:attribute:: response
      :type: JsonValue



.. py:class:: PromptPluginUsage

   Bases: :class:`smarter.models.base.SmarterModel`

   A use of a plugin in a chat session.

   .. py:attribute:: id
      :type: int


   .. py:attribute:: prompt
      :type: Union


   .. py:attribute:: created_at
      :type: Optional


   .. py:attribute:: updated_at
      :type: Optional


   .. py:attribute:: plugin
      :type: Optional


   .. py:attribute:: input_text
      :type: Optional



.. py:class:: Proxy

   Bases: :class:`smarter.models.base.SmarterCamelModel`

   A proxy: authenticated passthrough access to an LLM provider's own api.

   The platform holds the provider's api key. Callers use their Smarter api key instead, and may
   reach only the proxy's ``allowed_paths``.

   .. py:attribute:: name
      :type: str


   .. py:attribute:: description
      :type: Optional


   .. py:attribute:: provider
      :type: Optional


   .. py:attribute:: url
      :type: Optional

      The proxy's base url on the Smarter platform.


   .. py:attribute:: upstream_url
      :type: Optional
      :value: alias ``upstreamUrl``


   .. py:attribute:: allowed_paths
      :type: list
      :value: alias ``allowedPaths``


   .. py:attribute:: is_active
      :type: Optional
      :value: alias ``isActive``



.. py:class:: Proxies

   Bases: :class:`smarter.models.base.SmarterModel`

   The proxies that the user may call.

   .. py:attribute:: proxies
      :type: list



.. py:class:: Provider

   Bases: :class:`smarter.models.base.SmarterCamelModel`

   An LLM provider that the platform is configured for, e.g. openai.

   .. py:attribute:: name
      :type: str


   .. py:attribute:: description
      :type: Optional


   .. py:attribute:: base_url
      :type: Optional
      :value: alias ``baseUrl``


   .. py:attribute:: is_active
      :type: Optional
      :value: alias ``isActive``



.. py:class:: ProviderModel

   Bases: :class:`smarter.models.base.SmarterCamelModel`

   A model of an LLM provider.

   .. py:attribute:: name
      :type: str


   .. py:attribute:: description
      :type: Optional


   .. py:attribute:: max_tokens
      :type: Optional
      :value: alias ``maxTokens``


   .. py:attribute:: supports_streaming
      :type: Optional
      :value: alias ``supportsStreaming``


   .. py:attribute:: supports_tools
      :type: Optional
      :value: alias ``supportsTools``


   .. py:attribute:: metadata
      :type: Optional
