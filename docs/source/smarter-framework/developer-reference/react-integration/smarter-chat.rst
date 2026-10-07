Smarter Chat
============

Smarter Chat is the React chat component of the LLMClient prompt engineering workbench, the web
console page where you chat with an :doc:`LLMClient <../../../smarter-resources/smarter-llmclient>`
before you deploy it. Beside the chat, its Console displays the LLMClient's configuration, and the
chat session's api calls, tool calls and plugin usage, as JSON. When log viewing in the browser is
enabled (``SMARTER_ENABLE_DASHBOARD_SERVER_LOGS``), the Console's Server Logs tab also streams your
server logs, the same stream as the web console's log viewer, while you chat. Drag the separator
between the chat and the Console to resize them, or hide the Console with the arrow button in the
chat's header. The browser remembers both.

A toggle shows and hides the backend's own messages in the chat thread: the system prompt, tool
results, and Smarter's notes about the plugins it selected. While a prompt runs, the chat displays
its progress: each request to the LLM, and each tool, plugin and MCP server that the LLM calls.
Those steps are replaced by the response when it arrives. A failed prompt, for example one that the
LLM provider rejects, is displayed in the chat thread, with the provider's error message.

Messages are escaped, and their markdown links and images become html. ``![alt](url)`` is an image,
scaled to fit its chat bubble, which opens at full size in a new tab, and ``[![alt](url)](href)`` is
an image that links to ``href``. Urls must be ``http(s)`` or relative to the page. Images may also be
base64 ``png``, ``jpeg``, ``gif`` or ``webp`` data urls, for example from a tool that generates them.

.. raw:: html

  <img src="https://cdn.smarter.sh/images/smarter-chat-ui-example.png"
      style="width: 100%; height: auto; display: block; margin: 0 0 1.5em 0; border-radius: 0;"
      alt="Smarter Chat Component in Workbench Mode"/>

Smarter Chat has two lives. In the web console, it is one of the React apps that Django hosts, built
and served exactly as the others are. It is also published to npm as
`@smarter.sh/ui-chat <https://www.npmjs.com/package/@smarter.sh/ui-chat>`__, so that any web page,
for example a Wordpress or Squarespace marketing site, a Salesforce portal, a Shopify storefront or
your own web application, can use a Smarter LLMClient as its chat backend.


Source Code
-----------

Smarter Chat is managed in its own repository,
`smarter-sh/smarter-chat <https://github.com/smarter-sh/smarter-chat>`__, which is where it is
versioned and published to npm. ``make react-install`` clones it into the React workspace, as
``smarter/react/packages/smarter-chat``, which Smarter's ``.gitignore`` excludes. From then on it is
a workspace package like any other: ``npm run build`` builds it, and ``make react-test`` and
``make react-lint`` test and lint it, with the same TypeScript, Vite, Vitest, Storybook, ESLint and
Prettier configuration as the other React apps.

.. code-block:: console

  make react-install                          # clones smarter-chat's main branch, if it isn't there yet
  make react-install SMARTER_CHAT_BRANCH=alpha # or another branch
  make react-storybook APP=smarter-chat       # browse its components in Storybook

An existing clone is never changed by ``make``, so work in progress in it is safe. Commit and push
changes to Smarter Chat from inside ``smarter/react/packages/smarter-chat``, which is its own git
repository. The GitHub Actions workflows clone it too, before the React build, and the React build's
cache key includes the clone's commit.


How the Web Console Hosts It
----------------------------

The :py:class:`PromptWorkbenchView <smarter.apps.prompt.views.detailviews.prompt_workbench_view.PromptWorkbenchView>`
renders ``react/smarter-chat.html``. Its ``react_smarter_chat`` template tag reads the Vite
``manifest.json`` in ``static/react/@smarter.sh/ui-chat/`` to include the app's hashed JavaScript and
CSS files, and the template renders the app's root element, whose attributes configure it:

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Attribute
     - Value
   * - ``id``
     - ``smarter-chat-root``
   * - ``smarter-llmclient-api-url``
     - The LLMClient's sandbox url. Smarter Chat appends ``config/`` for its configuration.
   * - ``smarter-toggle-metadata``
     - Whether to show the button that shows and hides the backend's messages.
   * - ``smarter-csrf-cookie-name``
     - Django's ``CSRF_COOKIE_NAME``. The chat sends the cookie's value as the ``X-CSRFToken`` header.
   * - ``smarter-session-cookie-name``
     - The cookie in which the chat saves its chat session's key, for the page's path, so that each
       LLMClient has its own chat session.
   * - ``smarter-django-session-cookie-name``
     - Django's ``SESSION_COOKIE_NAME``.
   * - ``smarter-cookie-domain``
     - Django's ``SESSION_COOKIE_DOMAIN``.
   * - ``react-debug-mode``
     - The ``ENABLE_REACTAPP_DEBUG_MODE`` waffle switch, which turns on logging to the browser console.
   * - ``smarter-request-id``
     - A unique id of the page request, sent as the ``X-Smarter-RequestId`` header.
   * - ``smarter-log-stream-url``
     - The url of the user's server log stream, or empty when log viewing in the browser is
       disabled. Without it, the Console has no Server Logs tab.

