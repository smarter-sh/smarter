Embedding Smarter Chat
======================

This guide is for developers who want to add a Smarter chatbot to their own website or
application, with the `@smarter.sh/ui-chat <https://www.npmjs.com/package/@smarter.sh/ui-chat>`__
npm package. You need a deployed :doc:`LLMClient <../../smarter-resources/smarter-llmclient>` and a
React 19 application built with a bundler, such as Vite, webpack, Rollup or Next.js. You don't
need to know anything about Smarter's backend.


Before You Start
----------------

Smarter Chat runs in your visitors' browsers and talks directly to the Smarter platform. Check
these three things first, because each of them fails in the browser rather than in your build.

**1. The LLMClient is deployed.** Deploy it with ``smarter deploy llmclient <name>``, or from the
web console. A deployed LLMClient has its own host:

.. code-block:: text

  https://<name>.<account-number>.api.<smarter-domain>/

for example ``https://stackademy.3141-5926-5359.api.example.com/``, or the verified
:doc:`custom domain <../../smarter-resources/smarter-custom-domain>` that you gave it. This url is the
``apiUrl`` that you pass to the component.

**2. Your site's origin is allowed.** Requests from your page to Smarter are cross-origin, and are
sent with credentials, so the origin must be allowed explicitly; a wildcard is not allowed. List it
in the LLMClient's manifest, and apply it again:

.. code-block:: yaml

  spec:
    config:
      prompt:
        allowedOrigins:
          - https://www.example.com
          - http://localhost:5173   # your development server

An origin is a scheme, a host and an optional port, without a path. The chat calls one host only,
the LLMClient's (see :doc:`The Chat API Contract <api-contract>`). A platform operator can also
allow an origin for every LLMClient, in ``CORS_ALLOWED_ORIGINS`` or ``CORS_ALLOWED_ORIGIN_REGEXES``.

**3. The browser can authenticate, if the LLMClient requires it.** An LLMClient requires
authentication when it has at least one active :doc:`api key <../../smarter-platform/api-keys>`
attached. Then pass a Smarter api key to the component as ``apiKey``, which it sends as
``Authorization: Token <apiKey>``. A deployed LLMClient without api keys is public: anyone who can
reach its host can chat with it, without an ``apiKey``, and every prompt is charged to the
LLMClient's owner. Give a public LLMClient a :doc:`budget <../../smarter-resources/smarter-budget>`
if that matters to you.

.. warning::

  An ``apiKey`` in a web page is public: anyone who can view the page can read it, and use it. Use
  a key that is dedicated to this page, and revoke it if it is abused. Your web console login
  doesn't help here: the Smarter session cookie is ``SameSite=Lax``, so browsers don't send it with
  requests from other sites.

What the page receives is the public configuration: the LLMClient's name, welcome message, example
prompts, model and system prompt, but not, for example, its owner's profile or the session's
diagnostic histories, which only the workbench sees.


Installation
------------

.. code-block:: console

  npm install @smarter.sh/ui-chat

``react`` and ``react-dom`` 19 are peer dependencies. ``katex``, which typesets math, and
``mermaid``, which draws diagrams, are installed with the package.


Quick Start
-----------

.. code-block:: tsx

  import { createRoot } from "react-dom/client";
  import { SmarterChat } from "@smarter.sh/ui-chat";
  import "@smarter.sh/ui-chat/dist/ui-chat.css";
  import "katex/dist/katex.min.css";

  createRoot(document.getElementById("chat")!).render(
    <div style={{ height: 600 }}>
      <SmarterChat
        apiUrl="https://stackademy.3141-5926-5359.api.example.com/"
        apiKey={import.meta.env.VITE_SMARTER_API_KEY}
        showConsole={false}
      />
    </div>,
  );

That's all. On its first render, the component fetches the LLMClient's configuration, displays its
welcome message and example prompts, and is ready to chat. The chat fills the height of its parent
element, so give the parent a height.

``showConsole={false}`` hides the developer Console, which is on by default and suits only wide
pages, such as an internal tool. See :doc:`Features <features>`.


Props
-----

