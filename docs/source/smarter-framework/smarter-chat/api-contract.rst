The Chat API Contract
=====================

This page is the contract between Smarter Chat and the Smarter backend: every endpoint the chat
calls, and every header, field, event and error that it depends on. It is written for backend
developers. If you change anything in ``smarter.apps`` that ends up in one of these responses, for
example an LLMClient field, a prompt's messages, a provider's error handling, a progress signal, or
CORS or authentication, read this page first.


Where the Contract Lives
------------------------

The contract is code, in :mod:`smarter.apps.prompt.contract`:

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Module
     - Role
   * - :mod:`~smarter.apps.prompt.contract.models`
     - Pydantic models of every request, response and event, in both versions of the contract. The
       single source of truth.
   * - :mod:`~smarter.apps.prompt.contract.builders`
     - Contract negotiation, the error envelope, and the prompt's version 2 result.
   * - :mod:`~smarter.apps.prompt.contract.schema`
     - The JSON Schema of the models, which ``manage.py export_chat_contract_schema`` writes to
       ``chat-contract.schema.json``, beside them.
   * - :mod:`~smarter.apps.prompt.contract.example`
     - An example JSON of each model, generated from the schema, which ``manage.py
       export_chat_contract_example`` writes to ``chat-contract.example.json``, beside them.

The models are used, not just documented:

- ``PromptConfigView.chat_config()`` builds a :class:`~smarter.apps.prompt.contract.models.PromptChatApiConfig`,
  and every configuration response is derived from it, by its methods.
- The prompt api builds its version 2 result as a :class:`~smarter.apps.prompt.contract.models.PromptChatApiPromptResult`.
- Tests validate the views' real responses, in both versions, against the models, and fail if
  ``chat-contract.schema.json`` or ``chat-contract.example.json`` is out of date.
- Smarter Chat keeps a copy of the schema, in ``contract/chat-contract.schema.json``, generates its
  TypeScript types from it (``src/contract.gen.ts``), and validates its test fixtures against it
  (``src/contract.test.ts``), so its tests can't pass against responses that the backend never sends.

After changing a model, run ``make chat-contract``, which regenerates the schema and the examples in
the ``smarter-app`` container, copies it into Smarter Chat, and regenerates the TypeScript types. Commit
both repositories.

.. literalinclude:: ../../../../smarter/smarter/apps/prompt/contract/chat-contract.schema.json
   :language: json
   :caption: chat-contract.schema.json
   :lines: 1-12


Versions
--------

The contract is versioned, because Smarter Chat is published to npm, and pages run whichever version
they installed against whichever Smarter platform they call.

.. list-table::
   :header-rows: 1
   :widths: 15 85

   * - Version
     - Shape
   * - 1
     - Deprecated. The original. The configuration's LLMClient is ``chatbot``, with ``url_chatbot``,
       because every key that contains ``llmclient`` is renamed to ``chatbot``, at every depth (and
       ``account_number`` to ``accountNumber``). A prompt's result is an AWS Lambda style response,
       whose ``body`` is a JSON *string*.
   * - 2
     - The default. Keys are not renamed: the LLMClient is ``llmclient``, with ``url_llmclient``. A
       prompt's result is plain JSON: its messages, its completion, and its error. Both responses
       have ``contract: 2``.

:func:`~smarter.apps.prompt.contract.builders.requested_contract` decides, from the
``X-Smarter-Capabilities`` request header, a comma-separated list of capabilities:

- ``chat-contract-v2``: version 2. Smarter Chat sends it.
- ``chat-contract-v1``: version 1.
- neither, from Smarter Chat (``X-Smarter-Client: @smarter.sh/ui-chat``): version 1, because the
  versions of Smarter Chat that send no capability, up to 0.7, read version 1 only. The pages that
  installed them keep working.
- neither, from any other client: version 2.

The header is in ``CORS_ALLOW_HEADERS`` on every Smarter platform, so a new client can send it to an
older platform, which ignores it and answers with version 1; Smarter Chat reads both.

Version 1 is marked with ``typing_extensions.deprecated``: its models, and
:meth:`PromptChatApiConfig.to_v1() <smarter.apps.prompt.contract.models.PromptChatApiConfig.to_v1>`,
raise ``DeprecationWarning`` when they are used, and type checkers flag their callers.
``CHAT_CONTRACT_V1``, a constant, can't be marked, so its docstring says so.

The ``smarter`` cli calls both views internally: the configuration with ``as_view(legacy_keys=False,
include_diagnostics=True)``, which is version 2, and the prompt with
``as_view(include_diagnostics=True, forced_contract=CHAT_CONTRACT_V1)``, because the cli's clients
parse version 1. Both receive the diagnostics that browsers never receive.


Overview
--------

.. code-block:: text

  Browser (Smarter Chat)                         Smarter

  on load, on "new chat", and after every prompt:
    POST <apiUrl>config/?session_key=<key>  ───▶  PromptConfigView
                                            ◀───  the LLMClient's configuration, the session's
                                                  key, and the session's history

  on each message:
    POST <llmclient.url_llmclient>?session_key=<key>  ───▶  DefaultLLMClientApiView
         {"session_key", "messages": [...]}                 (LLMClientApiBaseViewSet)
                                            ◀───  the new messages, as JSON, or as Server-Sent
                                                  Events: progress events, then the result

  while the Console's Server Logs tab exists:
    GET <logStreamUrl>[?level=DEBUG]        ───▶  stream_user_logs
                                            ◀───  Server-Sent Events: a "bulk" history, then
                                                  one event per log record

  once the Console's Manifest tab is opened, in an iframe:
    GET <manifestEditorUrl>                 ───▶  LLMClientManifestEditorView
                                            ◀───  the manifest editor, which saves with the cli
                                                  api, then posts "smarter:manifest-saved"

The configuration tells the chat where to send prompts, so ``apiUrl`` is the only url a page has to
know.


Endpoints
---------

.. list-table::
   :header-rows: 1
   :widths: 18 42 40

   * -
     - Url
     - Served by
   * - Configuration, workbench
     - ``https://<platform>/workbench/llm-clients/<hashed_id>/config/``
     - :py:class:`~smarter.apps.prompt.views.detailviews.prompt_config_view.PromptConfigView`
   * - Configuration, deployed LLMClient
     - ``https://<name>.<account-number>.api.<domain>/config/`` (and ``/``), or the same paths on its
       verified custom domain
     - ``PromptConfigView``: ``smarter.urls.llmclients`` for the default host, and the root
       ``config/`` route of ``smarter.urls.console`` for a custom domain
   * - Configuration, platform api
     - ``https://<platform>/api/v1/llm-clients/<hashed_id>/config/``, plus the legacy aliases
       ``<llmclient_id>/config/``, ``<hashed_id>/prompt/config/`` and ``<llmclient_id>/prompt/config/``
     - ``PromptConfigView``
   * - Prompt
     - The configuration's ``url_llmclient``: ``/prompt/`` on the host that served the configuration,
       for a deployed LLMClient's own host or custom domain
       (:meth:`~smarter.apps.prompt.views.detailviews.prompt_config_view.PromptConfigView.prompt_url`),
       else ``https://<platform>/api/v1/llm-clients/<hashed_id>/prompt/`` (``LLMClient.url_llmclient``)
     - :py:class:`~smarter.apps.llmclient.api.v1.views.default.DefaultLLMClientApiView`, a
       :py:class:`~smarter.apps.llmclient.api.v1.views.base.LLMClientApiBaseViewSet`
   * - Server logs
     - The ``smarter-log-stream-url`` that the workbench passes, or the ``logStreamUrl`` prop
     - ``smarter.apps.dashboard.views.terminal_emulator.api.streams.stream_user_logs``
   * - Manifest editor
     - The ``smarter-manifest-editor-url`` that the workbench passes, or the ``manifestEditorUrl``
       prop: ``/workbench/llm-clients/<hashed_id>/manifest/editor/``, of the page's own origin
     - :py:class:`~smarter.apps.prompt.views.detailviews.prompt_manifest_view.LLMClientManifestEditorView`

A page that embeds the chat therefore calls one host only: its LLMClient's.

.. note::

  ``/workbench/llm-clients/<hashed_id>/prompt/`` is the workbench *page*
  (:py:class:`~smarter.apps.prompt.views.detailviews.prompt_workbench_view.PromptWorkbenchView`),
  not the prompt api.

