..
   Generated from the smarter-python SDK's docstrings by its scripts/generate_reference.py.
   Do not edit: change the docstring in https://github.com/smarter-sh/smarter-python, and regenerate.

API Contracts
=============

``smarter.models.chat``
-----------------------

.. py:module:: smarter.models.chat

Models of the Smarter Chat api contract, version 2: an LLMClient's configuration, its prompt api's request and response, and the prompt's progress events.

These mirror ``smarter.apps.prompt.contract.models`` in the Smarter platform, whose JSON Schema is
``chat-contract.schema.json``. The SDK always asks for version 2 of the contract (with the
``X-Smarter-Capabilities: chat-contract-v2`` request header), so the deprecated version 1 models are
not mirrored.

Two deliberate differences from the platform's models, both so that an SDK keeps working when the
platform is upgraded:

- every model allows extra fields, including the models of Django rows, whose platform models forbid
  them, and
- values that the platform may add to, such as a plugin's class or a progress event's type, are
  ``str`` rather than ``Literal``. Their known values are listed in the field descriptions.

The SDK's tests validate the platform's published example of every contract model against these
models. See ``scripts/sync-contracts.sh``.

.. py:data:: CHAT_CONTRACT_V2

   The version of the Smarter Chat api contract that the SDK reads.

.. py:data:: CHAT_CONTRACT_V2_CAPABILITY

   The ``X-Smarter-Capabilities`` value with which the SDK asks for version 2 of the contract.

.. py:data:: LLM_MESSAGE_ROLES

   The message roles that the LLM providers accept.

   Smarter's own roles, ``smarter`` and ``smarter_error``, are informational.

.. py:data:: PromptChatApiContentPart

   A part of a message whose content is a list of parts, by its ``type``.

.. py:class:: PromptChatApiTextPart

   Bases: :class:`smarter.models.base.SmarterModel`

   A text part of a message's content.

   .. py:attribute:: type
      :type: Literal


   .. py:attribute:: text
      :type: str



.. py:class:: PromptChatApiImageUrl

   Bases: :class:`smarter.models.base.SmarterModel`

   An image, by its url or as a data url.

   .. py:attribute:: url
      :type: str


   .. py:attribute:: detail
      :type: Optional



.. py:class:: PromptChatApiImagePart

   Bases: :class:`smarter.models.base.SmarterModel`

   An image part of a message's content.

   .. py:attribute:: type
      :type: Literal


   .. py:attribute:: image_url
      :type: PromptChatApiImageUrl



.. py:class:: PromptChatApiInputAudio

   Bases: :class:`smarter.models.base.SmarterModel`

   Audio, base64 encoded.

   .. py:attribute:: data
      :type: str


   .. py:attribute:: format
      :type: Literal



.. py:class:: PromptChatApiAudioPart

   Bases: :class:`smarter.models.base.SmarterModel`

   An audio part of a message's content.

   .. py:attribute:: type
      :type: Literal


   .. py:attribute:: input_audio
      :type: PromptChatApiInputAudio



.. py:class:: PromptChatApiFileRef

   Bases: :class:`smarter.models.base.SmarterModel`

   A file, base64 encoded, or by the provider's file id.

   .. py:attribute:: file_data
      :type: Optional


   .. py:attribute:: file_id
      :type: Optional


   .. py:attribute:: filename
      :type: Optional



.. py:class:: PromptChatApiFilePart

   Bases: :class:`smarter.models.base.SmarterModel`

   A file part of a message's content.

   .. py:attribute:: type
      :type: Literal


   .. py:attribute:: file
      :type: PromptChatApiFileRef



.. py:class:: PromptChatApiRefusalPart

   Bases: :class:`smarter.models.base.SmarterModel`

   The LLM's refusal, as a part of a message's content.

   .. py:attribute:: type
      :type: Literal


   .. py:attribute:: refusal
      :type: str



.. py:class:: PromptChatApiFunctionCall

   Bases: :class:`smarter.models.base.SmarterModel`

   The function that a tool call calls.

   .. py:attribute:: name
      :type: str


   .. py:attribute:: arguments
      :type: str

      The function's arguments, as a JSON string.