Smarter Chat then calls two apis, both with POST requests that the web console's session
authenticates:

- the LLMClient's configuration, at ``<smarter-llmclient-api-url>config/``, served by
  :py:class:`PromptConfigView <smarter.apps.prompt.views.detailviews.prompt_config_view.PromptConfigView>`.
  It includes the chat session's history, which restores the chat thread when the page reloads.
- the LLMClient's prompt api, ``chatbot.url_chatbot`` in the configuration, which receives the chat
  thread with each new message, and returns the new messages to add to it.

Streaming a Prompt's Progress
-----------------------------

The prompt api answers with JSON, unless the request's ``Accept`` header includes
``text/event-stream``, which Smarter Chat sends. Then the response is Server-Sent Events: a
``progress`` event for each step of the prompt as it happens, ``: keepalive`` comments while the
prompt waits, for example on the LLM, and finally a ``result`` event whose data is
``{"status": <http status>, "response": <the same JSON as a non-streaming response>}``. The http
status of the stream itself is always 200, and the prompt's own status is in its result.

.. code-block:: text

  event: progress
  data: {"type": "tool_requested", "message": "Calling tool get_current_weather", "tool": "get_current_weather", "arguments": "{...}"}

  event: progress
  data: {"type": "mcp_tool_called", "message": "Calling MCP server github: search_code", "mcpclient": "github", "tool": "search_code", "arguments": "{...}"}

  event: result
  data: {"status": 200, "response": {"data": {"statusCode": 200, "body": "..."}}}

The prompt itself runs synchronously in a worker thread, exactly as it does for a JSON client, so
its history, charges and journal are the same. Its progress comes from the signals that the prompt
already sends (``chat_request``, ``llm_tool_requested``, ``llm_tool_responded``,
``chat_plugin_called``, ``mcpclient_tool_called``, ...), which :py:mod:`smarter.apps.prompt.progress`
forwards to the stream of the prompt that sent them. A client that disconnects doesn't stop the
prompt, which finishes, and is saved in the chat session's history. Streaming needs Smarter's ASGI
server (uvicorn), and any proxy in front of it must not buffer the response; the stream sends
``X-Accel-Buffering: no`` for nginx.


Using Smarter Chat in Your Own Web Page
---------------------------------------

Install the npm package, then render the ``SmarterChat`` component wherever you want the chat to
appear. React 19 is a peer dependency.

.. code-block:: console

  npm install @smarter.sh/ui-chat

.. code-block:: tsx

  import { createRoot } from "react-dom/client";
  import { SmarterChat } from "@smarter.sh/ui-chat";
  import "@smarter.sh/ui-chat/dist/ui-chat.css";

  createRoot(document.getElementById("chat")!).render(
    <SmarterChat
      apiUrl="https://stackademy.3141-5926-5359.api.example.com/"
      cookieDomain="example.com"
      showConsole={false}
    />,
  );

``apiUrl`` is the url of a deployed LLMClient's api. Its other props are optional:

- ``apiKey``: a Smarter api key, sent as ``Authorization: Token <apiKey>``, for LLMClients that
  require authentication. Anyone who can view the page can read it, so use a key whose permissions
  you are comfortable sharing.
- ``toggleMetadata``, ``showConsole`` and ``debugMode``: the workbench's metadata toggle, Console,
  and browser console logging. ``showConsole`` defaults to ``true``, which only suits wide pages.
- ``csrfCookieName``, ``csrftoken``, ``sessionCookieName``, ``sessionCookieExpiration`` and
  ``cookieDomain``: the cookies that the chat reads and sets.
- ``streamProgress``: display the progress of a running prompt. It defaults to ``true``. A Smarter
  platform that doesn't stream answers with JSON, as before.
- ``logStreamUrl``: the url of a server log stream, for the Console's Server Logs tab.

Requests from your page to the Smarter api are cross-origin, so your page's origin must be allowed
by the Smarter platform's CORS configuration. The chat's custom ``X-Smarter-*`` request headers are
in ``CORS_ALLOW_HEADERS``, in ``smarter.settings.base``. See the
`smarter-chat README <https://github.com/smarter-sh/smarter-chat>`__ for its complete api.


Technical Reference
-------------------

.. toctree::
   :maxdepth: 1

   smarter-chat/django-view
   smarter-chat/django-template
   smarter-chat/template-tags
   smarter-chat/progress


See Also
--------

- https://www.npmjs.com/package/@smarter.sh/ui-chat
- https://github.com/smarter-sh/smarter-chat