.. note::

  ``smarter.hosts`` routes a deployed LLMClient's default host,
  ``<name>.<account-number>.[<environment>.]api.<domain>``, to ``smarter.urls.llmclients``, which
  serves ``/``, ``/config/`` and ``/prompt/`` only. A custom domain matches no host pattern, so it
  falls through to the default host's ``smarter.urls.console``, whose root ``config/`` and
  ``prompt/`` routes serve it.


Requests
--------

Every request is a ``POST`` with a JSON body, sent with ``fetch()``, ``credentials: "include"`` and
``mode: "cors"``. ``GET`` returns 405, unless the ``ALLOW_API_GET`` waffle switch is active for the
configuration.

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Header
     - Value
   * - ``Accept``
     - ``application/json``; for a prompt with ``streamProgress``,
       ``text/event-stream, application/json``.
   * - ``Content-Type``
     - ``application/json``
   * - ``X-Smarter-Capabilities``
     - ``chat-contract-v2``. See `Versions`_.
   * - ``X-CSRFToken``
     - The value of the CSRF cookie, or the ``csrftoken`` prop, or empty. Both views are CSRF exempt.
   * - ``X-Smarter-Client``, ``X-Smarter-ClientVersion``, ``X-Smarter-ClientType``
     - ``@smarter.sh/ui-chat``, the package's version, and ``react``.
   * - ``X-Smarter-RequestId``
     - The ``smarterRequestId`` prop, if set.
   * - ``Authorization``
     - ``Token <apiKey>``, if the ``apiKey`` prop is set.

Every custom header must be in ``CORS_ALLOW_HEADERS``, in ``smarter.settings.base``, or browsers
refuse to send it to another origin.


CORS
----

Preflight ``OPTIONS`` requests, and the CORS headers of the responses, come from the CORS middleware
(:py:class:`~smarter.lib.django.middleware.cors.SmarterCorsMiddleware`, which extends
``django-cors-headers``), with credentials allowed. An origin is allowed if:

- the platform's settings allow it (``CORS_ALLOWED_ORIGINS``, ``CORS_ALLOWED_ORIGIN_REGEXES``), or
- the LLMClient whose api the request calls lists it in ``spec.config.prompt.allowedOrigins``, in its
  manifest. :mod:`smarter.apps.llmclient.cors` applies these, through ``django-cors-headers``'
  ``check_request_enabled`` signal, for the configuration and prompt apis only: ``/``,
  ``/config/`` and ``/prompt/`` on a deployed LLMClient's own host, and
  ``/api/v1/llm-clients/<id>/config/``, ``.../prompt/`` and ``.../prompt/config/``.

``allowedOrigins`` are origins, ``http(s)://host[:port]``, without a path or a wildcard; the manifest
lowercases them and removes duplicates.

.. important::

  Traefik's CORS middleware answers preflight requests itself, before they reach Django, with a fixed
  list of origins and headers, which includes none of the ``X-Smarter-*`` headers. Each deployed
  LLMClient's Ingress (``smarter/apps/llmclient/k8s/ingress.yaml.tpl``) therefore attaches only the
  ``https-redirect`` middleware, so that Django applies the platform's settings and
  ``allowedOrigins``. An LLMClient deployed before this change keeps the old Ingress until it is
  deployed again. The platform's own hosts are defined in the smarter-infrastructure repository; a
  page that calls their ``/api/v1/`` urls from another origin needs them to drop the Traefik CORS
  middleware too.


Authentication
--------------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Caller
     - How it is authenticated
   * - The workbench
     - The web console's Django session cookie.
   * - A page with an ``apiKey``
     - ``Authorization: Token <apiKey>``, which
       :py:class:`~smarter.lib.drf.middleware.SmarterTokenAuthenticationMiddleware` authenticates for
       api urls: those under ``/api/``, or on the api subdomain, which includes every deployed
       LLMClient's host.
   * - An anonymous page
     - Allowed for a deployed LLMClient without an active api key
       (``LLMClient.is_authentication_required``). Its prompts run, and are charged, as the
       LLMClient's owner. An LLMClient with an api key answers an anonymous request with 403, an
       undeployed one with 404.

