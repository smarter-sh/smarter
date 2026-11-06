Web Console Api
===============

The web console's React apps read and change data through the **web console api**, a set of JSON
endpoints under ``/api/web/``. It is the backend half of the
:doc:`Django-React Integration <react-integration>`, and the console's own backend: the list, clone, rename and delete
actions of every resource list page, the dashboard's widgets, the Prompt Passthrough's providers,
the server log stream, and the like. Every path that the console's pages fetch is under ``/api/``,
and every other path is a page. The reasons are in
:doc:`ADR-034: The Web Console Api </adr/034-web-console-api>`.

How it differs from the public api
----------------------------------

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * -
     - ``/api/v1/``
     - ``/api/web/``
   * - Clients
     - The cli, the SDKs, any program
     - The web console's React apps only
   * - Authentication
     - An api key, in the ``Authorization`` header
     - The browser's Django session, with its CSRF token in the ``X-CSRFToken`` header
   * - Compatibility
     - Semantic versioning: a breaking change needs a new major version
     - None: an endpoint changes with the page that calls it
   * - Documented in
     - The OpenAPI document, at ``/docs/openapi/``
     - This page, and each endpoint's docstring
   * - Shape
     - Resources and commands
     - Whatever the page needs, e.g. one dashboard widget's rows

Both call the same models, brokers and helpers. A generic operation that other clients would want
belongs in ``/api/v1/`` too.

Layout
------

Each Django app mounts its endpoints at ``/api/web/<app label>/``, from its own
``api/web/urls.py``, beside its ``api/v1/urls.py``. :mod:`smarter.apps.api.web.urls` includes them
all, and :mod:`smarter.apps.api.urls` mounts it at ``web/``. Each module has a reverse names class,
``<App>ApiWebReverseNames``, whose ``namespace`` is ``api:web:<app>`` and whose names are derived
from the view classes, as :doc:`ADR-032 </adr/032-url-names>` describes.

A React app never builds these urls itself. The Django view that renders its page reverses the url
and passes it to the app in an attribute of its root element, as
:doc:`Django-React Integration <react-integration>` describes:

.. code-block:: python

    from smarter.apps.guardrail.api.web.urls import GuardrailApiWebReverseNames
    from smarter.lib.django.shortcuts import reverse

    url = reverse(GuardrailApiWebReverseNames.namespace, GuardrailApiWebReverseNames.listview_all)
    # "/api/web/guardrail/listview/"

The resource lists
------------------

Every resource list page has the same five endpoints, all POSTs, served by a
:class:`~smarter.lib.django.listview.SmarterListApiView` and its clone, rename and delete views.
The actions are siblings of ``listview/``, so a React app derives them from its list url with
``actionUrl()`` in ``@smarter/common``.

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Path
     - Does
   * - ``listview/``, ``listview/<owned|shared|all>/``
     - One page of the list. See :doc:`List Pagination, Search and Sorting <lib/django/pagination>`.
   * - ``clone/<id>/<new_name>/``
     - Copies the resource for the user.
   * - ``rename/<id>/<new_name>/``
     - Renames it.
   * - ``delete/<id>/``
     - Deletes it, unless something uses it.

