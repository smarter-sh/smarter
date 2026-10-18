How the Web Console Hosts It
============================

In the web console, Smarter Chat is the LLMClient prompt engineering workbench, at
``/workbench/llm-clients/<hashed_id>/prompt/``. It is hosted exactly as the web console's other
React apps are (see :doc:`Django-React Integration <../developer-reference/react-integration>`):
Django renders a page with the app's root element, the root element's attributes configure the app,
and the app takes over from there.


The View, the Template and the Template Tag
-------------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Piece
     - Role
   * - :py:class:`PromptWorkbenchView <smarter.apps.prompt.views.detailviews.prompt_workbench_view.PromptWorkbenchView>`
     - Requires a logged-in user, finds the LLMClient, and renders ``react/smarter-chat.html`` with a
       ``smarter_chat`` context of the values below.
   * - ``templates/react/smarter-chat.html``
     - Extends the dashboard's base template, includes the app's css and JavaScript files, and
       renders the root element, whose attributes are the ``smarter_chat`` context.
   * - :py:mod:`react_smarter_chat <smarter.apps.prompt.templatetags.react_smarter_chat>`
     - The ``smarter_chat_react_assets`` template tag, which reads the Vite ``manifest.json`` in
       ``static/react/@smarter.sh/ui-chat/`` to find the build's hashed file names, including its
       shared and vendor chunks.
   * - ``src/main.tsx``, in Smarter Chat
     - Reads the root element's attributes, and renders ``App``, which is ``SmarterChat`` with the
       Console.


The Root Element
----------------

The root element's attributes are the app's props. ``main.tsx`` throws an error if a required one
is missing, so the page fails loudly rather than rendering a broken chat.

.. list-table::
   :header-rows: 1
   :widths: 32 18 50

   * - Attribute
     - Prop
     - Value
   * - ``id``
     -
     - ``smarter-chat-root``
   * - ``smarter-llmclient-api-url``
     - ``apiUrl``
     - The LLMClient's ``sandbox_url``, ``https://<platform>/workbench/llm-clients/<hashed_id>/``.
       Required.
   * - ``smarter-toggle-metadata``
     - ``toggleMetadata``
     - ``True``: the workbench shows the Sandbox mode / Production mode button.
   * - ``smarter-csrf-cookie-name``
     - ``csrfCookieName``
     - Django's ``CSRF_COOKIE_NAME``. Required.
   * - ``smarter-session-cookie-name``
     - ``sessionCookieName``
     - ``SMARTER_CHAT_SESSION_KEY_NAME``, the cookie of the chat session's key (not Django's
       session). Required.
   * - ``smarter-django-session-cookie-name``
     -
     - Django's ``SESSION_COOKIE_NAME``. Not read by the app: the browser sends Django's session
       cookie with each request by itself.
   * - ``smarter-cookie-domain``
     - ``cookieDomain``
     - Django's ``SESSION_COOKIE_DOMAIN``, or the page's hostname if empty.
   * - ``react-debug-mode``
     - ``debugMode``
     - The ``ENABLE_REACTAPP_DEBUG_MODE`` waffle switch, which turns on logging to the browser
       console.
   * - ``smarter-request-id``
     - ``smarterRequestId``
     - A unique id of the page request, sent back as the ``X-Smarter-RequestId`` header. Required.
   * - ``smarter-log-stream-url``
     - ``logStreamUrl``
     - The url of the user's server log stream, or empty when log viewing in the browser is disabled
       (``SMARTER_ENABLE_DASHBOARD_SERVER_LOGS``), in which case the Console has no Server Logs tab.
   * - ``smarter-manifest-editor-url``
     - ``manifestEditorUrl``
     - The path of the LLMClient's manifest editor,
       :py:class:`~smarter.apps.prompt.views.detailviews.prompt_manifest_view.LLMClientManifestEditorView`,
       for the Console's Manifest tab. The page is the manifest editor of the LLMClient's detail page,
       without the console's header and sidebar, and it is the only console page that the console's
       own pages may frame (``X-Frame-Options: SAMEORIGIN``). When the editor saves, it posts a
       ``smarter:manifest-saved`` message to the workbench, which the chat accepts only from that
       frame, and then reloads the LLMClient's configuration.

Boolean attributes are compared case-insensitively with ``"true"``, so Django's ``True`` works.

Changing what the workbench passes to the chat is a change in both repositories: the view's context
and the template here, and ``main.tsx`` and ``index.html`` in Smarter Chat. See *Adding a prop* in
:doc:`Developing Smarter Chat <development>`.


Authentication in the Workbench
-------------------------------

The workbench page and the chat's requests are authenticated by the web console's Django session.
The chat's requests are sent with ``credentials: "include"``, so the browser adds the session
cookie, and the chat adds the ``X-CSRFToken`` header from the CSRF cookie. Its ``apiUrl`` is on the
platform's own domain, so the configuration request is same-origin. The prompt request, to the
LLMClient's ``url_llmclient``, is also on the platform domain, under ``/api/v1/``.

A workbench url is a sandbox url: the LLMClient requires an authenticated user there whether it is
deployed or not, and the configuration's ``sandbox_mode`` is ``true``.


Builds and Static Files
-----------------------

``npm run build``, in the React workspace, writes the app into
``smarter/smarter/static/react/@smarter.sh/ui-chat/``, with a ``manifest.json`` that has a
``_custom`` entry of the build's time, version and environment. ``collectstatic`` copies it into
``staticfiles``, from which it is served. In development, use ``make react-build``, and restart
``smarter-app`` afterwards: the template tag caches the manifest, including a missing one.


Technical Reference
-------------------

- :doc:`Workbench view <technical-reference/workbench-view>`
- :doc:`Django template <technical-reference/django-template>`
- :doc:`Template tags <technical-reference/template-tags>`