.. py:class:: PromptChatApiToolCall

   Bases: :class:`smarter.models.base.SmarterModel`

   A tool call of an assistant message.

   .. py:attribute:: id
      :type: str


   .. py:attribute:: type
      :type: str


   .. py:attribute:: function
      :type: PromptChatApiFunctionCall



.. py:class:: PromptChatApiMessage

   Bases: :class:`smarter.models.base.SmarterModel`

   A message of a chat thread, in the format of the OpenAI api.

   Smarter adds its own roles: ``smarter`` for informational messages (e.g. the prompt's
   configuration, the tools presented to the LLM, and its token charges), and ``smarter_error``.
   These are saved in the session's history, and are never sent to the LLM.

   .. py:attribute:: role
      :type: str

      system, assistant, user, tool, smarter or smarter_error.


   .. py:attribute:: content
      :type: Union

      The message's text, or a list of content parts.


   .. py:attribute:: tool_calls
      :type: Optional

      An assistant message's tool calls.


   .. py:attribute:: tool_call_id
      :type: Optional

      The tool call that a tool message answers.


   .. py:attribute:: name
      :type: Optional

      The name of a tool message's function.


   .. py:property:: text

      The message's text: its content, or the text of its text parts, joined by blank lines.



.. py:class:: PromptChatApiJournalMetadata

   Bases: :class:`smarter.models.base.SmarterModel`

   The ``metadata`` of a chat response.

   .. py:attribute:: command
      :type: Optional

      The journal's command, e.g. prompt.


   .. py:attribute:: thing
      :type: Optional

      The journal's thing, e.g. LLMClient.


   .. py:attribute:: key
      :type: Optional



.. py:class:: PromptChatApiErrorBody

   Bases: :class:`smarter.models.base.SmarterModel`

   The ``error`` of a chat error response.

   .. py:attribute:: errorClass
      :type: str

      The name of the error's class, e.g. NotFound or LLMProviderError.


   .. py:attribute:: description
      :type: str

      A human-readable description.


   .. py:attribute:: status
      :type: int

      The http status.



.. py:class:: PromptChatApiErrorResponse

   Bases: :class:`smarter.models.base.SmarterModel`

   A chat error response.

   .. py:attribute:: error
      :type: PromptChatApiErrorBody


   .. py:attribute:: api
      :type: Optional


   .. py:attribute:: metadata
      :type: Optional



.. py:class:: PromptChatApiEnvelope

   Bases: :class:`smarter.models.base.SmarterModel`

   The fields that every chat response adds beside ``data``.

   .. py:attribute:: api
      :type: str

      The api version, e.g. "smarter.sh/v1".


   .. py:attribute:: metadata
      :type: PromptChatApiJournalMetadata



.. py:class:: PromptChatApiStyleSection

   Bases: :class:`smarter.models.base.SmarterModel`

   The colors of one section of the chat ui.

   .. py:attribute:: background_color
      :type: Optional


   .. py:attribute:: color
      :type: Optional


   .. py:attribute:: border_color
      :type: Optional


   .. py:attribute:: info_color
      :type: Optional


   .. py:attribute:: link_color
      :type: Optional


   .. py:attribute:: editor_background_color
      :type: Optional


   .. py:attribute:: placeholder_color
      :type: Optional



.. py:class:: PromptChatApiStyles

   Bases: :class:`smarter.models.base.SmarterModel`

   The LLMClient's chat ui styles.

   .. py:attribute:: app_logo_url
      :type: Optional


   .. py:attribute:: app_background_image_url
      :type: Optional


   .. py:attribute:: app_background_image_size
      :type: Optional


   .. py:attribute:: assistant_avatar_url
      :type: Optional


   .. py:attribute:: user_avatar_url
      :type: Optional


   .. py:attribute:: font_family
      :type: Optional


   .. py:attribute:: google_font
      :type: Optional


   .. py:attribute:: font_size
      :type: Optional


   .. py:attribute:: border_radius
      :type: Optional


   .. py:attribute:: main_container
      :type: Optional


   .. py:attribute:: conversation_header
      :type: Optional


   .. py:attribute:: message_list
      :type: Optional


   .. py:attribute:: incoming_message
      :type: Optional


   .. py:attribute:: outgoing_message
      :type: Optional


   .. py:attribute:: message_input
      :type: Optional


   .. py:attribute:: buttons
      :type: Optional


   .. py:attribute:: typing_indicator
      :type: Optional



.. py:class:: PromptChatApiLLMClient

   Bases: :class:`smarter.models.base.SmarterModel`

   The LLMClient, as its configuration describes it.

   .. py:attribute:: id
      :type: int


   .. py:attribute:: name
      :type: str


   .. py:attribute:: url_llmclient
      :type: Optional

      The url of the LLMClient's prompt api.


   .. py:attribute:: version
      :type: Optional


   .. py:attribute:: deployed
      :type: Optional


   .. py:attribute:: provider
      :type: Optional


   .. py:attribute:: default_model
      :type: Optional


   .. py:attribute:: default_system_role
      :type: Optional

      The system prompt of a new chat session.


   .. py:attribute:: app_name
      :type: Optional


   .. py:attribute:: app_assistant
      :type: Optional


   .. py:attribute:: app_welcome_message
      :type: Optional


   .. py:attribute:: app_example_prompts
      :type: Optional


   .. py:attribute:: app_placeholder
      :type: Optional


   .. py:attribute:: app_info_url
      :type: Optional


   .. py:attribute:: app_file_attachment
      :type: Optional


   .. py:attribute:: styles
      :type: Optional


   .. py:attribute:: total_tools
      :type: Optional

      The number of the LLMClient's extensions, plugins and MCPClients.



.. py:class:: PromptChatApiOrmModel

   Bases: :class:`smarter.models.base.SmarterModel`

   The fields of a Django row that the contract returns.

   .. py:attribute:: id
      :type: int


   .. py:attribute:: created_at
      :type: Optional


   .. py:attribute:: updated_at
      :type: Optional



.. py:class:: PromptChatApiPluginMeta

   Bases: :class:`smarter.models.chat.PromptChatApiOrmModel`

   A plugin's metadata.

   .. py:attribute:: name
      :type: str


   .. py:attribute:: description
      :type: Optional


   .. py:attribute:: version
      :type: Optional


   .. py:attribute:: tags
      :type: list


   .. py:attribute:: annotations
      :type: Union


   .. py:attribute:: plugin_class
      :type: str

      api, skill, sql, static, websearch or imagesearch.



.. py:class:: PromptChatApiLLMClientPlugin

   Bases: :class:`smarter.models.chat.PromptChatApiOrmModel`

   A plugin of the LLMClient.

   .. py:attribute:: llmclient
      :type: int


   .. py:attribute:: plugin_meta
      :type: PromptChatApiPluginMeta



.. py:class:: PromptChatApiLLMClientExtension

   Bases: :class:`smarter.models.chat.PromptChatApiOrmModel`

   An extension of the LLMClient, whose tools it offers the LLM.

   .. py:attribute:: llmclient
      :type: int


   .. py:attribute:: extension
      :type: int

      The Extension's id.


   .. py:attribute:: name
      :type: str

      The Extension's slug, e.g. weather.


   .. py:attribute:: version
      :type: Optional

      The Extension's installed version, e.g. 1.0.0.


   .. py:attribute:: enabled
      :type: bool

      Whether the Extension is enabled, so that its tools are offered.



.. py:class:: PromptChatApiPromptRequest

   Bases: :class:`smarter.models.base.SmarterModel`

   The prompt api's request body.

   .. py:attribute:: session_key
      :type: Optional


   .. py:attribute:: messages
      :type: list



.. py:class:: PromptChatApiLLMClientRequest

   Bases: :class:`smarter.models.chat.PromptChatApiOrmModel`

   A request that Smarter sent to the LLM.

   .. py:attribute:: llmclient
      :type: int


   .. py:attribute:: request
      :type: Optional


   .. py:attribute:: session_key
      :type: Optional


   .. py:attribute:: is_aggregation
      :type: Optional



.. py:class:: PromptChatApiPromptToolCall

   Bases: :class:`smarter.models.chat.PromptChatApiOrmModel`

   A tool call of the chat session.

   .. py:attribute:: prompt
      :type: int


   .. py:attribute:: plugin
      :type: Optional


   .. py:attribute:: function_name
      :type: Optional


   .. py:attribute:: function_args
      :type: Optional


   .. py:attribute:: request
      :type: JsonValue


   .. py:attribute:: response
      :type: JsonValue