.. list-table::
   :header-rows: 1
   :widths: 30 40 30

   * - List
     - Prefix
     - Reverse names
   * - API Keys
     - ``/api/web/authtoken/``
     - ``AuthTokenApiWebReverseNames``
   * - Budgets
     - ``/api/web/account/budget/`` (``listview/`` and ``delete/`` only)
     - ``AccountApiWebReverseNames``
   * - Connections
     - ``/api/web/connection/``
     - ``ConnectionApiWebReverseNames``
   * - Custom Domains
     - ``/api/web/llmclient/custom-domains/``
     - ``LLMClientApiWebReverseNames``
   * - Guardrails
     - ``/api/web/guardrail/``
     - ``GuardrailApiWebReverseNames``
   * - Infrastructure resources
     - ``/api/web/infrastructure/`` (``listview/`` only)
     - ``InfrastructureApiWebReverseNames``
   * - LLMClients (the workbench)
     - ``/api/web/prompt/``
     - ``PromptApiWebReverseNames``
   * - LLMHosts
     - ``/api/web/llmhost/``
     - ``LLMHostApiWebReverseNames``
   * - LLMHost Computes
     - ``/api/web/llmhost/compute/``
     - ``LLMHostApiWebReverseNames``
   * - LLM Tools
     - ``/api/web/llmtool/``, plus ``listview/extensions/``
     - ``PluginApiWebReverseNames``
   * - MCPClients
     - ``/api/web/mcpclient/``
     - ``MCPClientApiWebReverseNames``
   * - Orchestrators
     - ``/api/web/orchestrator/``
     - ``OrchestratorApiWebReverseNames``
   * - Providers
     - ``/api/web/provider/``
     - ``ProviderApiWebReverseNames``
   * - Proxies
     - ``/api/web/proxy/``, when ``SMARTER_ENABLE_PROXY`` is true
     - ``ProxyApiWebReverseNames``
   * - Secrets
     - ``/api/web/secret/``
     - ``SecretApiWebReverseNames``
   * - Vector Searches
     - ``/api/web/vectorsearch/``
     - ``VectorsearchApiWebReverseNames``
   * - Vector Stores
     - ``/api/web/vectorstore/``, when ``SMARTER_ENABLE_VECTORSTORE`` is true
     - ``VectorstoreApiWebReverseNames``

Each list's console page stays at its own path (``/guardrail/``, ``/secret/``, ...). Its view class
is named after its list api's, e.g. ``GuardrailListView`` for ``GuardrailListApiView``, which is how
:func:`~smarter.lib.django.listview.listview_registry` pairs them.

The session
-----------

``GET /api/web/session/`` tells the console who is using it and how the platform is set up, in one
call: the signed-in user, the account the console acts for, the platform's branding, which ways to
sign in are offered, which optional features are on, the languages, the state of the welcome dialog
and the onboarding hints, and the sidebar's badge counts. A visitor who isn't signed in gets the same
response with ``user``, ``account``, ``onboarding``, ``welcome`` and ``badges`` set to ``null``, which
is all that the sign-in pages need. It is the one GET of this api, so that the console can call it
before it has a CSRF token, and it sets the CSRF cookie. It is never cached.

The single-page console (:doc:`ADR-035 </adr/035-single-page-app>`) calls it when it starts, and
again after the user signs in, signs out or changes profile. Its response is
:class:`~smarter.apps.api.web.session.contract.ConsoleSession`, whose JSON Schema,
``console-session.schema.json``, is generated by ``manage.py export_console_session_schema``. A test
fails if the committed copy is out of date.

Signing in
----------

The console's sign-in pages call the account api, under ``/api/web/account/``. Signing in, signing out
and activating an account answer with the new session, so that the console needn't ask for it again. A refused
request answers with :class:`~smarter.apps.account.api.web.contract.AccountErrors`: a message for the
whole form, and the messages of each field, which the console shows beside it.

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Path
     - Does
   * - ``login/``
     - Signs in with an email address and password. An unknown address and a wrong password get the
       same answer, so that it doesn't reveal which addresses have accounts. The right password of an
       account that isn't activated yet gets ``403``, and a message that says so.
   * - ``logout/``
     - Signs out. The console's sign-out, and the user menu's **Sign Out**, call it.
   * - ``register/``
     - Creates an inactive user, and emails them a link to activate their account, while the
       ``ENABLE_ACCOUNT_REGISTRATION`` switch is on; otherwise ``404``. The password must pass Django's
       password validators.
   * - ``activate/<uidb64>/<token>/``
     - Activates the account of an emailed link, and signs its user in. Signing in uses the link up.
   * - ``activation-resend/``
     - Emails a new activation link, and answers the same whether or not the address has an account
       that is waiting to be activated.
   * - ``password-reset-request/``
     - Emails a password reset link, and answers the same whether or not the address has an account.
   * - ``password-reset/<uidb64>/<token>/``
     - ``GET`` checks an emailed link; ``POST`` sets the new password, which must pass the validators.

Signing in, signing up and asking for an activation or password reset link are limited to ten a
minute per IP address, by :class:`~smarter.lib.drf.throttling.SmarterCredentialsRateThrottle`, on top
of the api's general rate limits. Every ``POST`` needs the CSRF token that the session api sets. Social
sign-in stays a redirect flow, through ``/social-auth/``. The emailed links keep their paths, which the
console serves: ``/account/activate/<uidb64>/<token>/`` and ``/password-reset-link/<uidb64>/<token>/``.

