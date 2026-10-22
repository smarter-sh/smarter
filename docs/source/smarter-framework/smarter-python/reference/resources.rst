..
   Generated from the smarter-python SDK's docstrings by its scripts/generate_reference.py.
   Do not edit: change the docstring in https://github.com/smarter-sh/smarter-python, and regenerate.

Resources
=========

``smarter.resources.base``
--------------------------

.. py:module:: smarter.resources.base

The base classes of the SDK's api resources.

Each resource family (LLMClients, Guardrails, ...) is a class whose methods send requests through
the client's :class:`~smarter.core.http.SmarterHttpClient`. Writes go through the manifest api,
exactly as the ``smarter`` cli sends them, so that the platform validates them and applies its
business rules. The REST endpoints are used to read resources, and for actions that the manifest
api has no verb for, such as evaluating a Guardrail or calling an MCP tool.

.. py:data:: ManifestInput

   A manifest: a :class:`Manifest`, a typed SAM model, a dict, YAML or JSON text, or the path of a YAML or JSON file.

.. py:function:: resource_id(value: 'SmarterIdType') -> 'str'

   A resource id as a url path segment.

   :param value: The resource's integer id, or its hashed id.
   :returns: The id, as text.
   :raises SmarterValueError: If the id is empty, or contains a slash.

.. py:class:: SmarterAPIResource(client: 'Smarter') -> 'None'

   A group of api operations.

   :param client: The client whose requests the operations send.


.. py:class:: SmarterKindResource

   Bases: :class:`smarter.resources.base.SmarterAPIResource`, :class:`typing.Generic`

   The operations of one resource kind, e.g. Guardrail.

   Subclasses set :attr:`kind`, the manifest kind, and :attr:`path`, the REST list endpoint, and
   :attr:`model`, the model of a resource. They get:

   - ``list()``, ``retrieve()`` and ``find()``, from the REST api, and
   - ``apply()``, ``describe()``, ``delete()``, ``example_manifest()`` and ``json_schema()``, from the
     manifest api.

   .. py:method:: list() -> 'list[ModelT]'

      Every resource of this kind that the api key's user may read.

      :returns: The resources.


   .. py:method:: retrieve(id: 'SmarterIdType') -> 'ModelT'

      One resource, by its id or hashed id.

      :param id: The resource's integer id, or its hashed id.
      :returns: The resource.
      :raises NotFoundError: If it does not exist, or the user may not read it.


   .. py:method:: find(name: 'str') -> 'ModelT'

      One resource, by its name.

      :param name: The resource's name.
      :returns: The first resource of that name that the user may read.
      :raises ResourceNotFoundError: If there is none.


   .. py:method:: apply(manifest: 'ManifestInput') -> 'SmarterJournalMessage'

      Create or update a resource of this kind from its manifest.

      :param manifest: The manifest.
      :returns: The platform's response, whose ``message`` says what was applied.
      :raises SmarterValueError: If the manifest is of another kind.


   .. py:method:: describe(name: 'str') -> 'Manifest'

      A resource's manifest, with its read-only ``status``.

      :param name: The resource's name.
      :returns: The manifest.


   .. py:method:: delete(name: 'str') -> 'SmarterJournalMessage'

      Permanently delete a resource.

      :param name: The resource's name.
      :returns: The platform's response.


   .. py:method:: example_manifest() -> 'Manifest'

      A valid example manifest of this kind, to start from.

      :returns: The manifest.


   .. py:method:: json_schema() -> 'SmarterJsonObjectType'

      The JSON Schema of this kind's manifest.

      :returns: The schema.



.. py:function:: to_manifest(manifest: 'ManifestInput') -> 'Manifest'

   A manifest from any of the forms that the SDK accepts.

   A string that names an existing file is read as a file. Any other string is parsed as YAML.

   :param manifest: The manifest.
   :returns: The parsed manifest.
   :raises SmarterValueError: If it cannot be parsed.

``smarter.resources.manifests``
-------------------------------

.. py:module:: smarter.resources.manifests

The manifest api: the brokered, journaled ``/api/v1/cli/`` endpoints that the ``smarter`` cli uses.

Every resource kind is managed through the same verbs: ``apply``, ``validate``, ``get``,
``describe``, ``delete``, ``deploy``, ``undeploy`` and ``logs``. The kind's broker on the platform
validates the manifest with its Pydantic models and applies its business rules, so this is the
only way that the SDK writes resources.

.. code-block:: python

    from smarter import Smarter

    client = Smarter()
    client.manifests.apply("guardrail.yaml")
    manifest = client.manifests.describe("Guardrail", "pii_redactor")
    client.manifests.delete("Guardrail", "pii_redactor")

.. py:class:: ManifestValidation

   Bases: :class:`smarter.models.base.SmarterModel`

   The result of validating a manifest, without applying it.

   .. py:attribute:: valid
      :type: bool


   .. py:attribute:: errors
      :type: list



