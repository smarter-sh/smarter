Prompts and Chat
================

An :doc:`LLMClient <../../smarter-resources/smarter-llmclient>` is prompted through its prompt API,
the same API that :doc:`Smarter Chat <../smarter-chat>` uses. The platform runs the whole prompt: it
selects plugins, calls the LLM, runs the tools that the LLM calls, applies the
:doc:`Guardrails <../../smarter-resources/smarter-guardrail>`, and saves the chat session's history.
Your code receives the result.

The SDK always reads version 2 of the :doc:`Smarter Chat API contract <../smarter-chat/api-contract>`,
whose Zod schemas are exported as ``PromptChatApiConfig``, ``PromptChatApiPromptResponse``, and so
on. Their fields are the contract's own names, e.g. ``session_key``.

One prompt
----------

.. code-block:: typescript

   import { Smarter, messageText } from "@smarter.sh/api";

   const client = new Smarter();
   const llmclient = await client.llmClients.find("calculator");

   const response = await client.llmClients.prompt(llmclient.id, "What is 17 times 23?");
   console.log(response.text); // the LLM's final reply
   for (const message of response.data.messages) console.log(message.role, messageText(message));

``response.data.messages`` is every message that the prompt added to the thread, in order: the
assistant's tool calls, the tools' results, the reply, and Smarter's own informational messages
(role ``smarter``), such as the prompt's configuration and its token charges.
``response.data.completion`` is the LLM's chat completion, with its token usage. ``text`` is a
convenience getter: ``JSON.stringify(response)`` is exactly the platform's JSON.

An LLMClient is identified by its id or its hashed id. ``find(name)`` looks one up by name.

A conversation
--------------

``chat()`` starts a chat session and keeps it: each ``send()`` sends the whole thread, with the
session's key, and adds the prompt's messages to the thread. The platform saves the session's
history, so a session can be resumed later, even from another process.

.. code-block:: typescript

   const chat = await client.llmClients.chat(llmclient.id);
   console.log((await chat.send("What is 2 to the 10th power?")).text);
   console.log((await chat.send("And divided by 4?")).text);

   const key = chat.sessionKey; // save it to resume the session later
   const resumed = await client.llmClients.chat(llmclient.id, { sessionKey: key });
   console.log(resumed.messages.length);

A new session's thread starts with the LLMClient's system prompt and welcome message, exactly as
Smarter Chat starts one. Only the roles that LLM providers accept (``system``, ``user``,
``assistant`` and ``tool``) are sent. Smarter's own messages stay in the thread for you to read.

Streaming a prompt's progress
-----------------------------

A prompt that calls tools can take a while. ``stream()`` reports its progress while it runs: each
LLM request, tool call, plugin call and MCP call. Read it with ``for await``. When the loop ends,
``stream.response`` is the same response that ``prompt()`` returns.

.. code-block:: typescript

   const stream = client.llmClients.stream(llmclient.id, "What is sin(pi / 2)?");
   for await (const event of stream) console.log("...", event.message); // e.g. "Calling tool calculator"
   console.log(stream.response.text);

   const chatStream = chat.stream("Now take its square root.");
   for await (const event of chatStream) console.log("...", event.message);
   console.log(chatStream.response.text); // and the chat's thread is updated

The request is sent when the loop starts, and its connection is closed when the loop ends, also
when you ``break`` out of it. ``await stream.untilDone()`` reads a stream to its end and returns its
response. The progress is streamed as Server-Sent Events, and the platform sends the reply once it
is complete: the reply's text itself is not streamed token by token.

Failed prompts
--------------

When the LLM provider rejects a prompt, the prompt API answers with the provider's status, and the
SDK throws the matching :doc:`error <errors>`, e.g. a ``BadRequestError``, whose ``body`` is the
error response. A failed stream throws ``SmarterPromptError`` when you read its ``response``. In
both cases the session's history keeps a ``smarter_error`` message, and a chat's thread is left
unchanged.

Prompts are billed by the LLM provider, to the account of the provider's API key on your platform.