A user who signs up with a password proves that the email address is theirs by following the activation
link (:mod:`smarter.apps.account.activation`). Users that social sign-in creates are inactive too, but an
administrator activates them, and they can't ask for an activation link: see ``SOCIAL_AUTH_CREATE_USERS``
in ``settings/base.py``. The pipeline sends them to ``/account/inactive/`` meanwhile, which the console
serves, as it does ``/account/already-associated/``, for a social account that belongs to another user.

The other endpoints
-------------------

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Path
     - Does
   * - ``/api/web/dashboard/my-resources/``, ``service-health/``, ``charges/``, ``budgets/``,
       ``budgets/<record locator>/series/``, ``activity/``, ``getting-started/``,
       ``quick-actions/``, ``search/``
     - The dashboard's widgets, and its global search. See :doc:`Dashboard <react-integration/dashboard>`.
   * - ``/api/web/dashboard/resource/<kind>/<record locator>/``
     - A resource's manifest, hierarchy and dependents, for a list row's detail. See
       :doc:`Resource Detail <smarter-dashboard/resource_detail>`.
   * - ``/api/web/dashboard/welcome/``, ``welcome/dismiss/``, ``onboarding/seen/``
     - The welcome card and the onboarding tour.
   * - ``/api/web/dashboard/passthrough/providers/``
     - The Prompt Passthrough's providers and their models, when
       ``ENABLE_DASHBOARD_PASSTHROUGH_PROMPT`` is true.
   * - ``/api/web/dashboard/logs/stream/``
     - The user's server log stream, when ``SMARTER_ENABLE_DASHBOARD_SERVER_LOGS`` is true.
   * - ``/api/web/dashboard/terminal/ticket/``
     - A one-time ticket that opens the Terminal's WebSocket.
   * - ``/api/web/llmtool/extensions/``
     - The Extensions console: ``list/``, ``registry/``, ``check-updates/``, ``install/``,
       ``upload/`` and ``accounts/``, then each extension's ``<slug>/``, with its ``enable/``,
       ``disable/``, ``update/``, ``rollback/``, ``configure/``, ``availability/`` and
       ``uninstall/``. Those six fixed names are reserved, so no extension's slug can be one of
       them.

Not yet in the web console api
------------------------------

A few console endpoints remain beside their pages:

- the workbench's chat endpoints, ``/workbench/llm-clients/<hashed_id>/config/`` and ``prompt/``,
  which a deployed LLMClient's own host serves too, and its Deployment tab's api key actions;
- the user menu's profile image and profile endpoints, under ``/account/dashboard/``;
- the Terminal's WebSocket, ``ws/terminal/``.

Adding an endpoint
------------------

1. Write the view, e.g. a :class:`~smarter.lib.django.listview.SmarterListApiView` subclass or a
   ``SmarterAuthenticatedNeverCachedWebView`` that returns JSON.
2. Route it in the app's ``api/web/urls.py``, named through its ``<App>ApiWebReverseNames`` class.
   An app that has none yet copies ``smarter/apps/guardrail/api/web/urls.py``, and adds itself to
   :mod:`smarter.apps.api.web.urls`, behind the same feature flag as its page, if it has one.
3. Reverse the url in the page's view, and pass it to the React app in its root element's
   attributes.
4. Test it through the class, and assert its path once. A resource list's tests get all five
   endpoints from :class:`~smarter.lib.unittest.resource_views.ResourceViewsTestMixin`, given
   ``web_reverse_names``.

Technical Reference
-------------------

.. automodule:: smarter.apps.api.web
    :members:

.. automodule:: smarter.apps.api.web.const
    :members:

.. automodule:: smarter.apps.api.web.urls
    :members:
    :undoc-members:

.. automodule:: smarter.apps.api.web.session.contract
    :members:

.. automodule:: smarter.apps.api.web.session.views
    :members:

.. automodule:: smarter.apps.account.api.web.contract
    :members:

.. automodule:: smarter.apps.account.api.web.views
    :members:

.. automodule:: smarter.apps.account.sign_in
    :members:

.. automodule:: smarter.apps.account.activation
    :members:

.. automodule:: smarter.apps.account.password_reset
    :members:

.. automodule:: smarter.apps.account.email_links
    :members:
