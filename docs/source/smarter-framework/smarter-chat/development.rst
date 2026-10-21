Developing Smarter Chat
=======================

This guide is for developers who write React code in Smarter Chat, the ``@smarter.sh/ui-chat`` npm
package, which the web console's prompt engineering workbench imports too. It assumes you know React and TypeScript, and
explains how Smarter Chat is put together, how to run it, how to test it, and how to make the most
common kinds of change. For the conventions that it shares with the web console's other React apps,
see :doc:`Django-React Integration <../developer-reference/react-integration>`.


Where the Code Lives
--------------------

Smarter Chat lives in the Smarter repository, as ``smarter/react/packages/smarter.sh-chat``, one of the
packages of the React npm workspace in ``smarter/react``. ``make react-install`` installs its
dependencies with everyone else's:

.. code-block:: console

  make react-install

It is a workspace package like any other, with the same TypeScript, Vite, Vitest, Storybook, ESLint
and Prettier configuration as the other React apps, and you change it in the same branch and commit
as the Django code that it talks to. A change to the chat api, for example, is one commit: the
backend's models, the contract's schema and the TypeScript types that ``make chat-contract``
regenerates in the package (see `Using a new field of the configuration`_). One thing is different:
**it is a library, not a page.** Its name is ``@smarter.sh/ui-chat``, its npm package name, rather
than the ``@smarter/<name>`` of the console's apps, and its build is its ``dist/``. The web console's
workbench, ``@smarter/workbench``, imports it from there, as any React application does, so the
workspace builds it before the workbench (``npm run build:deps``). See
:doc:`How the Web Console Hosts It <web-console-hosting>`.

Its npm scripts run from the package's folder, or from ``smarter/react`` with
``-w @smarter.sh/ui-chat``:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Script
     - What it does
   * - ``npm run dev``
     - Vite's dev server, with ``index.html``: the chat alone (see `Running It`_).
   * - ``npm run storybook``
     - Storybook, at http://localhost:6006.
   * - ``npm run build``, ``build:lib``, ``build:embed``
     - The package's builds (see `Builds`_), and ``npm run check:dist`` checks their output.
   * - ``npm test``, ``npm run coverage``
     - The unit tests, and a coverage report in ``coverage/``.
   * - ``npm run lint``, ``npm run typecheck``
     - ESLint, and the TypeScript compiler.
   * - ``npm run contract:types``
     - Generates ``src/contract.gen.ts`` from the contract's JSON Schema.
   * - ``npm run i18n``
     - Extracts, merges and compiles the translation catalogs.

Smarter Chat's history up to version 0.16.2, when it had a repository of its own, is in the
archived `smarter-sh/smarter-chat <https://github.com/smarter-sh/smarter-chat>`__ repository.


Running It
----------

There are three ways to run Smarter Chat, from the fastest feedback to the most realistic.

**Storybook, with the api mocked.** No backend is needed. The stories' api responses come from
`MSW <https://mswjs.io/>`__ handlers in ``src/mocks/``. When the Smarter dev server is running on
port 9357, the stories use the web console's stylesheets, so they look as they do in the web
console; otherwise they use Bootstrap, which the web console's theme is built on.

.. code-block:: console

  make react-storybook APP=smarter.sh-chat   # from the repository's root, or
  npm run storybook                       # from smarter/react/packages/smarter.sh-chat

**Vite's dev server, against your local Smarter.** ``npm run dev``, in the package, serves
``index.html`` with hot module replacement, and proxies ``/api``, ``/workbench`` and ``/static``
requests to the Django dev server at http://localhost:9357. Log in to the web console first, so that
the session and CSRF cookies exist, and set ``smarter-llmclient-api-url`` in ``index.html``'s root
element to the workbench url of one of your LLMClients, for example
``http://localhost:9357/workbench/llm-clients/<hashed_id>/``.

**The web console itself.** ``make react-build``, from the repository's root, builds Smarter Chat's
library, then every React app, the workbench among them, into Django's static files, collects them,
and builds the Docker image. Then restart
``smarter-app``, and open an LLMClient's workbench. Use ``make react-build``, not ``make build``,
which reuses the static files that were collected before. A page whose React app is missing its
build renders an empty root element, with no console errors, and the template tag caches the
missing manifest until ``smarter-app`` restarts.


