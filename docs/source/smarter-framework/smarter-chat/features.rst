Features
========

This page describes what Smarter Chat does, as its users see it. The same component runs in the
web console's prompt engineering workbench and on any page that embeds the
`@smarter.sh/ui-chat <https://www.npmjs.com/package/@smarter.sh/ui-chat>`__ npm package. Features
that only the workbench turns on by default are marked as such.


The Chat
--------

When it loads, the chat fetches its LLMClient's configuration, which gives it everything it
displays before the first prompt: the LLMClient's app name and version, its LLM provider and model,
the number of plugins it has, the placeholder text of the message box, the assistant's name, the
welcome message, and the example prompts, which the LLMClient's manifest declares (``appName``,
``appAssistant``, ``appWelcomeMessage``, ``appExamplePrompts``, ``appPlaceholder``).

The header shows the title, with a green check if the LLMClient is valid (a red cross if it is
not), and a rocket if it is deployed, or "(sandbox)" if it is not. Below the title is the
provider and model, for example ``openai gpt-4o-mini with 3 additional plugins``.

Chat sessions persist. The configuration includes the chat session's history, so reloading the
page restores the conversation. Each chat session has a 64-character key, which the chat saves in a
cookie for the page's path, so that each LLMClient's page keeps its own session. The **new chat**
button, a blank page, discards the key and starts a new session.

If the LLMClient allows file attachments (``appFileAttachment`` in its manifest), the message box
has an attach button, which sends the text of a ``.py``, ``.txt``, ``.md``, ``.json``, ``.yaml``,
``.yml`` or ``.csv`` file as a message.


Prompt Progress
---------------

A prompt can take a while: the LLM may call tools, plugins and MCP servers, and each tool call adds
another round trip to the LLM. While a prompt runs, the chat displays each step as it happens:

- each request to the LLM: "Sending the prompt to the LLM", then "Sending the tool results to the
  LLM" for each later round trip,
- each tool the LLM calls, and its response,
- each plugin that runs,
- each MCP server tool that is called, responds or fails.

The typing indicator names the current step, for example "Stanley: Calling tool stackademy_sql".
When the response arrives, it replaces the steps. In production mode, only the typing indicator
names the steps. Progress is streamed from the server as
Server-Sent Events. See :doc:`The Chat API Contract <api-contract>`.


Errors
------

A failed prompt, for example one that the LLM provider rejects because of a bad api key or a rate
limit, is displayed in the thread as an error message, with the provider's own error text. A
configuration that can't be loaded, for example because the LLMClient doesn't exist or the user may
not use it, is displayed the same way, and the header reads "Smarter Chat is not available".

When the LLM stops because it reached the LLMClient's maximum number of tokens, the chat says so,
and suggests raising ``defaultMaxTokens`` in the LLMClient's manifest. This matters most for
reasoning models, which can spend all of their tokens reasoning and return an empty response that
would otherwise display as nothing at all.


Sandbox Mode and Production Mode
--------------------------------

*In the workbench. The npm package's chat has it with the* ``toggleMetadata`` *prop, and the embed
script's is always in production mode.*

The **Sandbox mode / Production mode** button shows and hides the backend's own messages in the
thread: the system prompt, tool results, Smarter's notes, for example about the plugins it selected
and the tokens it charged, and the prompt's progress. In production mode, the thread is the
conversation as the LLMClient's users see it, and the Console and the button that shows and hides
it are hidden too. Switching back to sandbox mode restores the Console as you left it.

The Console's Server Logs tab shows the server logs of its own chat session: the records of the
requests that carry the chat's session key, so that other chats, and other work on your account,
stay out of it. A new chat has a new session key, and its Server Logs tab starts empty. The tab
follows the mode: in sandbox mode it streams every log record of the chat, DEBUG
included, and in production mode only the records at the platform's log level
(``smarter_settings.log_level``) and above. Switching modes reconnects the stream, which replays
the recent history at the new level.

