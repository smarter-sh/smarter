Smarter Chat
============

Smarter Chat is Smarter's chat user interface: a React component that holds a conversation with an
:doc:`LLMClient <../smarter-resources/smarter-llmclient>`. It renders the LLMClient's welcome message
and example prompts, sends each new message to the LLMClient's prompt api, shows the prompt's
progress while the LLM calls tools, plugins and MCP servers, and renders the response as GitHub
flavored markdown, with highlighted code, LaTeX math and Mermaid diagrams. An optional Console beside
the chat shows the LLMClient's configuration, the chat session's api calls, tool calls and plugin
usage, and a live stream of your server logs.

.. raw:: html

  <img src="https://cdn.smarter.sh/images/smarter-chat-ui-example.png"
      style="width: 100%; height: auto; display: block; margin: 0 0 1.5em 0; border-radius: 0;"
      alt="Smarter Chat in the prompt engineering workbench"/>

Smarter Chat has two lives:

- **In the web console**, it is the prompt engineering workbench, the page where you chat with an
  LLMClient before you deploy it. It is one of the React apps that Django hosts, built and served
  exactly as the others are (see :doc:`Django-React Integration <developer-reference/react-integration>`).
- **On any other web page**, it is the npm package
  `@smarter.sh/ui-chat <https://www.npmjs.com/package/@smarter.sh/ui-chat>`__, so that a marketing
  site, a customer portal, a storefront or your own application can use a deployed LLMClient as its
  chat backend: as a React component, or as an embed script, one ``<script>`` tag that needs no
  build.

Both are the same code, the package in the Smarter repository's React workspace,
`smarter/react/packages/smarter.sh-chat <https://github.com/smarter-sh/smarter/tree/main/smarter/react/packages/smarter.sh-chat>`__,
which is released to npm with each Smarter release, under the platform's version.


Where to Start
--------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - If you are...
     - Read
   * - Anyone who wants to know what the chat does
     - :doc:`Features <smarter-chat/features>`
   * - A prompt engineer who wants the chat to wear a brand: logo, colors, fonts, background
     - :doc:`Styling Your LLMClient's Chat <../smarter-resources/llmclient/styles>`
   * - Adding a Smarter chatbot to your own website or application
     - :doc:`Embedding Smarter Chat <smarter-chat/embedding>`, then the
       `README <https://github.com/smarter-sh/smarter/blob/main/smarter/react/packages/smarter.sh-chat/README.md>`__ for a quick reference
   * - Adding it to a WordPress, Drupal, Shopify or documentation site, or with Google Tag Manager
     - The plugin's page: :doc:`WordPress <smarter-wordpress>`, :doc:`Drupal <smarter-drupal>`,
       :doc:`Shopify <smarter-shopify>`, :doc:`Google Tag Manager <smarter-gtm>`,
       :doc:`documentation sites <smarter-docs-sites>`
   * - Writing React code in Smarter Chat, for the web console or the npm package
     - :doc:`Developing Smarter Chat <smarter-chat/development>`, then
       :doc:`How the Web Console Hosts It <smarter-chat/web-console-hosting>`
   * - A backend developer changing anything in ``smarter.apps`` that the chat reads or calls:
       LLMClients, prompts, plugins, providers, MCP clients, CORS or authentication
     - :doc:`The Chat API Contract <smarter-chat/api-contract>`, then
       :doc:`How the Web Console Hosts It <smarter-chat/web-console-hosting>`


.. toctree::
   :maxdepth: 2
   :caption: Smarter Chat

   smarter-chat/features
   smarter-chat/embedding
   smarter-chat/development
   smarter-chat/web-console-hosting
   smarter-chat/api-contract
   smarter-chat/technical-reference


See Also
--------

- https://www.npmjs.com/package/@smarter.sh/ui-chat
- https://github.com/smarter-sh/smarter/tree/main/smarter/react/packages/smarter.sh-chat
- :doc:`Smarter LLMClient <../smarter-resources/smarter-llmclient>`
- :doc:`Smarter Prompt <../smarter-resources/smarter-prompt>`