.. py:class:: PromptChatApiPromptPluginUsage

   Bases: :class:`smarter.models.chat.PromptChatApiOrmModel`

   A use of a plugin in the chat session.

   .. py:attribute:: prompt
      :type: int


   .. py:attribute:: plugin
      :type: int


   .. py:attribute:: input_text
      :type: Optional



.. py:class:: PromptChatApiPluginSelection

   Bases: :class:`smarter.models.chat.PromptChatApiOrmModel`

   A plugin selector's decision in the chat session.

   .. py:attribute:: plugin_selector
      :type: int


   .. py:attribute:: search_term
      :type: Optional


   .. py:attribute:: messages
      :type: Optional


   .. py:attribute:: session_key
      :type: Optional



.. py:class:: PromptChatApiHistory

   Bases: :class:`smarter.models.base.SmarterModel`

   The chat session's history.

   ``prompt_tool_call_history`` is returned only in the complete configuration, with ``verbose=True``.

   .. py:attribute:: chat_history
      :type: list

      The session's messages, which restore the chat thread.


   .. py:attribute:: prompt_tool_call_history
      :type: Optional


   .. py:attribute:: prompt_plugin_usage_history
      :type: Optional


   .. py:attribute:: plugin_selector_history
      :type: Optional


   .. py:attribute:: llmclient_request_history
      :type: Optional



.. py:class:: PromptChatApiMetaData

   Bases: :class:`smarter.models.base.SmarterModel`

   The LLMClient's state.

   The complete configuration, from :meth:`~smarter.resources.llmclients.LLMClients.config` with
   ``verbose=True``, adds the platform's other details of the LLMClient, which this model accepts as extra fields.

   .. py:attribute:: ready
      :type: Optional


   .. py:attribute:: is_valid
      :type: Optional


   .. py:attribute:: is_deployed
      :type: Optional


   .. py:attribute:: is_authentication_required
      :type: Optional

      True if the LLMClient requires a Smarter api key, or a logged-in user.


   .. py:attribute:: is_custom_domain
      :type: Optional

      True if the request's host is a custom domain.



.. py:class:: PromptChatApiListMetaData

   Bases: :class:`smarter.models.base.SmarterModel`

   The counts of a list of the LLMClient's plugins or extensions.

   .. py:attribute:: total_plugins
      :type: Optional


   .. py:attribute:: plugins_returned
      :type: Optional


   .. py:attribute:: total_extensions
      :type: Optional


   .. py:attribute:: extensions_returned
      :type: Optional



.. py:class:: PromptChatApiPluginList

   Bases: :class:`smarter.models.base.SmarterModel`

   The LLMClient's plugins.

   The list itself is returned only in the complete configuration, with ``verbose=True``. Otherwise
   ``plugins`` is empty, and ``meta_data`` has the counts.

   .. py:attribute:: meta_data
      :type: PromptChatApiListMetaData


   .. py:attribute:: plugins
      :type: list



.. py:class:: PromptChatApiExtensionList

   Bases: :class:`smarter.models.base.SmarterModel`

   The LLMClient's extensions.

   The list itself is returned only in the complete configuration, with ``verbose=True``. Otherwise
   ``extensions`` is empty, and ``meta_data`` has the counts.

   .. py:attribute:: meta_data
      :type: PromptChatApiListMetaData


   .. py:attribute:: extensions
      :type: list



.. py:class:: PromptChatApiConfig

   Bases: :class:`smarter.models.base.SmarterModel`

   An LLMClient's chat configuration: the LLMClient, the chat session's key and history, and its plugins and extensions.

   A new session's configuration has an empty history. Pass its ``session_key`` to the prompt api
   to continue the session.

   .. py:attribute:: contract
      :type: int


   .. py:attribute:: session_key
      :type: str

      The chat session's key.


   .. py:attribute:: sandbox_mode
      :type: bool

      True for a workbench url.


   .. py:attribute:: debug_mode
      :type: bool

      The platform's ENABLE_REACTAPP_DEBUG_MODE waffle switch.


   .. py:attribute:: meta_data
      :type: PromptChatApiMetaData


   .. py:attribute:: llmclient
      :type: PromptChatApiLLMClient


   .. py:attribute:: history
      :type: PromptChatApiHistory


   .. py:attribute:: plugins
      :type: PromptChatApiPluginList


   .. py:attribute:: extensions
      :type: Optional