Builds
------

``npm run build`` runs the package's two builds, into ``dist/``:

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * -
     - The npm library
     - The embed script
   * - Command
     - ``npm run build:lib`` (``vite build --mode lib``)
     - ``npm run build:embed`` (``--mode embed``, then ``embed-mermaid``)
   * - Entry point
     - ``src/index.ts``, the package's public api
     - ``src/embed/index.ts``, the ``<smarter-chat>`` element
   * - Output
     - ES and UMD bundles, ``ui-chat.css``, and type declarations
     - ``embed.js``, one classic script, and ``embed/``
   * - React
     - a peer dependency, not bundled
     - bundled
   * - Mermaid
     - left to the consuming page's bundler
     - its own ES module build, imported when a message first has a diagram
   * - KaTeX css and fonts
     - left out; pages import ``katex/dist/katex.min.css``
     - in the shadow root, and the fonts beside ``embed.js``

Both builds strip ``console.debug`` calls, so use ``console.debug`` freely for development logging,
and never for anything a production user needs. ``npm run dev`` serves ``index.html``, the chat
alone, for development; there is no app build.

``src/index.ts`` is the package's public api. Anything exported from it is a promise to the
package's users: removing or renaming an export, or a prop, is a breaking change (see
`Releases`_).


Architecture
------------

Source layout
~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Path
     - Responsibility
   * - ``src/components/SmarterChat/``
     - The chat: state, the api calls' orchestration, the header, the thread and the message box.
       ``HeaderButton.tsx`` is a button of the header, for a page's ``headerActions``, and
       ``icons.tsx`` has the toolbar's svg icons.
   * - ``src/components/AppTitle/``
     - The title, with its valid and deployed icons.
   * - ``src/components/ErrorBoundary/``
     - Displays a rendering error instead of an empty page.
   * - ``src/lib/api.ts``
     - Every request to the Smarter api: urls, headers, the configuration, prompts, and the
       prompt's Server-Sent Events. The only module that calls ``fetch``.
   * - ``src/lib/messages.ts``
     - The chat thread: building it from the configuration, turning api messages into displayable
       ones and back, and rendering markdown to sanitized html.
   * - ``src/lib/code.ts``, ``math.ts``, ``mermaid.ts``
     - Code blocks (highlight.js), math (KaTeX, as a ``marked`` extension) and diagrams (Mermaid).
   * - ``src/lib/cookie.ts``
     - Reading Django's CSRF cookie, and the chat session and debug cookies.
   * - ``src/lib/enums.ts``
     - Message directions and sender roles.
   * - ``src/types.ts``
     - The props, and the shapes of the api's data, as aliases of the generated contract types.
   * - ``src/contract.gen.ts``, ``contract/``, ``scripts/contract-types.mjs``
     - The api contract: its JSON Schema, copied from the backend by ``make chat-contract``, and the
       TypeScript types generated from it (``npm run contract:types``). Never edit them by hand.
   * - ``src/mocks/``
     - Api fixtures and MSW handlers for the stories and tests, and test doubles.

Components import from ``@/``, an alias of ``src/``.

What happens when the chat loads
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. ``SmarterChat`` builds its cookie descriptors (``ChatCookies``) and client context
   (``ClientContext``) from its props.
2. Its first effect calls ``startChat()``, which calls ``fetchConfig()``: a POST to
   ``<apiUrl>config/``, with the session key from the session cookie, if there is one, and
   ``X-Smarter-Capabilities: chat-contract-v2``. ``normalizeConfig()`` converts a version 1
   configuration, from an older platform, to version 2.
3. ``fetchConfig()`` saves the returned ``session_key`` and ``debug_mode`` in their cookies, and
   returns the ``ChatConfig``.
4. ``chatInit()`` builds the thread: the restored ``history.chat_history`` if there is one, else the
   system prompt, the welcome message and the example prompts.
