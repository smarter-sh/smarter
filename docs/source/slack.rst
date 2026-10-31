Smarter on Slack
================

Welcome to The Smarter Project's Slack workspace. Besides the people here, the workspace has a bot,
**@Smarter Developer**, that answers questions about Smarter at any hour. This page explains what
it knows, how to talk to it, and what to expect from it.

If you aren't in the workspace yet, join with this
`invite link <https://join.slack.com/t/thesmarterproject/shared_invite/zt-4f0t6v46q-e2c5Of4hS4fBr_XwfQARCw>`__.

What the Bot Is
---------------

@Smarter Developer is ``smarter_developer``, one of the example
:doc:`LLMClients <smarter-resources/smarter-llmclient>` that every Smarter platform ships with,
running on The Smarter Project's own platform. It acts as a staff engineer of the project, for
people who want to understand, use, extend or contribute to Smarter.

It answers from the :doc:`Smarter Project MCP Server <smarter-platform/smarter-project-mcp-server>`,
not from memory. For each question it searches and reads the source code and documentation of
every public repository of the `smarter-sh <https://github.com/smarter-sh>`__ GitHub organization,
which include the platform, the command-line interface, the Python, Node.js and Go SDKs, the VS
Code extension, Smarter Chat and its integrations, the cloud infrastructure, the example manifests
and the extensions. It also reads the project's blog, `blog.smarter.sh <https://blog.smarter.sh>`__.
So its answers follow the current code, and it links to the files, documentation pages and blog
posts that it used.

It's the same agent that answers in the chat window on `smarter.sh <https://smarter.sh>`__.

Talking to the Bot
------------------

In a channel
~~~~~~~~~~~~

Mention the bot at the start of your message:

.. code-block:: text

   @Smarter Developer How does Smarter keep API keys out of its logs?

The bot answers in a thread under your message. To ask a follow-up, reply in that thread and
**mention the bot again**. It reads only the messages that mention it, so a reply without the
mention is a message for the people in the thread, not for the bot. Everything you ask in one
thread is one conversation: the bot remembers the earlier questions and answers in it.

To ask about something new, start a new message in the channel, which starts a new thread and a
new conversation.

The bot answers only in channels that it has been added to. If it doesn't answer in a channel,
add it with ``/invite @Smarter Developer``, or ask in a channel where it already is.

In a direct message
~~~~~~~~~~~~~~~~~~~

Open a direct message with @Smarter Developer (click its name, then **Message**), and ask. There
is no need to mention it there. A direct message is private: only you see the conversation in
Slack.

The messages you send in the conversation itself are one ongoing conversation. A thread inside the
direct message, which you start by replying to one of its messages, is a separate conversation. To
start over in the main conversation, send a message that is only one of these words:

- ``new``
- ``reset``
- ``start over``
- ``new conversation``

The bot then forgets the conversation, and answers your next question afresh. This works in a
channel thread too, but there, starting a new message is easier.

Waiting for the answer
~~~~~~~~~~~~~~~~~~~~~~

Answers usually take 10 to 30 seconds, because the bot searches and reads the code before it
answers. Slack shows nothing while it works. Ask your question once: asking again only sends a
second question.

Asking Good Questions
---------------------

The bot answers best when the question is about Smarter, specific, and complete in itself. Some
examples:

- How does Smarter keep passwords and API keys out of its logs?
- Write an MCPClient manifest for an MCP server that needs an API key.
- How do I add a Smarter chatbot to my WordPress site?
- Write me a manifest for an LLMClient that uses the Smarter Project MCP server to answer questions
  about the Smarter codebase.
- What changed in the last release of the command-line interface?
- Which file handles the deployment of an LLMClient, and what does it create in Kubernetes?
- Why does Smarter use Pydantic models for its manifests?

Tips:

- **Name what you're asking about**: a resource kind (LLMClient, Plugin, MCPClient, Guardrail,
  Secret, ...), a command, an SDK, a file or an error message.
- **Paste the error.** Paste the error message, or the few lines of a manifest that fail, in a code
  block. Leave out keys, passwords and tokens (see `Privacy`_).