Both views extend :py:class:`~smarter.lib.django.views.SmarterOptionallyAuthenticatedApiView`, which,
unlike the web console's views, never redirects to the login page: it lets every request through to
the view, which authorizes it for the LLMClient it asks for, and answers with the error envelope if
not. It is never cached, and CSRF exempt.

A url with an id, a workbench or platform api url, requires a user who may read the LLMClient, and
answers anyone else with 404, so that the ids of other accounts' LLMClients can't be discovered.


Chat Sessions
-------------

A chat session is identified by a 64-character hexadecimal key, generated by the configuration api
(``SmarterRequestMixin.generate_session_key()``). The chat:

1. sends the key from its session cookie, if any, as the ``session_key`` query parameter and in the
   body of the configuration request,
2. saves the returned ``data.session_key`` in its session cookie, for the page's path,
3. sends the key, as the ``session_key`` query parameter and body field, with each prompt,
4. deletes the cookie on **new chat**, so that the next configuration request gets a new key.

The backend looks for the key in the url, the body, a header and a cookie, in that order
(``SmarterRequestMixin.find_session_key()``), and generates one if there is none. The session's
history is stored by the backend; the chat stores nothing but the key.


The Configuration
-----------------

Request body: ``{"session_key": "<key or empty>"}``
(:class:`~smarter.apps.prompt.contract.models.PromptChatApiConfigRequest`).

``PromptConfigView.chat_config()`` builds a :class:`~smarter.apps.prompt.contract.models.PromptChatApiConfig`,
and ``PromptConfigView.config()`` derives the response from it:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Request
     - Response
   * - A workbench or platform api url, which finds the LLMClient by its id and checks that the user
       may read it, or the cli
     - The complete configuration: every LLMClient field (``LLMClientConfigSerializer``), the
       session's diagnostic histories, and the lists of plugins and extensions.
   * - A deployed LLMClient's own host, or custom domain
     - The public configuration, :meth:`PromptChatApiConfig.public() <smarter.apps.prompt.contract.models.PromptChatApiConfig.public>`:
       the LLMClient's public fields only (:data:`~smarter.apps.prompt.contract.const.PUBLIC_LLMCLIENT_FIELDS`,
       without e.g. its owner's profile), the session's own messages, the public ``meta_data`` fields,
       and the plugins' and extensions' counts, without their lists.

Then, in version 2, the model is dumped as is; in version 1,
:meth:`PromptChatApiConfig.to_v1() <smarter.apps.prompt.contract.models.PromptChatApiConfig.to_v1>` renames its keys.

.. code-block:: json
   :caption: A version 2 public configuration

   {
     "data": {
       "contract": 2,
       "session_key": "e019a5c1cb2c1cb87992d2d03bccaf44c9d98406b46de5516a4fa03650038ac8",
       "sandbox_mode": false,
       "debug_mode": false,
       "llmclient": {
         "id": 1,
         "name": "stackademy_sql",
         "provider": "openai",
         "default_model": "gpt-4o-mini",
         "default_system_role": "You are a helpful assistant. ...",
         "app_name": "Stackademy",
         "app_assistant": "Stanley",
         "app_welcome_message": "Welcome to Stackademy! How can I help you today?",
         "app_example_prompts": ["Do you offer any courses on AI?"],
         "app_placeholder": "Ask me anything about Stackademy courses...",
         "app_file_attachment": false,
         "deployed": true,
         "url_llmclient": "https://stackademy-sql.3141-5926-5359.api.example.com/prompt/"
       },
       "history": { "chat_history": [] },
       "meta_data": { "ready": true, "is_deployed": true },
       "plugins": { "meta_data": { "total_plugins": 1, "plugins_returned": 1 }, "plugins": [] },
       "extensions": { "meta_data": { "total_extensions": 0, "extensions_returned": 0 }, "extensions": [] }
     },
     "api": "smarter.sh/v1",
     "metadata": { "command": "prompt_config", "thing": "PromptConfig" }
   }

