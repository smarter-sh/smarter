Prompts and Chat
================

An :doc:`LLMClient <../../smarter-resources/smarter-llmclient>` is prompted through its prompt API,
the same API that :doc:`Smarter Chat <../smarter-chat>` uses. The platform runs the whole prompt: it
selects plugins, calls the LLM, runs the tools that the LLM calls, applies the
:doc:`Guardrails <../../smarter-resources/smarter-guardrail>`, and saves the chat session's history.
Your code receives the result.

The SDK always reads version 2 of the :doc:`Smarter Chat API contract <../smarter-chat/api-contract>`,
whose structs are ``smarter.PromptChatAPIConfig``, ``smarter.PromptChatAPIPromptResponse``, and so on.

One prompt
----------

A prompt is a chat thread, a ``[]smarter.PromptChatAPIMessage``. ``smarter.Text`` makes one of a
single user message.

.. code-block:: go

   llmclient, err := client.LLMClients.Find(ctx, "calculator")
   if err != nil {
       return err
   }
   response, err := client.LLMClients.Prompt(ctx, llmclient.Ref(), smarter.Text("What is 17 times 23?"), nil)
   if err != nil {
       return err
   }
   fmt.Println(response.Text()) // the LLM's final reply
   for _, message := range response.Data.Messages {
       fmt.Println(message.Role, message.Text())
   }

``response.Data.Messages`` is every message that the prompt added to the thread, in order: the
assistant's tool calls, the tools' results, the reply, and Smarter's own informational messages
(role ``smarter``), such as the prompt's configuration and its token charges.
``response.Data.Completion`` is the LLM's chat completion, with its token usage.

An LLMClient is identified by a ``smarter.ID``: ``smarter.IntID(5)``, a hashed id such as
``smarter.ID("rMTAwMDAwNQx")``, or a resource's ``Ref()``. ``Find`` looks one up by name.

A conversation
--------------

``Chat`` starts a chat session and keeps it: each ``Send`` sends the whole thread, with the
session's key, and adds the prompt's messages to the thread. The platform saves the session's
history, so a session can be resumed later, even from another process.

.. code-block:: go

   chat, err := client.LLMClients.Chat(ctx, llmclient.Ref(), nil)
   if err != nil {
       return err
   }
   reply, err := chat.Send(ctx, "What is 2 to the 10th power?")
   if err != nil {
       return err
   }
   fmt.Println(reply.Text())

   key := chat.SessionKey() // save it to resume the session later
   resumed, err := client.LLMClients.Chat(ctx, llmclient.Ref(), &smarter.PromptParams{SessionKey: key})
   if err != nil {
       return err
   }
   fmt.Println(len(resumed.Messages))

A new session's thread starts with the LLMClient's system prompt and welcome message, exactly as
Smarter Chat starts one. Only the roles that LLM providers accept (``system``, ``user``,
``assistant`` and ``tool``) are sent. Smarter's own messages stay in the thread for you to read. A
chat session is not safe for concurrent use.

Streaming a prompt's progress
-----------------------------

A prompt that calls tools can take a while. ``Stream`` reports its progress while it runs: each LLM
request, tool call, plugin call and MCP call. Read it like a ``bufio.Scanner``, and close it. When
``Next`` returns false, ``Response`` is the same response that ``Prompt`` returns.

.. code-block:: go

   stream := client.LLMClients.Stream(ctx, llmclient.Ref(), smarter.Text("What is sin(pi / 2)?"), nil)
   defer stream.Close()
   for stream.Next() {
       fmt.Println("...", stream.Current().Message) // e.g. "Calling tool calculator"
   }
   response, err := stream.Response() // the stream's error, if it failed
   if err != nil {
       return err
   }
   fmt.Println(response.Text())

``chat.Stream(ctx, "...")`` streams a conversation's prompt, and updates the chat's thread when the
stream has been read. ``stream.UntilDone()`` reads a stream to its end and returns its response. The
progress is streamed as Server-Sent Events, and the platform sends the reply once it is complete:
the reply's text itself is not streamed token by token.

Failed prompts
--------------

When the LLM provider rejects a prompt, the prompt API answers with the provider's status, and the
SDK returns the matching :doc:`error <errors>`, e.g. one that matches ``smarter.ErrBadRequest``,
whose ``Body`` is the error response. A failed stream's ``Response`` returns a
``*smarter.PromptError``. In both cases the session's history keeps a ``smarter_error`` message, and
a chat's thread is left unchanged.

Prompts are billed by the LLM provider, to the account of the provider's API key on your platform.