In the workbench, sandbox mode also adds a **Docs** button to the chat's toolbar. It opens a dialog of links to the
technical references, on two tabs. The **Prompt Engineer** tab, which is selected when the dialog
opens, is for those who build LLMClients in the sandbox: this Smarter Chat documentation and the
LLMClient, Plugin, Guardrail and Budget references. The **Software Engineer** tab is for those who
build the applications that host them: the
`@smarter.sh/ui-chat <https://www.npmjs.com/package/@smarter.sh/ui-chat>`__ npm package, the chat
api, and the React integration guide. The links open in a new tab.


How Messages Are Rendered
-------------------------

The LLM's responses, and the backend's messages, are GitHub flavored markdown: headings, bold,
italics, strikethrough, lists, tables, block quotes, inline code, fenced code blocks, links and
images. A line break is a line break, as in any chat. The LLM is told so: Smarter adds a note to
the system prompt of each request it sends to an OpenAI-compatible provider, which is not saved in
the chat session's history. Your own messages are displayed as you typed them, except for their
links and images.

Links and images
  Raw html is displayed as text. ``![alt](url)`` is an image, scaled to fit its chat bubble, which
  opens at full size in a new tab, and ``[![alt](url)](href)`` is an image that links to ``href``.
  Links open in a new tab. Urls must be ``http(s)`` or relative to the page. Images may also be
  base64 ``png``, ``jpeg``, ``gif`` or ``webp`` data urls, for example from a tool that generates
  them. Anything else, such as a ``javascript:`` url, stays as text.

Code
  Fenced code blocks are syntax highlighted, in GitHub's dark theme, with a header that names the
  language and a **Copy** button. Highlighting covers the common languages (Python, JavaScript,
  TypeScript, Bash, JSON, YAML, SQL, Go, Rust, Java, C, C++, C#, HTML, CSS and more), plus
  Dockerfile, nginx and PowerShell.

Math
  Math, written in LaTeX, is typeset by `KaTeX <https://katex.org>`__: ``\( ... \)`` is inline math,
  and ``\[ ... \]`` or ``$$ ... $$`` is an equation displayed on a line of its own, which scrolls
  sideways if it is wider than its chat bubble. A single dollar sign is not math, so prices stay as
  text. Math in inline code and code blocks stays as code, and LaTeX that KaTeX cannot typeset, such
  as an equation that is still streaming, is displayed as its source. Screen readers read the
  equation's MathML.

Diagrams
  A fenced code block whose language is ``mermaid`` is drawn as a
  `Mermaid <https://mermaid.js.org>`__ diagram, such as a flowchart or a sequence diagram, whose
  **Code** button shows its source instead, and back. A diagram that Mermaid cannot draw, for example
  because of a syntax error, stays as its code. Mermaid is large, so it is downloaded only when a
  message first has a diagram. It runs at its ``strict`` security level, with plain text labels, and
  its svg is sanitized again before it is displayed, because the diagram comes from the LLM.

All of the html that the chat renders from messages is sanitized with
`DOMPurify <https://github.com/cure53/DOMPurify>`__, so nothing in a message can run a script.


Languages
---------

The chat's own text, such as its buttons, its labels, the "is typing" indicator and the errors that
it displays, is in English, Spanish, French or Brazilian Portuguese, the same languages as the web
console. It uses the
language that the page that hosts it asks for (the ``language`` prop, or the embed script's
``language`` option), or else the page's own language, from its ``<html lang>`` attribute, or else
the browser's. In the workbench, that is the language that you chose in the web console's user
menu. A regional variant gets its language (``es-MX`` gets Spanish, which is Latin American
Spanish, and ``pt`` or ``pt-PT`` gets Brazilian Portuguese), and any other language gets English.

The LLMClient's own text, which its manifest sets (its name, welcome message, example prompts and
placeholder), is displayed as it is, and so is the conversation: write them in your users'
language, and the LLM answers in the language that it is asked in. The Console's JSON, its
simulated terminal, and Smarter's progress messages are in English.