.. py:class:: PromptChatApiConfigRequest

   Bases: :class:`smarter.models.base.SmarterModel`

   The configuration api's request body.

   .. py:attribute:: session_key
      :type: Optional

      The chat session's key, or None for a new session.



.. py:class:: PromptChatApiConfigResponse

   Bases: :class:`smarter.models.chat.PromptChatApiEnvelope`

   The configuration api's response.

   .. py:attribute:: data
      :type: PromptChatApiConfig



.. py:class:: PromptChatApiChoice

   Bases: :class:`smarter.models.base.SmarterModel`

   A choice of a chat completion.

   .. py:attribute:: index
      :type: int


   .. py:attribute:: finish_reason
      :type: Optional

      e.g. stop, length or tool_calls.


   .. py:attribute:: message
      :type: Optional



.. py:class:: PromptChatApiTokenDetails

   Bases: :class:`smarter.models.base.SmarterModel`

   The breakdown of a completion's tokens.

   .. py:attribute:: reasoning_tokens
      :type: Optional


   .. py:attribute:: cached_tokens
      :type: Optional


   .. py:attribute:: audio_tokens
      :type: Optional



.. py:class:: PromptChatApiUsage

   Bases: :class:`smarter.models.base.SmarterModel`

   A chat completion's token usage.

   .. py:attribute:: prompt_tokens
      :type: Optional


   .. py:attribute:: completion_tokens
      :type: Optional


   .. py:attribute:: total_tokens
      :type: Optional


   .. py:attribute:: prompt_tokens_details
      :type: Optional


   .. py:attribute:: completion_tokens_details
      :type: Optional



.. py:class:: PromptChatApiCompletion

   Bases: :class:`smarter.models.base.SmarterModel`

   The LLM's chat completion, in the format of the OpenAI api.

   .. py:attribute:: id
      :type: Optional


   .. py:attribute:: object
      :type: Optional


   .. py:attribute:: created
      :type: Optional


   .. py:attribute:: model
      :type: Optional


   .. py:attribute:: choices
      :type: list


   .. py:attribute:: usage
      :type: Optional


   .. py:attribute:: system_fingerprint
      :type: Optional


   .. py:attribute:: service_tier
      :type: Optional



.. py:class:: PromptChatApiPromptResult

   Bases: :class:`smarter.models.base.SmarterModel`

   The result of a prompt.

   .. py:attribute:: contract
      :type: int


   .. py:attribute:: status
      :type: int

      The prompt's http status: 200, or the LLM provider's error status.


   .. py:attribute:: messages
      :type: list

      The messages that the prompt added to the chat thread, in order.


   .. py:attribute:: completion
      :type: Optional

      The LLM's chat completion.


   .. py:attribute:: plugins
      :type: list

      The plugins that Smarter selected.


   .. py:attribute:: tools
      :type: list

      The functions that the LLM could call.


   .. py:property:: assistant_messages

      The assistant messages that the prompt added, which are the LLM's replies and tool calls.


   .. py:property:: text

      The text of the LLM's final reply: the last assistant message that has content, or an empty string.



.. py:class:: PromptChatApiPromptResponse

   Bases: :class:`smarter.models.chat.PromptChatApiEnvelope`

   The prompt api's response.

   A failed prompt has ``error`` too, and its ``data.messages`` include a ``smarter_error`` message.

   .. py:attribute:: data
      :type: PromptChatApiPromptResult


   .. py:attribute:: error
      :type: Optional


   .. py:property:: text

      The text of the LLM's final reply.

      See :attr:`PromptChatApiPromptResult.text`.



.. py:class:: PromptChatApiProgressEvent

   Bases: :class:`smarter.models.base.SmarterModel`

   The data of a ``progress`` event: a step of a running prompt.

   Events may carry more fields, depending on their type, e.g. ``tool`` and ``arguments``.

   .. py:attribute:: type
      :type: str

      llm_request, tool_requested, tool_responded, plugin_called, mcp_tool_called, mcp_tool_responded or mcp_tool_failed.


   .. py:attribute:: message
      :type: str

      A short sentence, which a chat ui can display as is.