.. py:function:: kind_segment(kind: 'str') -> 'str'

   A kind as a url path segment.

   :param kind: The manifest kind, e.g. ``LLMClient``.
   :returns: The kind.
   :raises SmarterValueError: If it is empty or not a single path segment.

.. py:class:: Manifests

   Bases: :class:`smarter.resources.base.SmarterAPIResource`

   The manifest api: apply, validate, get, describe, delete, deploy, undeploy and logs, for any kind.

   .. py:method:: apply(manifest: 'ManifestInput') -> 'SmarterJournalMessage'

      Create or update a resource from its manifest.

      The platform compares the manifest with the resource's current state and makes the changes
      that the difference requires.

      :param manifest: The manifest: a :class:`~smarter.models.manifest.Manifest`, a dict, YAML
          text, or the path of a YAML file.
      :returns: The platform's response, whose ``message`` says what was applied.
      :raises BadRequestError: If the platform rejects the manifest.


   .. py:method:: validate(manifest: 'ManifestInput') -> 'ManifestValidation'

      Validate a manifest without applying it.

      :param manifest: The manifest, in any form that :meth:`apply` accepts.
      :returns: Whether it is valid, and its errors.


   .. py:method:: get(kind: 'str', name: 'str | None' = None) -> 'ManifestList'

      The resources of one kind, as a table.

      :param kind: The manifest kind, e.g. ``LLMClient``.
      :param name: Only the resource of this name.
      :returns: The table: ``.items`` are its rows, and ``.names`` the resources' names.


   .. py:method:: describe(kind: 'str', name: 'str') -> 'Manifest'

      A resource's manifest, with its read-only ``status``.

      :param kind: The manifest kind.
      :param name: The resource's name.
      :returns: The manifest, which :meth:`apply` accepts as is.
      :raises NotFoundError: If the resource does not exist.


   .. py:method:: delete(kind: 'str', name: 'str') -> 'SmarterJournalMessage'

      Permanently delete a resource.

      :param kind: The manifest kind.
      :param name: The resource's name.
      :returns: The platform's response.
      :raises NotFoundError: If the resource does not exist.


   .. py:method:: deploy(kind: 'str', name: 'str') -> 'SmarterJournalMessage'

      Deploy a resource, e.g. an LLMClient on its own host name.

      This creates real infrastructure on the platform's cloud, e.g. DNS records, TLS certificates
      and Kubernetes ingresses, which may be billable.

      :param kind: The manifest kind of a deployable resource. See :meth:`smarter.Smarter.kinds`.
      :param name: The resource's name.
      :returns: The platform's response.


   .. py:method:: undeploy(kind: 'str', name: 'str') -> 'SmarterJournalMessage'

      Undo a resource's deployment.

      :param kind: The manifest kind.
      :param name: The resource's name.
      :returns: The platform's response.


   .. py:method:: logs(kind: 'str', name: 'str') -> 'SmarterJournaledResponse[SmarterJsonObjectType]'

      A resource's logs.

      :param kind: The manifest kind.
      :param name: The resource's name.
      :returns: The platform's response: its ``message``, and its ``data`` for the kinds that have logs.


   .. py:method:: example_manifest(kind: 'str') -> 'Manifest'

      A valid example manifest of a kind, to start from.

      :param kind: The manifest kind.
      :returns: The manifest.


   .. py:method:: json_schema(kind: 'str') -> 'SmarterJsonObjectType'

      The JSON Schema of a kind's manifest, e.g. to validate manifests locally or to generate a form.

      :param kind: The manifest kind.
      :returns: The schema (draft 2020-12).



``smarter.resources.llmclients``
--------------------------------

.. py:module:: smarter.resources.llmclients

LLMClients: read them, prompt them, stream a prompt's progress, and hold a multi-turn chat.

.. code-block:: python

    from smarter import Smarter

    client = Smarter()
    llmclient = client.llm_clients.find("calculator")

    # one prompt
    response = client.llm_clients.prompt(llmclient.id, "What is 17 times 23?")
    print(response.text)

    # a conversation, which keeps its session and thread
    chat = client.llm_clients.chat(llmclient.id)
    print(chat.send("What is 2 to the 10th power?").text)
    print(chat.send("And divided by 4?").text)

    # the prompt's progress, e.g. its tool calls, while it runs
    with client.llm_clients.stream(llmclient.id, "What is sin(pi / 2)?") as stream:
        for event in stream:
            print(event.message)
        print(stream.response.text)

.. py:data:: MessageInput

   A message: a :class:`PromptChatApiMessage`, or a dict such as ``{"role": "user", "content": "Hi"}``.

.. py:data:: PromptInput

   A prompt: the text of one user message, or a list of messages.

.. py:class:: SmarterPromptError(message: 'str', response: 'PromptChatApiPromptResponse | PromptChatApiErrorResponse')

   Bases: :class:`smarter.core.exceptions.SmarterError`

   A streamed prompt failed.

   Its ``result`` event carried an error response.

   :param message: The error's description.
   :param response: The error response.


