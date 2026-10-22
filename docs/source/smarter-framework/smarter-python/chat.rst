Prompts and Chat
================

An :doc:`LLMClient <../../smarter-resources/smarter-llmclient>` is prompted through its prompt API,
the same API that :doc:`Smarter Chat <../smarter-chat>` uses. The platform runs the whole prompt: it
selects plugins, calls the LLM, runs the tools that the LLM calls, applies the
:doc:`Guardrails <../../smarter-resources/smarter-guardrail>`, and saves the chat session's history.
Your code receives the result.

The SDK always reads version 2 of the :doc:`Smarter Chat API contract <../smarter-chat/api-contract>`,
whose models are in :mod:`smarter.models.chat`.

One prompt
----------

.. code-block:: python

   from smarter import Smarter

   client = Smarter()
   llmclient = client.llm_clients.find("calculator")

   response = client.llm_clients.prompt(llmclient.id, "What is 17 times 23?")
   print(response.text)                 # the LLM's final reply
   for message in response.data.messages:
       print(message.role, message.text)

``response.data.messages`` is every message that the prompt added to the thread, in order: the
assistant's tool calls, the tools' results, the reply, and Smarter's own informational messages
(role ``smarter``), such as the prompt's configuration and its token charges. ``response.data.completion``
is the LLM's chat completion, with its token usage.

An LLMClient is identified by its id or its hashed id. ``find(name)`` looks one up by name.

A conversation
--------------

``chat()`` starts a chat session and keeps it: each ``send()`` sends the whole thread, with the
session's key, and adds the prompt's messages to the thread. The platform saves the session's
history, so a session can be resumed later, even from another process.

.. code-block:: python

   chat = client.llm_clients.chat(llmclient.id)
   print(chat.send("What is 2 to the 10th power?").text)
   print(chat.send("And divided by 4?").text)

   key = chat.session_key                       # save it to resume the session later
   resumed = client.llm_clients.chat(llmclient.id, session_key=key)
   print(len(resumed.messages))

A new session's thread starts with the LLMClient's system prompt and welcome message, exactly as
Smarter Chat starts one. Only the roles that LLM providers accept (``system``, ``user``,
``assistant`` and ``tool``) are sent. Smarter's own messages stay in the thread for you to read.

A chat's configuration
----------------------

``config()`` returns the configuration that a chat starts from: the LLMClient, the session's key and
chat history, the LLMClient's state in ``meta_data``, and the counts of its plugins and extensions.
``verbose=True`` adds the parts that the workbench's Console shows: the lists of plugins and extensions,
the session's tool calls (``history.prompt_tool_call_history``) and the complete ``meta_data``. A
deployed LLMClient's own host leaves them out either way.

.. code-block:: python

   config = client.llm_clients.config(llmclient.id, verbose=True)
   print([plugin.plugin_meta.name for plugin in config.plugins.plugins])

Streaming a prompt's progress
-----------------------------

A prompt that calls tools can take a while. ``stream()`` reports its progress while it runs: each
LLM request, tool call, plugin call and MCP call. When the stream ends, ``stream.response`` is the
same response that ``prompt()`` returns.

.. code-block:: python

   with client.llm_clients.stream(llmclient.id, "What is sin(pi / 2)?") as stream:
       for event in stream:
           print("...", event.message)       # e.g. "Calling tool calculator"
   print(stream.response.text)

   with chat.stream("Now take its square root.") as stream:
       for event in stream:
           print("...", event.message)
   print(stream.response.text)              # and the chat's thread is updated

The progress is streamed as Server-Sent Events, and the platform sends the reply once it is
complete: the reply's text itself is not streamed token by token.

Failed prompts
--------------

When the LLM provider rejects a prompt, the prompt API answers with the provider's status, and the
SDK raises the matching :doc:`exception <errors>`, e.g. a ``BadRequestError``, whose ``body`` is the
error response. A failed stream raises ``SmarterPromptError`` when you read its ``response``. In
both cases the session's history keeps a ``smarter_error`` message, and a chat's thread is left
unchanged.

Prompts are billed by the LLM provider, to the account of the provider's API key on your platform.