- **Ask for what you want back**: an explanation, a manifest, a code example, or the files to read.
- **Ask for a link** when you want to read further. The bot links to the documentation and the code
  that it used.

The bot checks a manifest's schema before it writes one, but it can still be wrong. Check its
answer against the documentation it links to before you apply a manifest or use its code.

How Answers Look in Slack
-------------------------

The bot writes for a chat window that shows Markdown, and Slack shows less than that:

- Links, bold text, lists and code blocks look as they should.
- Headings appear as bold text.
- Images appear as links. Click them to see the picture.
- Tables and diagrams appear as plain text or code.

When you want a diagram, a table or a long answer, ask the same agent in the chat window on
`smarter.sh <https://smarter.sh>`__, which shows them in full.

Limits
------

- **It answers about The Smarter Project only.** It's not a general assistant, and it doesn't know
  about your own platform, your account or your data.
- **It can be wrong.** It answers from the code and documentation that it finds, and says when it
  finds nothing, but like any LLM it can misread them. Treat an answer as a well-informed first
  draft, and check it against the links it gives.
- **It forgets.** The bot keeps conversations in memory, so when it restarts, for example during an
  upgrade, it starts every conversation again. If it no longer remembers a thread, repeat what it
  needs to know in your question.
- **It can't act.** It reads code and documentation. It can't change your account, run commands,
  open issues or read files that you attach in Slack.
- **It's one bot for everyone.** Every answer is a real request to an LLM provider, paid for by The
  Smarter Project. Ask as many real questions as you like, but please don't automate it or use it for
  load testing.

Privacy
-------

- Your question, and the earlier questions and answers of the same conversation, are sent to The
  Smarter Project's platform and to its LLM provider. The platform records each conversation in the
  LLMClient's chat history and cost accounting, where its administrators can see it.
- A thread in a channel is visible to everyone in that channel, like any other thread. Use a direct
  message for a question that you'd rather not ask in public.
- **Never paste API keys, passwords, tokens or customer data.** The bot's
  :doc:`Guardrails <smarter-resources/smarter-guardrail>` redact secrets that they recognize in
  your question, and block them in its answer, but they can't recognize every secret, and Slack keeps
  your message either way.

When to Ask a Person
--------------------

The bot is for quick, factual questions about how Smarter works. For everything else:

- **Discussion, opinions, plans and help with your own setup**: ask the people in this workspace, or
  in the `GitHub Discussions <https://github.com/smarter-sh/smarter/discussions/>`__ forum.
- **Bugs**: open a `GitHub issue <https://github.com/smarter-sh/smarter/issues/>`__, with what you
  did, what you expected and what happened. The bot can help you find the relevant code first.
- **Security problems**: don't post them in Slack. See :doc:`smarter-platform/security`.

If the bot gives a wrong or misleading answer, tell the people in the workspace. That helps improve
both the bot and the documentation.

Troubleshooting
---------------

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - What happens
     - What to do
   * - The bot doesn't answer in a channel.
     - Check that your message mentions **@Smarter Developer**, and that the bot is in the channel.
       If it isn't, add it with ``/invite @Smarter Developer``.
   * - The bot doesn't answer a reply in a thread.
     - Mention it in the reply. Without the mention, the reply is for the people in the thread.
   * - The bot says "Hi! Ask me a question about Smarter".
     - Your message mentioned it but had no question. Ask again, with the question in the same
       message.
   * - The bot says "Sorry, I couldn't reach the Smarter agent".
     - The platform didn't answer in time, for example during an upgrade. Try again in a minute.
       If it keeps happening, say so in the workspace.
   * - The bot says "Sorry, I have no answer to that".
     - Rephrase the question, more specifically, or ask a person.
   * - The bot forgot the conversation.
     - It was restarted. Repeat what it needs to know, or start a new thread.
   * - The answer has broken formatting, a table or a diagram.
     - Ask the same question in the chat window on `smarter.sh <https://smarter.sh>`__.

Running Your Own
----------------

The bot is part of Smarter. Any Smarter platform can run it, in its own Slack workspace, with any of
its deployed LLMClients. See :doc:`smarter-framework/smarter-on-kubernetes/slack-bot`.