.. py:function:: to_messages(prompt: 'PromptInput') -> 'list[PromptChatApiMessage]'

   A prompt as a list of messages.

   :param prompt: A user message's text, or a list of messages.
   :returns: The messages.

.. py:function:: request_messages(messages: 'Sequence[PromptChatApiMessage]') -> 'list[SmarterJsonType]'

   Messages as the prompt api's request sends them: only those that the LLM accepts.

   Smarter's own ``smarter`` and ``smarter_error`` messages are left out, as Smarter Chat leaves them out.
   Every message keeps its ``content``, even when it is null, e.g. an assistant's tool calls: the
   platform requires the key.

   :param messages: A chat thread.
   :returns: The messages, as JSON.

.. py:class:: PromptStream(events: 'AbstractContextManager[Iterator[ServerSentEvent]]') -> 'None'

   A prompt whose progress is streamed as Server-Sent Events.

   Iterate it for the :class:`PromptChatApiProgressEvent` events, e.g. "Calling tool calculator". When
   the iteration ends, :attr:`response` is the prompt's response, exactly as a non-streaming prompt
   returns it. Use it as a context manager, so that the connection is closed.

   :param events: The context manager of the stream's Server-Sent Events.

   .. py:method:: until_done() -> 'PromptChatApiPromptResponse'

      Read the stream to its end, discarding the progress events.

      :returns: The prompt's response.


   .. py:property:: result

      The final ``result`` event, once the stream has been read: the prompt's status and response.


   .. py:property:: response

      The prompt's response, once the stream has been read.

      :raises SmarterPromptError: If the prompt failed.
      :raises SmarterError: If the stream has not been read, or ended without a result.



.. py:class:: ChatSession(llmclients: 'LLMClients', llmclient_id: 'SmarterIdType', config: 'PromptChatApiConfig') -> 'None'

   A multi-turn conversation with an LLMClient.

   It keeps the chat session's key, so that the platform keeps the session's history, and the
   thread, which it sends with each prompt as Smarter Chat does. Create one with
   :meth:`LLMClients.chat`.

   :param llmclients: The LLMClients resource.
   :param llmclient_id: The LLMClient's id or hashed id.
   :param config: The chat session's configuration.

   .. py:property:: session_key

      The chat session's key, with which the session can be resumed: see :meth:`LLMClients.chat`.


   .. py:method:: send(content: 'str | MessageInput') -> 'PromptChatApiPromptResponse'

      Send a message, and add it and the prompt's messages to the thread.

      :param content: A user message's text, or a message.
      :returns: The prompt's response. ``.text`` is the LLM's reply.


   .. py:method:: stream(content: 'str | MessageInput') -> 'ChatStream'

      Send a message, and stream the prompt's progress.

      The thread is updated when the stream has been read to its end.

      :param content: A user message's text, or a message.
      :returns: The stream. Use it as a context manager.



.. py:class:: ChatStream(events: 'AbstractContextManager[Iterator[ServerSentEvent]]', session: 'ChatSession', thread: 'list[PromptChatApiMessage]') -> 'None'

   Bases: :class:`smarter.resources.llmclients.PromptStream`

   A :class:`PromptStream` of a :class:`ChatSession`, which adds the prompt's messages to the session's thread.