Only ``apiUrl`` is required. The defaults suit a page that embeds one public LLMClient.

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Prop
     - Default
     - Description
   * - ``apiUrl``
     - (required)
     - The LLMClient's url. The chat appends ``config/`` to it for its configuration.
   * - ``apiKey``
     - ``null``
     - A Smarter api key, sent as ``Authorization: Token <apiKey>``, for LLMClients that require
       authentication.
   * - ``showConsole``
     - ``true``
     - Show the developer Console beside the chat.
   * - ``toggleMetadata``
     - ``false``
     - Show the Sandbox mode / Production mode button, which shows and hides the backend's own
       messages, and start in sandbox mode. Sandbox mode also shows the Docs button. Without it, the chat is in production mode: the thread
       is the conversation, without the system prompt, tool results or Smarter's notes.
   * - ``streamProgress``
     - ``true``
     - Display a running prompt's progress, streamed as Server-Sent Events. A platform that doesn't
       stream answers with JSON, and the chat shows a typing indicator instead.
   * - ``debugMode``
     - ``false``
     - Log to the browser console. The LLMClient's configuration can also turn it on.
   * - ``cookieDomain``
     - ``""``
     - The domain whose cookies the chat reads. Empty means the page's own domain. The chat reads a
       cookie only if the page's hostname is in this domain.
   * - ``sessionCookieName``
     - ``"session_key"``
     - The cookie in which the chat saves its chat session's key.
   * - ``sessionCookieExpiration``
     - one day
     - The session cookie's lifetime, in milliseconds. After it, the visitor starts a new chat.
   * - ``csrfCookieName``
     - ``"csrftoken"``
     - The name of a Django CSRF cookie, whose value is sent as the ``X-CSRFToken`` header. Only the
       web console needs it.
   * - ``csrftoken``
     - ``null``
     - A CSRF token to send instead of the cookie's value.
   * - ``debugCookieName``, ``debugCookieExpiration``
     - ``"debug"``, one day
     - The cookie in which the chat saves the LLMClient's debug mode.
   * - ``smarterRequestId``
     - ``""``
     - An id of the page request, sent as the ``X-Smarter-RequestId`` header, which appears in
       Smarter's logs, for tracing.
   * - ``logStreamUrl``
     - ``null``
     - The url of a Smarter server log stream, for the Console's Server Logs tab. Only useful to
       developers who are logged in to the web console on the same domain.


Recipes
-------

A floating chat widget
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: tsx

  import { useState } from "react";
  import { SmarterChat } from "@smarter.sh/ui-chat";

  export function ChatWidget() {
    const [open, setOpen] = useState(false);
    return (
      <>
        <button className="chat-launcher" onClick={() => setOpen(!open)}>
          Chat with us
        </button>
        {open && (
          <div style={{ position: "fixed", right: 24, bottom: 80, width: 400, height: 600, zIndex: 1000 }}>
            <SmarterChat apiUrl="https://support.3141-5926-5359.api.example.com/" apiKey={apiKey} showConsole={false} />
          </div>
        )}
      </>
    );
  }

Closing the widget unmounts the chat, but not its session: the session's key is in a cookie, so the
conversation is restored when the widget opens again.

Next.js
~~~~~~~

The component uses browser apis (cookies, ``localStorage``, ``EventSource``), so render it on the
client only:

.. code-block:: tsx

  "use client";
  import dynamic from "next/dynamic";
  import "@smarter.sh/ui-chat/dist/ui-chat.css";
  import "katex/dist/katex.min.css";

  const SmarterChat = dynamic(() => import("@smarter.sh/ui-chat").then((m) => m.SmarterChat), { ssr: false });

  export default function Chat() {
    return (
      <div style={{ height: "80vh" }}>
        <SmarterChat
          apiUrl={process.env.NEXT_PUBLIC_SMARTER_LLMCLIENT_URL!}
          apiKey={process.env.NEXT_PUBLIC_SMARTER_API_KEY}
          showConsole={false}
        />
      </div>
    );
  }

Several chatbots on one site
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The chat saves its session's key in a cookie for the page's path, so two LLMClients on two pages,
``/sales/`` and ``/support/``, keep separate sessions. Two chats on the same page must use different
cookies:

.. code-block:: tsx

  <SmarterChat apiUrl={salesUrl} apiKey={apiKey} sessionCookieName="sales_session_key" showConsole={false} />
  <SmarterChat apiUrl={supportUrl} apiKey={apiKey} sessionCookieName="support_session_key" showConsole={false} />

A sandbox for your own team
~~~~~~~~~~~~~~~~~~~~~~~~~~~

An internal tool can show everything the workbench shows:

.. code-block:: tsx

  <SmarterChat apiUrl={apiUrl} apiKey={apiKey} toggleMetadata showConsole />


Styling
-------

Import ``@smarter.sh/ui-chat/dist/ui-chat.css`` (or its alias, ``@smarter.sh/ui-chat/style.css``)
once. It contains the component's own css, and that of
`chatscope <https://github.com/chatscope/chat-ui-kit-react>`__, the chat UI kit that it is built on.