No field of the contract is an untyped list. Every list holds a named model, and the few values
that are stored as arbitrary JSON, such as a tool's result, are
:data:`~smarter.apps.prompt.contract.models.PromptChatApiJson`, which is exactly JSON. In particular,
the lists of the complete configuration are models of their Django ORM rows
(:class:`~smarter.apps.prompt.contract.models.PromptChatApiOrmModel`), built from the rows by
``from_model()``, with exactly the rows' fields:

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Field
     - Model, and its row
   * - ``plugins.plugins``
     - ``PromptChatApiLLMClientPlugin``: ``LLMClientPlugin``, with its ``PluginMeta``, without its owner
   * - ``extensions.extensions``
     - ``PromptChatApiLLMClientExtension``: ``LLMClientExtensions``, with its Extension's slug, version and state
   * - ``history.prompt_tool_call_history``
     - ``PromptChatApiPromptToolCall``: ``PromptToolCall``
   * - ``history.prompt_plugin_usage_history``
     - ``PromptChatApiPromptPluginUsage``: ``PromptPluginUsage``
   * - ``history.plugin_selector_history``
     - ``PromptChatApiPluginSelection``: ``PluginSelectorHistory``
   * - ``history.llmclient_request_history``
     - ``PromptChatApiLLMClientRequest``: ``LLMClientRequests``

A plugin's class and a function's name are the ORM's choices, and a test fails if the two differ.
Messages (:class:`~smarter.apps.prompt.contract.models.PromptChatApiMessage`) declare their content
parts (text, image, audio, file and refusal, by ``type``) and their tool calls.

The fields that Smarter Chat reads are the declared fields of
:class:`~smarter.apps.prompt.contract.models.PromptChatApiConfig`,
:class:`~smarter.apps.prompt.contract.models.PromptChatApiLLMClient`,
:class:`~smarter.apps.prompt.contract.models.PromptChatApiHistory` and
:class:`~smarter.apps.prompt.contract.models.PromptChatApiMetaData`. ``llmclient.url_llmclient`` and
``session_key`` are required. Everything else is displayed, as is, in the Console's Config tab.

.. note::

  The system prompt, ``default_system_role``, is public: the chat sends it as the first message of
  a new session. Never put a secret in a system prompt.


The Prompt
----------

Request body (:class:`~smarter.apps.prompt.contract.models.PromptChatApiPromptRequest`):

.. code-block:: json

  {
    "session_key": "e019a5c1cb2c1cb87992d2d03bccaf44c9d98406b46de5516a4fa03650038ac8",
    "messages": [
      { "role": "system", "content": "You are a helpful assistant. DO NOT GUESS." },
      { "role": "assistant", "content": "Welcome to Stackademy! How can I help you today?" },
      { "role": "user", "content": "Do you offer any courses on AI?" }
    ]
  }

``messages`` is the whole thread, with only the roles that LLMs accept: ``system``, ``assistant``,
``user`` and ``tool``. Messages that came from the backend keep all of their original fields, for
example an assistant message's ``tool_calls``. Smarter's own ``smarter`` and ``smarter_error``
messages are never sent.

The view runs the prompt with the LLMClient's provider (``smarter_compatible_client``), which calls
the LLM, its tools, plugins and MCP servers, and saves the new messages in the session's history.
The provider adds the complete requests to and responses from the LLM to the completion, as
``smarter.first_iteration`` and ``smarter.second_iteration``, and a ``metadata`` object, whose tool
calls describe each plugin with its owner's profile. They include the system prompt and every tool
result, so :func:`~smarter.apps.prompt.contract.builders.without_diagnostics` removes them from every
response except the cli's.

Version 2
~~~~~~~~~

:class:`~smarter.apps.prompt.contract.models.PromptChatApiPromptResponse`. The http status is the prompt's own:
200, or the LLM provider's error status.

.. code-block:: json

  {
    "data": {
      "contract": 2,
      "status": 200,
      "messages": [
        { "role": "smarter", "content": "Smarter selected the stackademy_sql plugin." },
        { "role": "assistant", "content": "We offer CS210 Artificial Intelligence, for $700.00." }
      ],
      "completion": { "id": "chatcmpl-123", "object": "chat.completion", "choices": [], "usage": {} },
      "plugins": ["stackademy_sql"],
      "tools": ["smarter_plugin_0000000016"]
    },
    "api": "smarter.sh/v1",
    "metadata": { "command": "prompt", "thing": "LLMClient" }
  }