.. py:class:: LLMClients

   Bases: :class:`smarter.resources.base.SmarterKindResource`

   LLMClients: ``/api/v1/llm-clients/``, and the manifest api's ``LLMClient`` kind.

   .. py:method:: config(id: 'SmarterIdType', *, session_key: 'str | None' = None, verbose: 'bool' = False) -> 'PromptChatApiConfig'

      An LLMClient's chat configuration, and a chat session.

      By default the configuration has what a chat needs: the LLMClient, the session's key and chat
      history, a short ``meta_data``, and the counts of the LLMClient's plugins and extensions, whose
      lists are empty. ``verbose=True`` asks for the complete configuration, which adds those lists,
      the session's tool calls (``history.prompt_tool_call_history``) and the complete ``meta_data``.

      .. code-block:: python

          config = client.llm_clients.config(llmclient.id, verbose=True)
          print([plugin.plugin_meta.name for plugin in config.plugins.plugins])

      :param id: The LLMClient's id or hashed id.
      :param session_key: An existing session's key, to resume it with its history, or None for a new session.
      :param verbose: True for the complete configuration, with the lists of the LLMClient's plugins
          and extensions, and the session's tool calls. A deployed LLMClient's own host ignores it.
      :returns: The configuration, whose ``session_key`` identifies the session.


   .. py:method:: prompt(id: 'SmarterIdType', prompt: 'PromptInput', *, session_key: 'str | None' = None, timeout: 'float | None' = None) -> 'PromptChatApiPromptResponse'

      Prompt an LLMClient.

      The platform runs the LLMClient's whole prompt: it selects plugins, calls the LLM, runs the
      tools that the LLM calls, and applies the Guardrails. Prompts are billed by the LLM provider.

      :param id: The LLMClient's id or hashed id.
      :param prompt: The text of one user message, or the chat thread as a list of messages.
      :param session_key: The chat session's key, from :meth:`config`, to keep the prompt's history
          in that session.
      :param timeout: Seconds, instead of the client's timeout.
      :returns: The response. ``.text`` is the LLM's final reply, and ``.data.messages`` every
          message that the prompt added, including Smarter's own.
      :raises APIStatusError: If the prompt failed, e.g. the LLM provider returned an error. The
          exception's ``body`` is the error response.


   .. py:method:: stream(id: 'SmarterIdType', prompt: 'PromptInput', *, session_key: 'str | None' = None, timeout: 'float | None' = None) -> 'PromptStream'

      Prompt an LLMClient, and stream its progress: the LLM requests, tool calls and plugin calls.

      :param id: The LLMClient's id or hashed id.
      :param prompt: The text of one user message, or the chat thread as a list of messages.
      :param session_key: The chat session's key.
      :param timeout: Seconds to wait for each event, instead of the client's timeout.
      :returns: The stream. Use it as a context manager, and iterate it for the progress events.


   .. py:method:: chat(id: 'SmarterIdType', *, session_key: 'str | None' = None) -> 'ChatSession'

      Start or resume a conversation with an LLMClient.

      :param id: The LLMClient's id or hashed id.
      :param session_key: An existing session's key, to resume it, or None for a new session.
      :returns: The chat session.


   .. py:method:: plugins(id: 'SmarterIdType') -> 'list[LLMClientPlugin]'

      An LLMClient's plugins.

      :param id: The LLMClient's integer id.
      :returns: The plugins.


   .. py:method:: extensions(id: 'SmarterIdType') -> 'list[LLMClientExtension]'

      The extensions whose tools an LLMClient offers the LLM, e.g. ``calculator``.

      :param id: The LLMClient's integer id.
      :returns: The extensions.


   .. py:method:: api_keys(id: 'SmarterIdType') -> 'list[LLMClientApiKey]'

      The api keys that may call an LLMClient that requires authentication.

      :param id: The LLMClient's integer id.
      :returns: The api keys.


   .. py:method:: custom_domains(id: 'SmarterIdType') -> 'list[LLMClientCustomDomain]'

      The custom domains of an LLMClient.

      :param id: The LLMClient's integer id.
      :returns: The custom domains.


   .. py:method:: deploy(name: 'str') -> 'SmarterJournalMessage'

      Deploy an LLMClient on its own host name.

      This creates real, possibly billable infrastructure: DNS records, a TLS certificate and a
      Kubernetes ingress.

      :param name: The LLMClient's name.
      :returns: The platform's response.


   .. py:method:: undeploy(name: 'str') -> 'SmarterJournalMessage'

      Undo an LLMClient's deployment.

      :param name: The LLMClient's name.
      :returns: The platform's response.



``smarter.resources.guardrails``
--------------------------------

.. py:module:: smarter.resources.guardrails

Guardrails: checks that the platform runs on prompts and on the LLM's replies.

.. code-block:: python

    result = client.guardrails.evaluate(17, "My card is 4111 1111 1111 1111")
    if result.triggered:
        print(result.disposition, result.text)

.. py:class:: Guardrails

   Bases: :class:`smarter.resources.base.SmarterKindResource`

   Guardrails: ``/api/v1/guardrails/``, and the manifest api's ``Guardrail`` kind.

   .. py:method:: evaluate(id: 'SmarterIdType', text: 'str', *, stage: "Literal['input', 'output']" = 'input') -> 'GuardrailEvaluation'

      Dry-run a Guardrail on a text, without saving an event.

      :param id: The Guardrail's id or hashed id.
      :param text: The text, e.g. a prompt (``input``) or an LLM's reply (``output``).
      :param stage: The stage to evaluate the text as. The Guardrail must run on it.
      :returns: Whether it triggered, its disposition, and the text after its action.
      :raises BadRequestError: If the text is empty or too long, or the Guardrail does not run on the stage.


   .. py:method:: events(id: 'SmarterIdType', *, reviewed: 'bool | None' = None, disposition: 'str | None' = None) -> 'GuardrailEvents'

      The latest events of a Guardrail that the user owns.

      :param id: The Guardrail's id or hashed id.
      :param reviewed: Only reviewed (True) or unreviewed (False) events.
      :param disposition: Only events of this disposition, e.g. ``blocked``.
      :returns: The events, newest first.



``smarter.resources.mcpclients``
--------------------------------

.. py:module:: smarter.resources.mcpclients

MCPClients: the platform's connections to Model Context Protocol servers.

.. code-block:: python

    tools = client.mcp_clients.tools(1)
    result = client.mcp_clients.call_tool(1, "aws___search_documentation", {"search_phrase": "S3"})
    print(result.content)

.. py:class:: MCPClients

   Bases: :class:`smarter.resources.base.SmarterKindResource`

   MCPClients: ``/api/v1/mcpclients/``, and the manifest api's ``MCPClient`` kind.

   .. py:method:: tools(id: 'SmarterIdType', *, refresh: 'bool' = False) -> 'MCPClientTools'

      The tools that an MCPClient allows the LLM to call, from the server's cached catalog.

      :param id: The MCPClient's id or hashed id.
      :param refresh: True to read the catalog from the server now.
      :returns: The connection's state, the server's instructions, and the tools.


   .. py:method:: refresh(id: 'SmarterIdType') -> 'MCPClientStatus'

      Reconnect to an MCPClient's server, and reload its catalog.

      Only the owner may refresh.

      :param id: The MCPClient's id or hashed id.
      :returns: The connection's state.


   .. py:method:: call_tool(id: 'SmarterIdType', tool: 'str', arguments: 'Mapping[str, SmarterJsonType] | None' = None) -> 'MCPToolResult'

      Call one of an MCPClient's tools.

      Only the owner may call tools.

      :param id: The MCPClient's id or hashed id.
      :param tool: The tool's name.
      :param arguments: The tool's arguments, as its input schema describes them.
      :returns: The tool's result. Check ``is_error``: a tool reports its own failures in its result.



``smarter.resources.vectorstores``
----------------------------------

.. py:module:: smarter.resources.vectorstores

Vectorstores: vector databases for retrieval-augmented generation.

.. code-block:: python

    client.vectorstores.add_text(2, "Our refund window is 30 days.", name="refunds")
    client.vectorstores.add_files(2, ["handbook.pdf"])
    for result in client.vectorstores.search(2, "How long is the refund window?").results:
        print(result.score, result.text)

.. py:class:: Vectorstores

   Bases: :class:`smarter.resources.base.SmarterKindResource`

   Vectorstores: ``/api/v1/vectorstores/``, and the manifest api's ``Vectorstore`` kind.

   The platform serves these endpoints only when ``SMARTER_ENABLE_VECTORSTORE`` is true.

   .. py:method:: status(id: 'SmarterIdType') -> 'VectorstoreStatus'

      A vectorstore's state, checked now.

      :param id: The vectorstore's id or hashed id.
      :returns: Its status and vector count.


   .. py:method:: deploy(id: 'SmarterIdType') -> 'Vectorstore'

      Deploy a vectorstore: create its database, or connect to the provider's.

      A self-hosted vectorstore creates real, possibly billable, Kubernetes resources.

      :param id: The vectorstore's id or hashed id.
      :returns: The vectorstore.


   .. py:method:: undeploy(id: 'SmarterIdType') -> 'Vectorstore'

      Stop serving a vectorstore.

      A self-hosted server's data is kept.

      :param id: The vectorstore's id or hashed id.
      :returns: The vectorstore.


   .. py:method:: documents(id: 'SmarterIdType') -> 'VectorstoreDocuments'

      A vectorstore's documents, newest first.

      :param id: The vectorstore's id or hashed id.
      :returns: The documents.


   .. py:method:: add_text(id: 'SmarterIdType', text: 'str', *, name: 'str | None' = None, metadata: 'Mapping[str, SmarterJsonType] | None' = None) -> 'VectorstoreDocumentsAdded'

      Add a text as a document.

      :param id: The vectorstore's id or hashed id.
      :param text: The text.
      :param name: The document's name.
      :param metadata: A JSON object, stored with each of the document's chunks.
      :returns: The added document. It is loaded asynchronously, once the vectorstore is deployed.


   .. py:method:: add_url(id: 'SmarterIdType', url: 'str', *, metadata: 'Mapping[str, SmarterJsonType] | None' = None) -> 'VectorstoreDocumentsAdded'

      Add a public web page or file, by its url, as a document.

      The platform fetches it.

      :param id: The vectorstore's id or hashed id.
      :param url: The url.
      :param metadata: A JSON object, stored with each of the document's chunks.
      :returns: The added document.


   .. py:method:: add_files(id: 'SmarterIdType', files: 'Sequence[str | Path]') -> 'VectorstoreDocumentsAdded'

      Upload files as documents, e.g. PDF, Word, HTML or text files.

      The platform extracts their text.

      :param id: The vectorstore's id or hashed id.
      :param files: The files' paths.
      :returns: The added documents.


   .. py:method:: delete_document(id: 'SmarterIdType', document_id: 'int') -> 'VectorstoreDocumentDeleted'

      Remove a document and its chunks.

      The removal is asynchronous.

      :param id: The vectorstore's id or hashed id.
      :param document_id: The document's id.
      :returns: The document, being deleted.


   .. py:method:: search(id: 'SmarterIdType', query: 'str', *, k: 'int' = 4, search_type: "Literal['similarity', 'mmr', 'similarity_score_threshold']" = 'similarity', score_threshold: 'float | None' = None, fetch_k: 'int | None' = None, lambda_mult: 'float | None' = None, filter: 'Mapping[str, SmarterJsonType] | None' = None) -> 'VectorstoreSearchResults'

      Search a vectorstore.

      :param id: The vectorstore's id or hashed id.
      :param query: The search text.
      :param k: How many chunks to return. The platform caps it.
      :param search_type: ``similarity``, ``mmr`` (maximal marginal relevance), or ``similarity_score_threshold``.
      :param score_threshold: The minimum score, for ``similarity_score_threshold``.
      :param fetch_k: How many chunks ``mmr`` considers.
      :param lambda_mult: ``mmr``'s balance of relevance (1) and diversity (0).
      :param filter: Only chunks whose metadata match.
      :returns: The matching chunks, best first.


   .. py:method:: snapshots(id: 'SmarterIdType') -> 'VectorstoreSnapshots'

      A vectorstore's snapshots.

      :param id: The vectorstore's id or hashed id.
      :returns: The snapshots.


   .. py:method:: create_snapshot(id: 'SmarterIdType') -> 'VectorstoreSnapshot'

      Take a snapshot of a vectorstore's data now.

      :param id: The vectorstore's id or hashed id.
      :returns: The snapshot.


   .. py:method:: restore(id: 'SmarterIdType', snapshot_id: 'int') -> 'VectorstoreRestored'

      Replace a vectorstore's data with one of its snapshots.

      :param id: The vectorstore's id or hashed id.
      :param snapshot_id: The snapshot's id.
      :returns: The restored vector count.



