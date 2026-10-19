How the Web Console Hosts It
============================

In the web console, Smarter Chat is the chat of the LLMClient prompt engineering workbench, at
``/workbench/llm-clients/<hashed_id>/prompt/``. The workbench is the platform's own React app,
``@smarter/workbench`` (``smarter/react/packages/smarter-workbench``), which imports
``SmarterChat`` from the ``@smarter.sh/ui-chat`` npm package, as any React application does, and puts
the developer Console beside it. It is hosted exactly as the web console's other React apps are (see
:doc:`Django-React Integration <../developer-reference/react-integration>`): Django renders a page
with the app's root element, the root element's attributes configure the app, and the app takes
over from there.


The View, the Template and the Template Tag
-------------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Piece
     - Role
   * - :py:class:`PromptWorkbenchView <smarter.apps.prompt.views.detailviews.prompt_workbench_view.PromptWorkbenchView>`
     - Requires a logged-in user, finds the LLMClient, and renders ``react/workbench.html`` with a
       ``workbench`` context of the values below.
   * - ``templates/react/workbench.html``
     - Extends the dashboard's base template, includes the app's css and JavaScript files, and
       renders the root element, whose attributes are the ``workbench`` context.
   * - :py:mod:`react_workbench <smarter.apps.prompt.templatetags.react_workbench>`
     - The ``workbench_react_assets`` template tag, which reads the Vite ``manifest.json`` in
       ``static/react/@smarter/workbench/`` to find the build's hashed file names.
   * - ``src/main.tsx``, in ``@smarter/workbench``
     - Reads the root element's attributes, and renders the workbench: ``SmarterChat``, and the
       Console beside it.


The Root Element
----------------

``main.tsx`` throws an error if a required attribute is missing, so the page fails loudly rather
than rendering a broken workbench.

.. list-table::
   :header-rows: 1
   :widths: 34 66

   * - Attribute
     - Value
   * - ``id``
     - ``smarter-workbench-root``
   * - ``smarter-llmclient-api-url``
     - The LLMClient's ``sandbox_url``, ``https://<platform>/workbench/llm-clients/<hashed_id>/``, the
       chat's ``apiUrl``. Required.
   * - ``smarter-toggle-metadata``
     - ``True``: the chat shows the Sandbox mode / Production mode button (``toggleMetadata``).
   * - ``smarter-csrf-cookie-name``
     - Django's ``CSRF_COOKIE_NAME``. Required.
   * - ``smarter-session-cookie-name``
     - ``SMARTER_CHAT_SESSION_KEY_NAME``, the cookie of the chat session's key (not Django's
       session). Required.
   * - ``smarter-django-session-cookie-name``
     - Django's ``SESSION_COOKIE_NAME``. Required.
   * - ``smarter-cookie-domain``
     - Django's ``SESSION_COOKIE_DOMAIN``, or the page's hostname if empty.
   * - ``react-debug-mode``
     - The ``ENABLE_REACTAPP_DEBUG_MODE`` waffle switch, which turns on logging to the browser
       console.
   * - ``smarter-request-id``
     - A unique id of the page request, sent back as the ``X-Smarter-RequestId`` header. Required.
   * - ``smarter-log-stream-url``
     - The url of the user's server log stream, or empty when log viewing in the browser is disabled
       (``SMARTER_ENABLE_DASHBOARD_SERVER_LOGS``), in which case the Console has no Server Logs tab.
   * - ``smarter-manifest-url``
     - The path of the LLMClient's manifest, as JSON,
       :py:class:`~smarter.apps.prompt.views.detailviews.prompt_manifest_view.LLMClientManifestEditorView`,
       which the Console's Manifest tab fetches when it is first opened, and edits with the
       ``@smarter/manifest-editor`` component, the editor of every manifest detail page.
   * - ``smarter-architecture-url``
     - The path of the LLMClient's architecture, as JSON,
       :py:class:`~smarter.apps.prompt.views.detailviews.prompt_architecture_view.LLMClientArchitectureView`,
       which the Console's Architecture tab fetches when it is first opened, and draws with the
       ``@smarter/llmclient-architecture`` component: the tree of the SAM resources that the LLMClient is
       built from, as cards that open each resource's manifest page. Its data is
       :py:mod:`~smarter.apps.prompt.views.detailviews.architecture_contract`.
   * - ``smarter-deployment-url``
     - The path of the LLMClient's deployment page's data,
       :py:class:`~smarter.apps.prompt.views.detailviews.prompt_deployment_view.LLMClientDeploymentView`,
       which the Console's Deployment tab fetches when it is first opened, and renders with the
       ``@smarter/llmclient-deployment`` component: the content of the page at a deployed LLMClient's
       url, with its owner and its api key. Its data is
       :py:mod:`~smarter.apps.llmclient.views.deployment_contract`.
   * - ``smarter-llmclient-list-url``
     - The LLM Clients list, where the workbench goes when its Manifest tab deletes the LLMClient.
       Required.
   * - ``smarter-apply-api-url``, ``smarter-validate-api-url``, ``smarter-delete-api-url``,
       ``smarter-kind-placeholder``
     - The cli api's urls, with which the Manifest tab's editor saves, validates and deletes the
       manifest, as every manifest page's editor does. Required.