Import ``katex/dist/katex.min.css`` too. It's the stylesheet and fonts of math in the LLM's
responses, and is left out of ``ui-chat.css`` so that your bundler emits KaTeX's fonts as separate
files, which browsers download only when an equation uses them. Without it, math is displayed twice:
as plain text, and as unstyled MathML.

The component's root element has the class ``SmarterChat``, and its parts have stable class names
prefixed ``smarter-chat-``, for example:

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Class
     - Element
   * - ``.smarter-chat-message-list``
     - The thread.
   * - ``.smarter-message``, ``.smarter-error-message``, ``.system-message``
     - Smarter's notes, errors, and system and tool messages.
   * - ``.smarter-progress-message``
     - A step of a running prompt.
   * - ``.smarter-chat-code``
     - A code block, with its header and copy button.
   * - ``.smarter-chat-image``
     - An image in a message.
   * - ``.smarter-chat-console``
     - The Console.

Override them from your own stylesheet, loaded after ``ui-chat.css``.


Bundling Notes
--------------

- **Mermaid** is imported only when a message first has a diagram, so your bundler splits it into
  separate chunks that are downloaded only then.
- **The UMD bundle**, ``dist/smarter-chat-library.umd.js``, expects ``React``, ``ReactDOM`` and
  ``jsxRuntime`` globals. It can't import Mermaid, and displays diagrams as code, unless the page
  maps ``mermaid`` to Mermaid's ES module with an import map, for example to
  ``https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs``. Prefer a bundler.
- **Production builds** of the component strip its ``console.debug`` calls.


What the Component Stores in the Browser
----------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 35 15 50

   * - Name
     - Where
     - Contents
   * - ``session_key`` (``sessionCookieName``)
     - cookie
     - The chat session's key, for the page's path, ``SameSite=Lax``.
   * - ``debug`` (``debugCookieName``)
     - cookie
     - The LLMClient's debug mode.
   * - ``smarter-chat.chat-width``, ``smarter-chat.console-visible``, ``smarter-chat.log-wrap``
     - localStorage
     - The Console's layout, once the visitor changes it.

The chat session itself, its messages, is stored by Smarter, not in the browser. Mention the session
cookie in your site's cookie notice if you have one.


Troubleshooting
---------------

Open the browser's developer tools, and look at the console and the network tab.

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Symptom
     - Cause and fix
   * - "blocked by CORS policy" in the console
     - Your origin isn't in the LLMClient's ``allowedOrigins``. See `Before You Start`_. Origins must
       match exactly, including the scheme and port.
   * - The header reads "Smarter Chat is not available", with "LLMClient not found."
     - ``apiUrl`` is wrong, or the LLMClient isn't deployed.
   * - "blocked by CORS policy" from an origin in ``allowedOrigins``
     - The LLMClient was deployed before its Ingress stopped using Traefik's CORS middleware, which
       answers preflight requests itself. Deploy it again.
   * - "Forbidden. Please provide a valid API key.", or an http 401 or 403
     - The LLMClient has an api key, and ``apiKey`` is missing, wrong, expired or revoked.
   * - "Unexpected response from the Smarter api (http ...)", with another status
     - The response wasn't JSON, for example a proxy's html error page, or a server error. The
       message includes the start of the response.
   * - The chat never leaves "Configuring workbench..."
     - The configuration request is pending. Check that ``apiUrl`` is reachable from the browser.
   * - A blank area where the chat should be
     - The parent element has no height. Give it one.
   * - Math is shown twice, as text and as unstyled symbols
     - ``katex/dist/katex.min.css`` isn't imported.
   * - The prompt's progress never appears, only a typing indicator
     - A proxy in front of Smarter buffers the response, or ``streamProgress`` is ``false``. See
       :doc:`The Chat API Contract <api-contract>`.
   * - Every reload starts a new chat
     - The browser blocks the session cookie, or ``cookieDomain`` doesn't contain the page's hostname.


Versions
--------

The package follows `semantic versioning <https://semver.org>`__, and its
`changelog <https://github.com/smarter-sh/smarter-chat/blob/main/CHANGELOG.md>`__ lists every
release. It asks the platform for the current version of the api contract, and reads the previous one from
older platforms, so a new version of the package works with older Smarter platforms; when a feature
needs a newer platform, its release notes say so. Pin a minor version, ``~0.7.0``, if you want to
review changes before your visitors see them.