.. py:class:: PromptChatApiProgressResult

   Bases: :class:`smarter.models.base.SmarterModel`

   The data of the final ``result`` event.

   .. py:attribute:: status
      :type: int

      The prompt's http status.


   .. py:attribute:: response
      :type: Union

      Exactly the JSON of a non-streaming response.



``smarter.models.journal``
--------------------------

.. py:module:: smarter.models.journal

Models of the Smarter Journal api contract: the envelope of every journaled response, its error body, and a journal entry.

The Smarter platform journals its api responses. Each one carries ``api`` (the api version, e.g.
``smarter.sh/v1``) and ``metadata`` (the command and the resource kind, which the platform calls
its "thing") beside its own ``data``, ``message`` or ``error``.

These models mirror ``smarter.lib.journal.contract.models`` in the Smarter platform, whose JSON
Schema is ``journal-contract.schema.json``. The SDK's tests validate the platform's schema against
them. See ``scripts/sync-contracts.sh``.

.. py:class:: SAMJournalApiMetadata

   Bases: :class:`smarter.models.base.SmarterModel`

   The ``metadata`` of a journaled response: its command and thing, and the key of its journal entry.

   .. py:attribute:: command
      :type: str

      The journal's command, e.g. apply.


   .. py:attribute:: thing
      :type: str

      The journal's thing, e.g. Guardrail. The string 'None' when there is none.


   .. py:attribute:: key
      :type: Optional

      The key of the response's journal entry, when the journal is enabled.



.. py:class:: SAMJournalApiErrorBody

   Bases: :class:`smarter.models.base.SmarterModel`

   The ``error`` of a journaled error response.

   Every error of the cli api has this shape.

   .. py:attribute:: errorClass
      :type: str

      The name of the exception's class, e.g. SAMBrokerErrorNotFound.


   .. py:attribute:: stacktrace
      :type: Optional

      The server's stack trace, when the platform includes it.


   .. py:attribute:: description
      :type: Optional

      A human-readable description of the error.


   .. py:attribute:: status
      :type: int

      The http status.


   .. py:attribute:: args
      :type: JsonValue

      The exception's arguments, or the request's url.


   .. py:attribute:: cause
      :type: Optional

      The exception's cause.


   .. py:attribute:: context
      :type: Optional

      The exception's context, or the response's thing and command.


   .. py:attribute:: thing
      :type: Optional

      The journal's thing, e.g. Guardrail.


   .. py:attribute:: command
      :type: Optional

      The journal's command, e.g. describe.



.. py:class:: SAMJournalApiEnvelope

   Bases: :class:`smarter.models.base.SmarterModel`

   The fields that every journaled response adds beside its own data.

   .. py:attribute:: api
      :type: str

      The api version, e.g. "smarter.sh/v1".


   .. py:attribute:: metadata
      :type: Optional



.. py:class:: SAMJournalApiErrorResponse

   Bases: :class:`smarter.models.journal.SAMJournalApiEnvelope`

   The body of a journaled error response.

   .. py:attribute:: error
      :type: SAMJournalApiErrorBody



.. py:class:: SmarterJournaledResponse

   Bases: :class:`smarter.models.journal.SAMJournalApiEnvelope`, :class:`typing.Generic`

   A successful journaled response: the envelope, the response's ``data``, and an optional ``message``.

   ``data`` is typed by the endpoint, e.g. ``SmarterJournaledResponse[WhoAmI]``.

   .. py:attribute:: data
      :type: Optional


   .. py:attribute:: message
      :type: Optional

      A human-readable message, e.g. 'LLMClient calculator applied'.



.. py:class:: SmarterJournalMessage

   Bases: :class:`smarter.models.journal.SAMJournalApiEnvelope`

   A journaled response that carries only a ``message``, e.g. the response of delete or deploy.

   .. py:attribute:: message
      :type: Optional