``smarter.resources.llmhosts``
------------------------------

.. py:module:: smarter.resources.llmhosts

LLMHosts: open-weight models that the platform serves on its own Kubernetes cluster.

.. code-block:: python

    models = client.llm_hosts.discover(query="qwen", task="chat")
    plan = client.llm_hosts.plan(3)          # what deploying would create, without creating it
    status = client.llm_hosts.status(3)

.. py:class:: LLMHosts

   Bases: :class:`smarter.resources.base.SmarterKindResource`

   LLMHosts: ``/api/v1/llmhosts/``, and the manifest api's ``LLMHost`` kind.

   .. py:method:: status(id: 'SmarterIdType') -> 'LLMHostStatus'

      An LLMHost's state, read from Kubernetes now.

      :param id: The LLMHost's id or hashed id.
      :returns: Its status, replicas and pods.


   .. py:method:: logs(id: 'SmarterIdType', *, tail: 'int' = 200) -> 'LLMHostLogs'

      The latest log lines of an LLMHost's pods.

      :param id: The LLMHost's id or hashed id.
      :param tail: How many lines.
      :returns: The logs.


   .. py:method:: plan(id: 'SmarterIdType') -> 'LLMHostPlan'

      The Kubernetes resources that deploying an LLMHost would create, without creating them.

      :param id: The LLMHost's id or hashed id.
      :returns: The resources.


   .. py:method:: deploy(id: 'SmarterIdType') -> 'LLMHostStatus'

      Deploy an LLMHost on the platform's cluster.

      This creates real, billable infrastructure, e.g. GPU nodes. Check :meth:`plan` first.

      :param id: The LLMHost's id or hashed id.
      :returns: Its state.


   .. py:method:: undeploy(id: 'SmarterIdType', *, purge: 'bool' = False) -> 'LLMHostStatus'

      Undeploy an LLMHost.

      :param id: The LLMHost's id or hashed id.
      :param purge: True to delete its model storage too.
      :returns: Its state.


   .. py:method:: report() -> 'LLMHostReport'

      A report of every LLMHost that the user may read: counts by status and engine, and estimated costs.

      :returns: The report.


   .. py:method:: discover(*, query: 'str | None' = None, task: 'str | None' = None, catalog: 'str' = 'huggingface', limit: 'int' = 20) -> 'list[DiscoveredModel]'

      Search a public model catalog for models that an LLMHost can serve.

      :param query: The search text, e.g. ``qwen``.
      :param task: Only models of this task, e.g. ``chat`` or ``embedding``.
      :param catalog: The catalog.
      :param limit: The maximum number of models.
      :returns: The models, each with the LLMHost manifest that would serve it.


   .. py:method:: discover_manifest(repository: 'str', *, catalog: 'str' = 'huggingface', engine: 'str | None' = None, name: 'str | None' = None, token_secret: 'str | None' = None) -> 'Manifest'

      An LLMHost manifest for a model in a public catalog, ready to apply.

      :param repository: The model's repository, e.g. ``Qwen/Qwen2.5-7B-Instruct``.
      :param catalog: The catalog.
      :param engine: The inference engine, or None for the platform's choice.
      :param name: The LLMHost's name, or None for one derived from the repository.
      :param token_secret: The name of a Secret that holds the catalog's access token, for gated models.
      :returns: The manifest, which :meth:`apply` accepts.