The Console
-----------

*Only in the workbench, whose own app,* ``@smarter/workbench``, *puts it beside the chat. The npm
package and the embed script have no Console.*

The Console is a simulated terminal beside the chat. Its tabs follow a prompt engineer's work, from
left to right: the LLMClient's manifest, which each change starts with, the chat session's server logs
and tool calls, which show what a prompt did, its configuration, as JSON, and the LLMClient's
deployment:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Tab
     - Contents
   * - Manifest
     - The LLMClient's YAML manifest, in the web console's manifest editor, which validates it as you
       type, and saves, clones and deletes the LLMClient with your own permissions. When you save,
       the chat reloads the LLMClient's configuration, so that the next prompt uses your changes, and
       the chat session carries on. The editor loads when you first
       open it, then keeps your unsaved changes while you look at the other tabs. If you delete the
       LLMClient, the workbench, whose LLMClient is gone, takes you to the LLM Clients list. The tab is
       the far left one, where each change to the LLMClient starts.
   * - Architecture
     - How the LLMClient is built: the tree of the SAM resources that it uses, such as its Provider, its
       plugins, MCPClients and Guardrails, and beneath them, what those use in turn, such as Connections
       and Secrets. Each resource is a card with its kind's icon, its name and its owner, and clicking it
       opens the resource's manifest page, where its manifest can be edited, in a new tab. A short
       introduction explains SAM resources and their manifests, and each kind links to its page in this
       documentation. Each resource that uses others can be collapsed, **Collapse all** and **Expand all**
       do it for every one, and **Reload** fetches the tree again, after a manifest was changed in
       another tab. A resource that you may not read, such as another account's, is a locked card with
       only its kind and record locator. The tab is right of Manifest, and loads when you first open it.
   * - Server Logs
     - The chat session's server logs, as they stream in, in the colors and font of the web console's log viewer.
       Long lines scroll horizontally, or wrap, with the tab's **Wrap lines** button. Blocks of
       pretty-printed JSON, such as a prompt's request and response, are collapsed to their first
       line and their length: each block's **+** button expands it, and **Expand JSON** expands or
       collapses all of them. Copying the lines copies the JSON in full. The tab is right of Architecture. Present only
       when log viewing in the browser is enabled (``SMARTER_ENABLE_DASHBOARD_SERVER_LOGS``), and
       then selected when the Console opens. A new chat clears it.
   * - Tool Calls
     - The chat session's tool calls, each collapsed to its function's name: click one to see its
       request and response.
   * - Config
     - The LLMClient's complete configuration, as the config api returns it with ``?verbose=true``,
       collapsed to its top-level keys.
   * - Deployment
     - What the prompt engineer needs once the LLMClient is deployed: its status and url, the ways
       to put its chat on a web site (WordPress, Drupal, Shopify, React from npm, and any html page),
       how to secure its url with an api key, how the url works, with curl commands and an example
       response, how chat sessions carry a conversation across page loads, and its manifest. Its api key section lists the account's api keys, creates one,
       showing its secret once, and attaches it to the LLMClient or detaches it. An LLMClient that
       isn't deployed gets the url that it will have, and the command that deploys it. The tab is the
       far right one, and the page loads when you first open it, whatever the
       ``enable_llmclient_endpoints_page`` waffle switch.

The Tool Calls and Config tabs display the configuration's diagnostic parts, which are costly for
the platform to build, and grow with the chat session. The chat fetches them only while one of these
tabs is selected and the Console is visible, and again after each prompt while it still is. The rest
of the time, and in production mode, the chat fetches only what it needs, once per page load.

Drag the separator between the chat and the Console to resize them, or focus it and use the arrow
keys. The chat takes between 20% and 80% of the width, a third by default. The panel button in the
chat's header hides the Console, which slides out to the right, and back. The browser remembers the
width, whether the Console is visible, and whether log lines wrap.