``messages`` are the messages that the prompt added to the thread, in order. ``completion``
(:class:`~smarter.apps.prompt.contract.models.PromptChatApiCompletion`) is the LLM's chat completion,
in the format of the OpenAI api, with only its declared fields; the chat reads its
``choices[0].finish_reason`` and ``usage``, to say when the LLM reached the LLMClient's max tokens.

A failed prompt has the error envelope beside ``data``, and its ``messages`` include the
``smarter_error`` message that is saved in the session's history:

.. code-block:: json

  {
    "data": {
      "contract": 2,
      "status": 401,
      "messages": [{ "role": "smarter_error", "content": "401 error: Incorrect API key provided." }],
      "completion": null,
      "plugins": [],
      "tools": []
    },
    "error": { "errorClass": "PromptChatApiErrorLLMProvider", "description": "Incorrect API key provided.", "status": 401 },
    "api": "smarter.sh/v1",
    "metadata": { "command": "prompt", "thing": "LLMClient" }
  }

Version 1
~~~~~~~~~

:class:`~smarter.apps.prompt.contract.models.PromptChatApiPromptResponseV1`: ``data`` is an AWS Lambda style
response (``isBase64Encoded``, ``statusCode``, ``headers``, ``body``), whose ``body`` is a JSON string.
Parsed, a successful body is a chat completion with Smarter's messages in ``smarter.messages``
(:class:`~smarter.apps.prompt.contract.models.PromptChatApiCompletionV1`), and a failed one is
``{"error": {"status", "message"}, "response": <the completion>}``
(:class:`~smarter.apps.prompt.contract.models.PromptChatApiFailureV1`).

Streaming the prompt's progress
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When the request's ``Accept`` header includes ``text/event-stream``
(:py:func:`~smarter.apps.prompt.progress.wants_event_stream`), the response is Server-Sent Events,
in either version. Its http status is always 200; the prompt's own status is in its ``result`` event.

.. code-block:: text

  retry: 3000

  event: progress
  data: {"type": "llm_request", "message": "Sending the prompt to the LLM", "iteration": 1}

  event: progress
  data: {"type": "tool_requested", "message": "Calling tool stackademy_sql", "tool": "stackademy_sql", "function": "smarter_plugin_0000000016", "arguments": "{...}"}

  : keepalive

  event: result
  data: {"status": 200, "response": {"data": {"contract": 2, "status": 200, "messages": [...]}, "api": "smarter.sh/v1", "metadata": {}}}

- ``retry: 3000`` comes first, once.
- ``progress`` events (:class:`~smarter.apps.prompt.contract.models.PromptChatApiProgressEvent`) describe the
  prompt's steps, as they happen. Every one has a ``type`` and a ``message``, a short sentence that
  the chat displays as is.
- ``: keepalive`` comments are sent every 15 seconds while the prompt waits.
- ``result`` (:class:`~smarter.apps.prompt.contract.models.PromptChatApiProgressResult`) comes last, once.
  ``response`` is exactly the JSON of a non-streaming response.

.. list-table:: Progress event types (:py:class:`~smarter.apps.prompt.progress.PromptProgressEvents`)
   :header-rows: 1
   :widths: 22 33 45

   * - ``type``
     - Sent when
     - Other fields
   * - ``llm_request``
     - The prompt, or the results of its tool calls, is sent to the LLM.
     - ``iteration``: 1 for the prompt, 2 and up for tool results.
   * - ``tool_requested``
     - The LLM calls a tool.
     - ``tool``: its name as users know it. ``function``: the function name that the LLM called.
       ``arguments``: a JSON string, truncated to 500 characters.
   * - ``tool_responded``
     - A tool returns its result to the LLM.
     - ``tool``, ``function``
   * - ``plugin_called``
     - A plugin runs.
     - ``plugin``
   * - ``mcp_tool_called``
     - An MCP server's tool is called.
     - ``mcpclient``, ``tool``, ``arguments``
   * - ``mcp_tool_responded``
     - An MCP server's tool returns.
     - ``mcpclient``, ``tool``, ``is_error``
   * - ``mcp_tool_failed``
     - An MCP server's tool can't be called.
     - ``mcpclient``, ``tool``, ``error``