.. py:class:: JournalEntry

   Bases: :class:`smarter.models.base.SmarterCamelModel`

   A Smarter Journal entry, as ``/api/v1/journal/`` returns it.

   The list returns entries without ``request`` and ``response``. Retrieving one entry by its key
   includes them. Only superusers may read the journal, because the request documents hold the
   callers' credentials.

   .. py:attribute:: key
      :type: str


   .. py:attribute:: created_at
      :type: Optional
      :value: alias ``createdAt``


   .. py:attribute:: user
      :type: Optional

      The username of the caller, or None for an anonymous request.


   .. py:attribute:: thing
      :type: str


   .. py:attribute:: command
      :type: str


   .. py:attribute:: status_code
      :type: int
      :value: alias ``statusCode``


   .. py:attribute:: request
      :type: JsonValue


   .. py:attribute:: response
      :type: JsonValue



.. py:class:: JournalPagination

   Bases: :class:`smarter.models.base.SmarterCamelModel`

   The description of one page of the journal's entries.

   .. py:attribute:: page
      :type: int


   .. py:attribute:: page_size
      :type: int
      :value: alias ``pageSize``


   .. py:attribute:: num_pages
      :type: int
      :value: alias ``numPages``


   .. py:attribute:: count
      :type: int


   .. py:attribute:: search
      :type: str


   .. py:attribute:: ordering
      :type: str


   .. py:attribute:: sort_fields
      :type: list
      :value: alias ``sortFields``


   .. py:attribute:: filter
      :type: str

      The named filter that narrows the list, e.g. pending, or an empty string for none.


   .. py:attribute:: filters
      :type: list

      The named filters that the list offers.



.. py:class:: JournalPage

   Bases: :class:`smarter.models.base.SmarterModel`

   One page of the journal's entries.

   .. py:attribute:: objects
      :type: list


   .. py:attribute:: pagination
      :type: JournalPagination



``smarter.models.react``
------------------------

.. py:module:: smarter.models.react

Pydantic models of the Smarter platform's Django-React integration: a React app's Vite manifest, and the assets that a template includes.

The platform's web console pages are React apps that Django hosts.
``SmarterReactTemplateTagManager`` (in ``smarter.lib.django.templatetags``) reads each app's
Vite-generated ``manifest.json``, and each ``<app>_react_assets`` template tag returns the files
that a template includes. These models are a copy of the platform's
``smarter.lib.django.templatetags.smarter_react_contract``, which is pure Pydantic, so that tools
that build or check React apps for a Smarter platform can use them without the platform.

- :class:`ViteManifest` is a Vite-generated React ``manifest.json``: a map of
  :class:`ViteManifestChunk` keyed by source path. The manager validates the
  file against it when it loads it, and collects an entry point's assets with
  its methods.
- :class:`ReactAppAssets` is what every ``<app>_react_assets`` template tag
  returns: the ordered JS and CSS files that a Django template includes for a
  React app.

The manifest is a third-party shape. :class:`ViteManifestChunk` declares the
fields that Vite documents, and allows extra fields, which newer Vite (or
Rolldown) versions add, so that a Vite upgrade doesn't break page rendering.
Smarter's own addition, the ``_custom`` entry that every package's
``vite.config.ts`` writes after the build, is a :class:`ReactAppBuildInfo`.

.. py:data:: ReactAssetType

   The kinds of asset that a React app's entry point loads.

.. py:data:: BUILD_INFO_KEY

   The key of the build information that each React package's ``vite.config.ts`` adds to its manifest.json.

.. py:class:: ViteManifestChunk

   Bases: :class:`pydantic.main.BaseModel`

   One entry of a Vite-generated ``manifest.json``: a chunk, or a static asset.

   See https://vite.dev/guide/backend-integration. Extra fields are allowed,
   because Vite and Rolldown add their own.

   Example::

       "index.html": {
           "file": "assets/index.js",
           "name": "index",
           "src": "index.html",
           "isEntry": true,
           "imports": ["_rolldown-runtime.js", "_xterm.js"],
           "css": ["assets/index-DvLY75bJ.css"]
       }

   .. py:attribute:: file
      :type: str

      The output file of this chunk, relative to the app's static directory.


   .. py:attribute:: name
      :type: Optional

      The chunk's name.


   .. py:attribute:: names
      :type: list

      The names of a static asset.


   .. py:attribute:: src
      :type: Optional

      The chunk's source path.


   .. py:attribute:: is_entry
      :type: bool
      :value: alias ``isEntry``

      Whether this chunk is an entry point.


   .. py:attribute:: is_dynamic_entry
      :type: bool
      :value: alias ``isDynamicEntry``

      Whether this chunk is a dynamic entry point.


   .. py:attribute:: imports
      :type: list

      The manifest keys of statically imported chunks.


   .. py:attribute:: dynamic_imports
      :type: list
      :value: alias ``dynamicImports``

      The manifest keys of dynamically imported chunks.


   .. py:attribute:: css
      :type: list

      The CSS files that this chunk loads.


   .. py:attribute:: assets
      :type: list

      The other static files that this chunk references.



.. py:class:: ReactAppBuildInfo

   Bases: :class:`pydantic.main.BaseModel`

   The build information that each React package's ``vite.config.ts`` adds to its manifest.json, as ``_custom``.

   Example::

       "_custom": {
           "buildTime": "2026-10-12T01:09:47.988Z",
           "version": "0.3.0",
           "buildEnv": "production"
       }

   .. py:attribute:: build_time
      :type: datetime
      :value: alias ``buildTime``

      When the app was built.


   .. py:attribute:: version
      :type: str

      The version of the app's npm package.


   .. py:attribute:: build_env
      :type: str
      :value: alias ``buildEnv``

      The build's NODE_ENV, e.g. production.



.. py:class:: ViteManifest

   Bases: :class:`pydantic.main.BaseModel`

   A React app's Vite-generated ``manifest.json``: its chunks, keyed by source path, and Smarter's build information.

   In the file, the build information is the ``_custom`` entry, beside the
   chunks. Validating a manifest.json splits it out into :attr:`build_info`,
   and dumping the model puts it back, so ``model_dump(by_alias=True)`` has the
   file's shape.

   See https://vite.dev/guide/backend-integration.

   .. py:attribute:: chunks
      :type: dict

      The manifest's chunks, keyed by source path.


   .. py:attribute:: build_info
      :type: Optional

      The \`\`_custom\`\` build information, if the package's vite.config.ts adds it.


   .. py:method:: split_build_info(data: object) -> object
      :classmethod:

      Split a manifest.json's ``_custom`` entry from its chunks.

      Input that already has ``chunks``, e.g. keyword arguments, is left as is.

      :param data: The manifest.json's content.
      :returns: The model's fields.
      :rtype: object


   .. py:method:: join_build_info(handler: pydantic_core.core_schema.SerializerFunctionWrapHandler) -> dict[str, typing.Any]

      Dump the manifest in the shape of manifest.json, with the build information as its ``_custom`` entry.

      :param handler: Pydantic's default serializer.
      :returns: The chunks, keyed by source path, and ``_custom``.
      :rtype: SmarterDictType


   .. py:method:: entry_key() -> Optional[str]

      Find the key of the manifest's entry point, the first chunk with ``"isEntry": true``.

      :returns: The entry point's key, or None if the manifest has no entry point.
      :rtype: Optional[str]


   .. py:method:: collect_assets(key: str, asset_type: Literal['js', 'css'], seen: Optional[set[str]] = None) -> list[str]

      Recursively collect the JS or CSS files of a chunk and of its static imports.

      A chunk's own files come first, followed by those of each of its
      ``imports``, depth first, in the order they are listed. Each chunk is
      visited once, so circular imports terminate.

      :param key: The manifest key of the chunk to collect assets for.
      :param asset_type: ``"js"`` for the chunks' ``file``, ``"css"`` for their ``css`` files.
      :param seen: The keys already visited, used by the recursion.
      :returns: The asset file paths, relative to the app's static directory.
      :rtype: list[str]



.. py:class:: ReactAppAssets

   Bases: :class:`pydantic.main.BaseModel`

   The ordered JS and CSS files of a React app's entry point, which a Django template includes.

   Every ``<app>_react_assets`` template tag returns one. Templates read its
   attributes, e.g. ``{% for css_file in assets.css %}``.

   Example::

       {
           "js": [
               "assets/index-CZK_Bxxh.js",
               "assets/rolldown-runtime-B3igc2qu.js",
               "assets/xterm-D5XSfLrr.js"
           ],
           "css": [
               "assets/index-58MXwt-L.css",
               "assets/xterm-kHJ-D0s7.css"
           ]
       }

   .. py:attribute:: js
      :type: list

      The JS files, the entry point's first.


   .. py:attribute:: css
      :type: list

      The CSS files, the entry point's first.
