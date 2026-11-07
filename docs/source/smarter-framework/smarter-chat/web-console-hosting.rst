How the Web Console Hosts It
============================

In the web console, Smarter Chat is the chat of the LLMClient prompt engineering workbench, at
``/workbench/llm-clients/<hashed_id>/prompt/``. The workbench is the platform's own React package,
``@smarter/workbench`` (``smarter/react/packages/smarter-workbench``), which imports
``SmarterChat`` from the ``@smarter.sh/ui-chat`` npm package, as any React application does, and puts
the developer Console beside it. It is a page of the single-page console, ``@smarter/console``
(:doc:`ADR-035 </adr/035-single-page-app>`, and
:doc:`Django-React Integration <../developer-reference/react-integration>`): the console renders the
workbench's component at the page's route, configured from the url's hashed id and the console's
session.


The Page
--------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Piece
     - Role
   * - :py:class:`PromptWorkbenchView <smarter.apps.prompt.views.detailviews.prompt_workbench_view.PromptWorkbenchView>`
     - Django's view of the path, a ``ConsoleAppView``: it answers with the console's page, and keeps the
       url name that ``LLMClient.workbench_url`` reverses.
   * - ``src/routes/WorkbenchPage.tsx``, in ``@smarter/console``
     - The console's route, ``/workbench/llm-clients/:id/prompt``, loaded lazily, so that the chat and the
       Console's editor are in a chunk of their own. It asks the resource api for the LLMClient,
       ``/api/web/dashboard/resource/llmclient-<hashed_id>/``, first, and shows Page not found when the
       api answers 404: an unknown LLMClient, another account's, or a staff-only one for a user who is not
       the platform's staff.
   * - ``src/lib/workbench.ts``, in ``@smarter/console``
     - ``workbenchConfig()``: the workbench's configuration, below, from the hashed id and the session.
   * - ``src/index.ts``, in ``@smarter/workbench``
     - Exports the ``Workbench`` component and its ``WorkbenchConfig``: ``SmarterChat``, and the Console
       beside it. The package has no build of its own; its ``main.tsx`` is a development page.


The Configuration
-----------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Field
     - Value
   * - ``apiUrl``
     - The LLMClient in the platform api, ``/api/v1/llm-clients/<hashed_id>/``, the chat's ``apiUrl``: the
       chat reads its configuration from ``config/`` there.
   * - ``toggleMetadata``
     - ``true``: the chat shows the Sandbox / Production mode switch.
   * - ``csrfCookieName``, ``cookieDomain``
     - Django's CSRF cookie, and the cookies' domain, from the session, or the page's hostname.
   * - ``sessionCookieName``
     - ``session_key``, ``SMARTER_CHAT_SESSION_KEY_NAME``: the cookie of the chat session's key (not
       Django's session).
   * - ``debugMode``
     - The session's ``reactDebugMode``, the ``ENABLE_REACTAPP_DEBUG_MODE`` waffle switch, which turns on
       logging to the browser console.
   * - ``smarterRequestId``
     - A new id of the page's requests, sent as the ``X-Smarter-RequestId`` header.
   * - ``logStreamUrl``
     - The user's server log stream, ``/api/web/dashboard/logs/stream/``, while the session's
       ``serverLogs`` is on; otherwise null, and the Console has no Server Logs tab.
   * - ``manifestUrl``
     - ``/api/web/prompt/llm-clients/<hashed_id>/manifest/``,
       :py:class:`~smarter.apps.prompt.views.detailviews.prompt_manifest_view.LLMClientManifestEditorView`,
       which the Console's Manifest tab fetches when it is first opened, and edits with the
       ``@smarter/manifest-editor`` component, the editor of every manifest page.
   * - ``architectureUrl``
     - ``/api/web/prompt/llm-clients/<hashed_id>/architecture/``,
       :py:class:`~smarter.apps.prompt.views.detailviews.prompt_architecture_view.LLMClientArchitectureView`,
       which the Console's Architecture tab fetches when it is first opened, and draws with the
       ``@smarter/llmclient-architecture`` component: the tree of the SAM resources that the LLMClient is
       built from, as cards that open each resource's manifest page, whether its chat is styled, and the
       web console's Guardrails, Plugins, Extensions, MCPClients and API Keys pages, for its next steps. Its data is
       :py:mod:`~smarter.apps.prompt.views.detailviews.architecture_contract`.
   * - ``deploymentUrl``
     - ``/api/web/prompt/llm-clients/<hashed_id>/deployment/``,
       :py:class:`~smarter.apps.prompt.views.detailviews.prompt_deployment_view.LLMClientDeploymentView`,
       which the Console's Deployment tab fetches when it is first opened, and renders with the
       ``@smarter/llmclient-deployment`` component: the content of the page at a deployed LLMClient's
       url, with its owner and its api key. Its data is
       :py:mod:`~smarter.apps.llmclient.views.deployment_contract`.
   * - ``llmclientListUrl``, ``navigate``
     - The LLM Clients list, ``/workbench``, and the console router's ``navigate``, with which the
       workbench goes to the list when its Manifest tab deletes the LLMClient.
   * - ``applyApiUrl``, ``validateApiUrl``, ``deleteApiUrl``, ``kindPlaceholder``
     - The cli api's urls, with which the Manifest tab's editor saves, validates and deletes the
       manifest, as every manifest page's editor does.
   * - ``session``
     - The ``SessionContext`` of the Console's own requests, from the console's session.