The events come from the signals that a prompt already sends, which :py:mod:`smarter.apps.prompt.progress`
forwards to the stream of the prompt that sent them. To add an event type, add it to
``PromptProgressEvents`` and to the contract's ``PromptChatApiProgressEventType``; a test fails if they differ.
Older versions of the chat display any event's ``message``, so new types are backward compatible.

Streaming needs Smarter's ASGI server (uvicorn), and any proxy in front of it must not buffer the
response. The stream sends ``X-Accel-Buffering: no`` for nginx.


Errors
------

Every error of both apis, in both versions, is one envelope,
:class:`~smarter.apps.prompt.contract.models.PromptChatApiErrorResponse`, built by
:func:`~smarter.apps.prompt.contract.builders.chat_error_response`:

.. code-block:: json

  {
    "error": { "errorClass": "PromptChatApiErrorNotFound", "description": "LLMClient not found.", "status": 404 },
    "api": "smarter.sh/v1",
    "metadata": { "command": "prompt_config", "thing": "PromptConfig" }
  }

It never includes a stack trace: errors are logged with theirs, and the response's
``SmarterJournaledJsonErrorResponse`` is created with ``include_stack_trace=False``.

.. list-table::
   :header-rows: 1
   :widths: 35 10 55

   * - ``errorClass``
     - Status
     - When
   * - ``PromptChatApiErrorNotFound``
     - 404
     - The LLMClient doesn't exist, the user can't read it, it isn't deployed (to an anonymous client,
       or on its own host), or the chat session can't be found.
   * - ``PromptChatApiErrorForbidden``
     - 403
     - The LLMClient has an active api key, and the request isn't authenticated.
   * - ``PromptChatApiErrorNotReady``
     - 400
     - The LLMClient can't be initialized.
   * - ``PromptChatApiErrorLLMProvider``
     - provider's
     - The LLM provider rejected the prompt (version 2; version 1 keeps its Lambda style failure).
   * - ``PromptChatApiErrorInternal``
     - 500
     - Anything unexpected, including a configuration that breaks the contract. The description is
       generic.

Smarter Chat displays ``error.description``. A response that isn't JSON, such as a proxy's error
page, becomes "Unexpected response from the Smarter api
(http <status>)".


The Server Log Stream
---------------------

The Console's Server Logs tab opens an ``EventSource`` to ``logStreamUrl``, with credentials:

- the first event is named ``bulk``, and its data is a JSON array of the recent log records,
- each later, unnamed event is one record, as JSON, with ``message`` (the formatted line, including
  its ANSI colors), ``level``, ``logger`` and ``timestamp``,
- the ``level`` query parameter sets the minimum level; without it, the stream sends the records at
  ``smarter_settings.log_level`` and above. In sandbox mode the chat adds ``level=DEBUG``,
- the ``session_key`` query parameter narrows the stream to the records of one chat session. The
  platform tags each record of a request to an LLMClient's api with the request's ``session_key``,
  including the records of a prompt that streams its progress, and the config api tags its
  records with the session key that it creates for a new chat. The chat adds its own session key,
  and opens a new stream for each new chat.

This stream is not part of the versioned contract: only the web console's own pages use it.


Changing the Contract Safely
----------------------------

1. Change the models in :mod:`smarter.apps.prompt.contract.models` first, then the code that builds
   the response.
2. **Adding** a field, a progress event type, or a message role that is only displayed is backward
   compatible. Declare it in the models only if Smarter Chat reads it.
3. **Removing or renaming** a declared field, or changing its type, breaks the installed versions of
   the chat. Add the new shape beside the old one, and remove the old one only in a new version of
   the contract, which clients ask for with a new capability.
4. **A new request header** must be added to ``CORS_ALLOW_HEADERS``, or pages on other domains break.
5. Run ``make chat-contract``, and update Smarter Chat's code and fixtures until ``make test`` passes
   there, then update this page.


Technical Reference
-------------------

- :doc:`Contract <technical-reference/contract>`
- :doc:`Configuration view <technical-reference/config-view>`
- :doc:`Prompt api view <technical-reference/prompt-api-view>`
- :doc:`Prompt progress <technical-reference/progress>`
- :doc:`Per-LLMClient CORS origins <technical-reference/cors>`