``smarter.resources.catalog``
-----------------------------

.. py:module:: smarter.resources.catalog

Secrets, plugins, orchestrators and vectorsearches: the kinds whose REST api only lists and reads them.

.. py:data:: PLUGIN_KINDS

   The manifest kinds of plugins.

.. py:class:: Secrets

   Bases: :class:`smarter.resources.base.SmarterKindResource`

   Secrets: ``/api/v1/secrets/``, and the manifest api's ``Secret`` kind.

   The api never returns a secret's value. Create and rotate secrets with :meth:`apply`.


.. py:class:: Plugins

   Bases: :class:`smarter.resources.base.SmarterKindResource`

   Plugins: ``/api/v1/plugins/``, and the manifest api's plugin kinds.

   A plugin's manifest kind is its class, e.g. ``ApiPlugin`` or ``SqlPlugin``. :meth:`apply`
   accepts any of them, and :meth:`describe` and :meth:`delete` look the kind up by name.

   .. py:method:: apply(manifest: 'ManifestInput') -> 'SmarterJournalMessage'

      Create or update a plugin from its manifest, of any plugin kind.

      :param manifest: The manifest.
      :returns: The platform's response.
      :raises SmarterValueError: If the manifest is not a plugin's.


   .. py:method:: kind_of(name: 'str') -> 'str'

      A plugin's manifest kind.

      :param name: The plugin's name.
      :returns: e.g. ``SqlPlugin``.


   .. py:method:: describe(name: 'str') -> 'Manifest'

      A plugin's manifest, with its read-only ``status``.

      :param name: The plugin's name.
      :returns: The manifest.


   .. py:method:: delete(name: 'str') -> 'SmarterJournalMessage'

      Permanently delete a plugin.

      :param name: The plugin's name.
      :returns: The platform's response.


   .. py:method:: retrieve(id: 'SmarterIdType') -> 'Manifest'

      One plugin's manifest, by the plugin's id.

      The platform serves this only when its ``ALLOW_API_GET`` waffle switch is on. Otherwise it
      answers 405: use :meth:`find` or :meth:`describe` instead.

      :param id: The plugin's id.
      :returns: The plugin's manifest, whose ``kind`` is the plugin's, e.g. ``SqlPlugin``.



.. py:class:: Orchestrators

   Bases: :class:`smarter.resources.base.SmarterKindResource`

   Orchestrators: ``/api/v1/orchestrators/``, and the manifest api's ``Orchestrator`` kind.


.. py:class:: Vectorsearches

   Bases: :class:`smarter.resources.base.SmarterKindResource`

   Vectorsearches: ``/api/v1/vectorsearches/``, and the manifest api's ``Vectorsearch`` kind.


``smarter.resources.accounts``
------------------------------

.. py:module:: smarter.resources.accounts

Accounts, their users, and their contacts: ``/api/v1/accounts/``.

Only superusers may read them: the platform refuses other users with a 403.

Users and accounts are created and changed with manifests (the ``User`` and ``Account`` kinds):
see :class:`smarter.resources.manifests.Manifests`.

.. py:class:: Users

   Bases: :class:`smarter.resources.base.SmarterAPIResource`

   The users of the api key's account: ``/api/v1/accounts/users/``.

   .. py:method:: list() -> 'list[User]'

      The users that the api key's user may read.

      :returns: The users.


   .. py:method:: retrieve(id: 'SmarterIdType') -> 'User'

      A user, by id.

      :param id: The user's id.
      :returns: The user.



.. py:class:: UserProfiles

   Bases: :class:`smarter.resources.base.SmarterAPIResource`

   Each user's membership of an account: ``/api/v1/accounts/user-profiles/``.

   .. py:method:: list() -> 'list[UserProfile]'

      The user profiles that the api key's user may read.

      :returns: The user profiles.


   .. py:method:: retrieve(id: 'SmarterIdType') -> 'UserProfile'

      A user profile, by id.

      :param id: The user profile's id.
      :returns: The user profile.



.. py:class:: AccountContacts

   Bases: :class:`smarter.resources.base.SmarterAPIResource`

   The contacts of the api key's account: ``/api/v1/accounts/contacts/``.

   .. py:method:: list() -> 'list[AccountContact]'

      The account's contacts.

      :returns: The contacts.


   .. py:method:: retrieve(id: 'SmarterIdType') -> 'AccountContact'

      A contact, by id.

      :param id: The contact's id.
      :returns: The contact.



.. py:class:: Accounts(client: 'Smarter') -> 'None'

   Bases: :class:`smarter.resources.base.SmarterKindResource`

   Accounts: ``/api/v1/accounts/``, and the manifest api's ``Account`` kind.