5. The header, placeholder and attach button are rendered from ``config.llmclient``, and
   ``onConfig`` passes the whole configuration to the page, e.g. to the workbench's Console.

A failure sets ``configError``, which the thread and header display.

What happens when the user sends a message
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. ``sendMessage()`` adds the user's message to the thread, and shows the typing indicator.
2. ``chatMessages2RequestMessages()`` turns the thread into api messages: only the roles the LLM
   accepts (``system``, ``assistant``, ``user``, ``tool``), each with its original fields, such as
   an assistant's ``tool_calls``. Smarter's own messages are never sent back.
3. ``fetchPrompt()`` POSTs ``{session_key, messages}`` to ``config.llmclient.url_llmclient``. With
   ``streamProgress``, it asks for Server-Sent Events, and passes each ``progress`` event to
   ``onProgress``, which adds it to the ``progress`` state, displayed as a step in the thread.
4. The result's messages (``data.messages`` in version 2, ``smarter.messages`` in the completion in
   version 1) are added to the thread. Backend
   messages are hidden if the chat is in production mode. A failed prompt resolves too, with a
   ``smarter_error`` message.
5. With ``verbose``, ``refreshConfig()`` fetches the configuration again, with its diagnostic parts,
   so that the page, e.g. the workbench's Console, gets the session's new tool calls.

See :doc:`The Chat API Contract <api-contract>` for the requests and responses themselves.

State
~~~~~

``SmarterChat`` holds all of the chat's state, with plain ``useState``; there is no store.

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - State
     - Meaning
   * - ``config``
     - The ``ChatConfig``, or ``null`` until it loads. The chat is disabled until then.
   * - ``configError``
     - Why the configuration couldn't be loaded.
   * - ``messages``
     - The thread, as ``ChatMessage`` objects. ``display: false`` hides one without removing it.
   * - ``showMetadata``
     - Sandbox mode (``true``) or production mode. It starts as ``toggleMetadata``.
   * - ``isTyping``, ``progress``
     - A prompt is running, and its steps so far.
   * - ``configVerbose``
     - Whether the configuration's diagnostic parts are current: fetched with ``verbose``, and since
       the last prompt.

Rendering messages
~~~~~~~~~~~~~~~~~~

Messages are displayed by `chatscope <https://github.com/chatscope/chat-ui-kit-react>`__'s
``Message`` component, which takes html strings, not React elements. So message rendering is a
pipeline of strings, in ``messages.ts``:

1. ``messageFactory()`` turns an api message into a ``ChatMessage``. The user's messages go through
   ``convertMarkdownLinksToHTML()``, which escapes them and converts only links and images. Every
   other role goes through ``convertMarkdownToHTML()``.
2. ``convertMarkdownToHTML()`` parses GitHub flavored markdown with ``marked``, with the math
   extension from ``math.ts``, and custom renderers that escape raw html, restrict link and image
   urls, and render code blocks with ``code.ts``.
3. The html is sanitized with DOMPurify, and only then displayed.

Because messages are html strings, their interactive parts can't have React event handlers. The
code blocks' **Copy** buttons and the diagrams' **Code** buttons are handled by one click listener on
the chat, by event delegation (``copyCodeBlock()`` and ``toggleMermaidDiagram()``). Mermaid renders
asynchronously, so a ``mermaid`` block is first rendered as a code block, and
``renderMermaidDiagrams()``, called in a layout effect whenever the messages change, replaces it in
the page with its diagram. Diagrams are cached by their source, so a re-render doesn't redraw them.

.. important::

  Every string that reaches a ``Message`` must come from ``messageFactory()``, or be sanitized the
  same way. Messages come from the LLM, from tools, and from users, and must never be trusted as
  html.

Styling
~~~~~~~

Each component imports its own ``styles.css``. Class names are prefixed ``smarter-chat-``, because the
npm package's css shares the page with its host's. chatscope's classes (``cs-*``) are overridden in
``SmarterChat/styles.css``.


Testing
-------

Smarter Chat's tests use `Vitest <https://vitest.dev/>`__ and React Testing Library, with jsdom.

.. code-block:: console

  npm test                                # in smarter/react/packages/smarter.sh-chat
  npm run coverage                        # with a coverage report in coverage/
  npm run lint && npm run typecheck       # ESLint and TypeScript
  npx vitest run --project smarter.sh-chat   # in smarter/react: only Smarter Chat's tests
  make react-test                         # from the repository's root: every React app, as CI does
  make react-lint                         # formatting, lint and types of every React app

- **One test module per source module**, beside it: ``api.test.ts`` for ``api.ts``,
  ``Component.test.tsx`` for ``Component.tsx``.
- **Every story is also a test.** ``src/stories.test.tsx`` renders each story in
  ``*.stories.tsx``, and runs its ``play`` function, with its MSW handlers. A new visual state needs
  a story; a story that breaks fails the tests.
- **The api is mocked with MSW**, in tests and in Storybook alike. ``src/mocks/fixtures.ts`` holds
  the api's data, copied from real responses, and ``src/mocks/handlers.ts`` groups handlers by
  scenario (``chatHandlers``, ``promptErrorHandlers``, ``streamingHandlers``, ...). An unmocked
  request fails the test.
- **jsdom has no** ``EventSource``. ``installFakes()`` from ``src/mocks/fakes.ts`` installs
  ``FakeEventSource``, which a test drives with ``open()``, ``emit()`` and ``fail()``.
- **The fixtures match the contract.** ``src/contract.test.ts`` validates them against
  ``contract/chat-contract.schema.json`` with Ajv, in both versions of the contract, so a test can't
  pass against a response that the backend never sends.
- **jsdom can't lay out Mermaid's svg**, so tests mock ``mermaid`` with ``src/mocks/mermaid.ts``.
  Storybook's ``WithDiagram`` story uses the real Mermaid.

See the ``smarter-react-testing`` skill in the repository's ``skills/`` folder for the workspace's shared test
configuration and its pitfalls.


Common Changes
--------------

Adding a prop
~~~~~~~~~~~~~

1. Add it to ``SmarterChatProps`` in ``src/types.ts``, optional, with a doc comment.
2. Give it a default in ``SmarterChat``'s parameter list. The default must suit the npm package's
   users.
3. If the web console's workbench sets it, pass it in the workbench's ``App.tsx``
   (``smarter/react/packages/smarter-workbench``), in the same change (see
   :doc:`How the Web Console Hosts It <web-console-hosting>`).
4. Add it to the props table of the README, and of :doc:`Embedding Smarter Chat <embedding>`.
5. Test it, and add a story if it changes what the chat looks like.

Adding or changing text
~~~~~~~~~~~~~~~~~~~~~~~

Smarter Chat is translated with gettext, as the web console is (see
:doc:`Translations <../developer-reference/translations>`), but its catalogs are its own, because the
npm package and the embed script run on pages that Django didn't render. Its ``src/lib/i18n.tsx``
has the same functions as ``@smarter/common``: ``gettext``, ``ngettext``, ``pgettext``,
``npgettext``, ``interpolate`` and ``interpolateNodes``, and the same rules: a whole sentence, as a
string literal, with named ``%(name)s`` placeholders. Translate when the text is displayed, never in
a module-level constant, because ``SmarterChat`` activates its language as it renders.

1. Mark the text, e.g. ``gettext("Start a new chat")``.
2. ``npm run i18n``, in the package. ``scripts/i18n.mjs`` extracts the messages with the TypeScript
   compiler into ``locale/smarter-chat.pot``, merges them into
   ``locale/<language>/LC_MESSAGES/smarter-chat.po``, keeping their translations, and compiles the
   ``.po`` files into ``src/catalogs.gen.ts``, which the builds bundle.
3. Translate the new ``msgstr`` entries in every language's ``.po`` file (Spanish, French and
   Brazilian Portuguese), with the web console's terms, and check them with ``msgfmt --check -o /dev/null <file>.po``.
4. ``npm run i18n`` again. ``src/catalogs.test.ts`` fails when a catalog is out of date, or a message
   isn't translated, or its placeholders differ from the English text's.

Using a new field of the configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