Boolean attributes are compared case-insensitively with ``"true"``, so Django's ``True`` works.


The Chat and the Console
------------------------

The workbench passes the chat its props, and follows it with the props that
``@smarter.sh/ui-chat`` has for a page that hosts it:

- ``verbose``: the chat fetches the configuration's diagnostic parts, e.g. the chat session's tool
  calls, only while the Console displays them, in its Tool Calls and Config tabs.
- ``onConfig``: the Console displays the configuration that the chat fetched, and streams the server
  logs of its chat session.
- ``onNewChat``: a new chat clears the Console's server logs.
- ``onModeChange``: in production mode, the Console, its button and the Docs button are hidden, and
  the server logs are at the server's own level, rather than DEBUG.
- ``reloadKey``: when the Manifest tab's editor saves the manifest, the chat reloads the LLMClient's
  configuration, and the chat session continues.
- ``headerActions``: the workbench's Docs and Console buttons, in the chat's header, as
  ``HeaderButton`` s, which look like the chat's own.

Changing what the chat passes to the workbench is a change in both repositories: a prop of
``SmarterChat`` in Smarter Chat, released, and the workbench here. Changing only what Django passes to
the workbench is a change here: the view's context, the template, and the workbench's
``src/lib/session.ts``.


Authentication in the Workbench
-------------------------------

The workbench page and its requests are authenticated by the web console's Django session. The
chat's requests are sent with ``credentials: "include"``, so the browser adds the session cookie, and
the chat adds the ``X-CSRFToken`` header from the CSRF cookie. Its ``apiUrl`` is on the platform's
own domain, so the configuration request is same-origin. The prompt request, to the LLMClient's
``url_llmclient``, is also on the platform domain, under ``/api/v1/``. The Console's Manifest,
Architecture and Deployment tabs fetch their data from the platform's own domain, with the same session.

A workbench url is a sandbox url: the LLMClient requires an authenticated user there whether it is
deployed or not, and the configuration's ``sandbox_mode`` is ``true``.


Builds and Static Files
-----------------------

``npm run build``, in the React workspace, builds Smarter Chat's library first, into
``packages/smarter-chat/dist/``, and then the workbench, which imports it, into
``smarter/smarter/static/react/@smarter/workbench/``, with a ``manifest.json`` that has a ``_custom``
entry of the build's time, version and environment. ``collectstatic`` copies it into
``staticfiles``, from which it is served. In development, use ``make react-build``, and restart
``smarter-app`` afterwards: the template tag caches the manifest, including a missing one. The
workbench's tests and type check import the library too, so ``make react-test`` and
``make react-lint`` build it first (``npm run build:deps``).


Technical Reference
-------------------

- :doc:`Workbench view <technical-reference/workbench-view>`
- :doc:`Django template <technical-reference/django-template>`
- :doc:`Template tags <technical-reference/template-tags>`