``smarter.resources.history``
-----------------------------

.. py:module:: smarter.resources.history

The history of chat sessions, tool calls and plugin uses: ``/api/v1/prompts/history/``, and the Smarter Journal.

.. py:class:: PromptHistory

   Bases: :class:`smarter.resources.base.SmarterAPIResource`

   The chat sessions of the api key's user, and their tool calls and plugin uses, newest first.

   An account admin also reads the sessions of their account's users, and a superuser every session.

   .. py:method:: sessions() -> 'list[PromptSession]'

      The chat sessions.

      :returns: The sessions.


   .. py:method:: session(id: 'SmarterIdType') -> 'PromptSession'

      A chat session, by id.

      :param id: The session's id.
      :returns: The session.


   .. py:method:: tool_calls() -> 'list[PromptToolCall]'

      The tool calls of the chat sessions, with the LLM requests that made them.

      :returns: The tool calls.


   .. py:method:: tool_call(id: 'SmarterIdType') -> 'PromptToolCall'

      A tool call, by id.

      :param id: The tool call's id.
      :returns: The tool call.


   .. py:method:: plugin_usage() -> 'list[PromptPluginUsage]'

      The plugin uses of the chat sessions.

      :returns: The plugin uses.


   .. py:method:: plugin_use(id: 'SmarterIdType') -> 'PromptPluginUsage'

      A plugin use, by id.

      :param id: The plugin use's id.
      :returns: The plugin use.



.. py:class:: Journal

   Bases: :class:`smarter.resources.base.SmarterAPIResource`

   The Smarter Journal: a record of every journaled api request and response.

   Superusers only.

   Each entry's request document holds the caller's headers, including their api key, so only
   superusers may read the journal.

   .. py:method:: list(*, page: 'int' = 1, page_size: 'int | None' = None, search: 'str | None' = None, ordering: 'str | None' = None) -> 'JournalPage'

      One page of the journal's entries, newest first, without their request and response documents.

      :param page: The page number, from 1.
      :param page_size: Entries per page, or None for the platform's default.
      :param search: Only entries whose key, thing or command contains this text.
      :param ordering: A sort field, e.g. ``createdAt`` or ``-statusCode``.
      :returns: The page, and its pagination.


   .. py:method:: retrieve(key: 'str') -> 'JournalEntry'

      A journal entry, with its request and response documents.

      :param key: The entry's key: the ``metadata.key`` of a journaled response.
      :returns: The entry.



``smarter.resources.providers``
-------------------------------

.. py:module:: smarter.resources.providers

LLM providers and their models: ``/api/v1/providers/``.

.. py:class:: Providers

   Bases: :class:`smarter.resources.base.SmarterAPIResource`

   The LLM providers that the platform is configured for, e.g. openai or anthropic.

   .. py:method:: list() -> 'list[Provider]'

      The providers.

      :returns: The providers.


   .. py:method:: retrieve(name: 'str') -> 'Provider'

      A provider, by name.

      :param name: The provider's name, e.g. ``openai``.
      :returns: The provider.


   .. py:method:: models(name: 'str') -> 'list[ProviderModel]'

      A provider's models.

      :param name: The provider's name.
      :returns: The models.



``smarter.resources.proxies``
-----------------------------

.. py:module:: smarter.resources.proxies

Proxies: authenticated passthrough access to LLM providers' own apis.

The platform holds the provider's api key, and callers use their Smarter api key instead. The
easiest way to call a proxy is with the provider's own SDK:

.. code-block:: python

    from openai import OpenAI
    from smarter import Smarter

    smarter = Smarter()
    openai = OpenAI(base_url=smarter.proxies.base_url("openai"), api_key=smarter.api_key)

.. py:class:: Proxies

   Bases: :class:`smarter.resources.base.SmarterAPIResource`

   Proxies: ``/api/v1/proxy/``.

   The platform serves these endpoints only when ``SMARTER_ENABLE_PROXY`` is true.

   .. py:method:: list() -> 'list[Proxy]'

      The proxies that the user may call.

      :returns: The proxies.


   .. py:method:: base_url(name: 'str') -> 'str'

      A proxy's base url, for the provider's own SDK.

      :param name: The proxy's name, e.g. ``openai``.
      :returns: e.g. ``https://platform.smarter.sh/api/v1/proxy/openai/``.


   .. py:method:: request(name: 'str', path: 'str', *, method: 'str' = 'POST', json: 'SmarterJsonType' = None, params: 'Mapping[str, QueryParamValue] | None' = None) -> 'SmarterJsonType'

      Send a request to a provider's api, through its proxy.

      :param name: The proxy's name, e.g. ``openai``.
      :param path: The provider api's path, e.g. ``v1/chat/completions``. It must be one of the proxy's ``allowed_paths``.
      :param method: The http method.
      :param json: The JSON body, as the provider's api expects it.
      :param params: Query parameters.
      :returns: The provider's JSON response.