The api's types are not written by hand. They are generated from the contract's JSON Schema, which
the backend generates from its Pydantic models (see :doc:`The Chat API Contract <api-contract>`):

1. Declare the field in the backend's model, in :mod:`smarter.apps.prompt.contract.models` (for
   example ``PromptChatApiLLMClient`` for ``llmclient.*``), optional unless every supported Smarter
   release sends it. If the public configuration must include it, add it to
   ``PUBLIC_LLMCLIENT_FIELDS`` too.
2. Run ``make chat-contract``, from the repository's root. It regenerates the backend's schema, and
   the package's ``contract/chat-contract.schema.json`` and ``src/contract.gen.ts``. Commit them
   together with the model.
3. Add the field to ``makeConfig()`` in ``src/mocks/fixtures.ts``. ``src/contract.test.ts`` checks
   the fixtures against the schema, and that ``src/contract.gen.ts`` is up to date.
4. Read it, with a fallback for platforms that don't send it yet, and for version 1 of the contract,
   which ``normalizeConfig()`` in ``src/lib/api.ts`` converts.

Handling a new kind of progress event
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Nothing is required: the chat displays any ``progress`` event's ``message``. To treat a type
specially, switch on ``event.type`` in ``SmarterChat``'s ``onProgress``, and add an example to
``progressEvents`` in ``src/mocks/fixtures.ts``. The types are listed in
:py:class:`~smarter.apps.prompt.progress.PromptProgressEvents`.

Adding a Console tab
~~~~~~~~~~~~~~~~~~~~

The Console is the workbench's (``smarter/react/packages/smarter-workbench``), not Smarter Chat's. Add the tab's id to ``MenuItems`` in ``Console/enums.ts``, its label to ``tabs()``
in ``Console/Component.tsx``, and its data to ``consoleData()`` in ``Console/data.ts``, which reads it
from the configuration that ``onConfig`` passes. A tab that fetches its own data, as the Manifest and
Deployment tabs do, uses ``useTabData()``.

Extending markdown
~~~~~~~~~~~~~~~~~~

Add a ``marked`` extension or renderer in ``messages.ts``, following ``math.ts``. Anything it emits
passes through DOMPurify; if it emits tags or attributes that DOMPurify removes, allow exactly those
in ``sanitize()``, never more. Add a fixture with an example to ``src/mocks/fixtures.ts``, and a
story.


Releases
--------

``@smarter.sh/ui-chat`` is released with the Smarter platform, and has its version. Commit messages
follow `Conventional Commits <https://www.conventionalcommits.org/>`__, and
`semantic-release <https://semantic-release.gitbook.io/>`__ versions the platform from them on each
push to ``alpha`` and ``beta`` (prereleases) and ``main``: ``feat`` is a minor release, ``fix`` and
``perf`` are patches, and a ``BREAKING CHANGE:`` footer is a major release. Each GitHub release that
semantic-release publishes starts ``.github/workflows/uiChatRelease.yml``, which checks out the
release's tag, sets the package's version from it (``v0.36.0-alpha.3`` publishes
``0.36.0-alpha.3``), runs the package's tests, builds it, checks the build with
``npm run check:dist``, and publishes it to npm with trusted publishing and a provenance statement.
A release from ``main`` gets the npm dist-tag ``latest``, and a prerelease gets its channel's,
``alpha`` or ``beta``, so ``npm install @smarter.sh/ui-chat`` and the embed script's jsDelivr ranges,
such as ``@0``, only ever load ``latest`` releases; the workflow asks jsDelivr to refresh those
ranges after each one. ``@smarter.sh/ui-widgets`` is published the same way, by
``uiWidgetsRelease.yml``.

Keep two audiences in mind when you change behavior that depends on the backend:

- **The web console** always runs the Smarter Chat that was built into its image, from the same
  commit as the backend, so the two change together.
- **Pages that embed the npm package** run whichever version they installed, against whichever
  Smarter platform they call. A new version of the chat must keep working with the platform
  releases that are in use, and the platform must keep working with the chat versions that are in
  use. Read the fields you depend on defensively, and say in the release notes when a feature needs
  a newer platform.