The guided tour's onboarding state is the console session's too.


The Chat and the Console
------------------------

The workbench passes the chat its props, and follows it with the props that
``@smarter.sh/ui-chat`` has for a page that hosts it:

- ``verbose``: the chat fetches the configuration's diagnostic parts, e.g. the chat session's tool
  calls, only while the Console displays them, in its Tool Calls and Config tabs.
- ``onConfig``: the Console displays the configuration that the chat fetched, and streams the server
  logs of its chat session.
- ``onNewChat``: a new chat clears the Console's server logs.
- ``onModeChange``: in production mode, the Console, its button and the Help menu are hidden, and
  the server logs are at the server's own level, rather than DEBUG.
- ``reloadKey``: when the Manifest tab's editor saves the manifest, the chat reloads the LLMClient's
  configuration, and the chat session continues.
- ``headerActions``: the workbench's Help menu and Console button, in the chat's header, as
  ``HeaderButton`` s, which look like the chat's own. The Help menu opens and closes with
  ``useDropdown()`` from ``@smarter/common``, as the console's user menu does, and returns the focus
  to its button through ``HeaderButton``'s ``ref``.

Changing what the chat passes to the workbench is a change in both repositories: a prop of
``SmarterChat`` in Smarter Chat, released, and the workbench here. Changing only what the console
passes to the workbench is a change here: ``WorkbenchConfig`` in the workbench's ``src/lib/types.ts``,
and ``workbenchConfig()`` in the console's ``src/lib/workbench.ts``.


Authentication in the Workbench
-------------------------------

The workbench and its requests are authenticated by the web console's Django session. The chat's
requests are sent with ``credentials: "include"``, so the browser adds the session cookie, and the chat
adds the ``X-CSRFToken`` header from the CSRF cookie. Its ``apiUrl`` is on the platform's own domain, so
the configuration request is same-origin. The prompt request, to the LLMClient's ``url_llmclient``, is
also on the platform domain, under ``/api/v1/``. The Console's Manifest, Architecture and Deployment tabs
fetch their data from the web console's api, with the same session, and answer 404 for an LLMClient that
the user may not read.

The configuration comes from the platform api, so its ``sandbox_mode`` is ``false``, and its
``meta_data.is_authentication_required`` says whether the LLMClient has an active api key; neither the
chat nor the workbench reads them. The older ``/workbench/llm-clients/<hashed_id>/config/`` is still
served, and is the only url whose configuration has ``sandbox_mode`` true.


Builds and Static Files
-----------------------

The workbench is bundled by the console's build, ``npm run build -w @smarter/console``, into
``smarter/smarter/static/react/@smarter/console/``, in a chunk of its own. It imports Smarter Chat's
built library, ``packages/smarter.sh-chat/dist/``, as npm users do, so ``npm run build:deps`` builds the
library first; ``make react-build``, ``make react-test`` and ``make react-lint`` run it. ``collectstatic``
copies the console's build into ``staticfiles``, from which it is served. In development, use
``make react-build``.


Technical Reference
-------------------

- :doc:`Workbench view <technical-reference/workbench-view>`
