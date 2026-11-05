ADR-034: The Web Console Api
============================

Status
------
Accepted

Context
-------
The web console's pages are Django views whose templates host small React apps
(:doc:`ADR-019 <019-react>`), as the
:doc:`Django-React Integration </smarter-framework/developer-reference/react-integration>`
describes. The React apps fetch and change data with POST requests to JSON
endpoints that Django also serves. Those endpoints grew up beside the pages that use them, under each
page's own prefix: ``/guardrail/react-integration/api/listview/``, ``/dashboard/api/my-resources/``,
``/workbench/api/listview/clone/<id>/<new_name>/``, and so on, in about twenty urls modules.

That made the console's boundary invisible. The public api is under ``/api/v1/``, but nothing
separated the console's own JSON endpoints from its pages. A route, an ingress rule, a CORS policy or
an authentication rule couldn't tell them apart, and splitting the console into a separate frontend,
a direction the project wants to keep open, would first need a survey of every urls module.

The endpoints are not part of the public api, and shouldn't be. They are shaped around one page's
needs, change whenever that page does, and authenticate with the browser's Django session and CSRF
token, where ``/api/v1/`` authenticates with an api key and promises compatibility under semantic
versioning (:doc:`ADR-020 <020-semantic-versioning>`, :doc:`ADR-023 <023-api-versioning>`).

Decision
--------
The JSON endpoints that the web console's React apps call are the **web console api**, mounted at
``/api/web/``.

1. **One prefix.** Each Django app mounts its console endpoints at ``/api/web/<app label>/``, e.g.
   ``/api/web/guardrail/listview/``, from its own ``api/web/urls.py``, beside its ``api/v1/urls.py``.
   ``smarter.apps.api.web.urls`` includes them all. Everything the backend serves to a program is
   then under ``/api/``, and everything else is a console page.
2. **Internal and unversioned.** The prefix is ``/api/web/``, not ``/api/v1/web/``, so that the
   console's endpoints are outside the public api's compatibility promise. A change to one needs no
   major version and no upgrade note, as long as the console changes with it. They are not in the
   OpenAPI document.
3. **Session authentication.** The endpoints authenticate with the browser's Django session and its
   CSRF token, as the pages do.
4. **The same names.** Each module follows :doc:`ADR-032 <032-url-names>`: an
   ``<App>ApiWebReverseNames`` class, whose ``namespace`` is ``api:web:<app>``, and names derived from
   the view classes. A list page's actions (``clone/``, ``rename/``, ``delete/``) are siblings of its
   ``listview/``.
5. **No duplicate business logic.** A web console endpoint calls the same models, brokers and helpers
   as the public api. When a generic operation is useful outside the console, such as cloning or
   renaming a resource, it belongs in ``/api/v1/`` too, and the console should eventually call that
   instead (:doc:`ADR-033 <033-dry>`). Page-shaped endpoints, such as the dashboard's widgets, stay in
   ``/api/web/``.

The pages that host the React apps stay where they are. The workbench's chat endpoints
(``/workbench/llm-clients/<hashed_id>/config/`` and ``prompt/``), which a deployed LLMClient's host
serves too, the account dashboard's older form pages, and the terminal's WebSocket are not yet part
of this api.

Alternatives Considered
-----------------------
- **Leave the endpoints beside their pages.** No work, and no visible boundary.
- **``/api/v1/web/``.** One prefix for everything under ``/api/v1/``, but it puts the console's
  page-shaped endpoints under the public api's compatibility promise, so that a dashboard redesign
  would be a breaking api change.
- **Move everything into the public api now.** The cleanest end state for generic operations, but a
  much larger change, and the wrong home for page-shaped endpoints that no other client needs.

Consequences
------------
- **Positive:**

  - The console's backend boundary is one prefix: ``/api/`` is the backend, everything else is a page.
    A routing rule, an authentication policy or a future split of the console can rely on it.
  - The console's endpoints can change with the console, without a breaking-change note.
  - All the console's endpoints are listed in one urlconf, and documented in one place.

- **Negative:**

  - Every endpoint's path changed once. Paths are internal and React apps receive them from Django,
    so only code that reversed or hard-coded them changed with them.
  - Two apis now cover some of the same resources. Rule 5 limits the overlap, but it has to be
    watched.
  - A list page's api and its page are in different urlconfs, so the console's list registry
    (:func:`smarter.lib.django.listview.listview_registry`) pairs them by their view classes' names.

Related ADRs
------------
- :doc:`ADR-006: REST API <006-rest-api>`
- :doc:`ADR-019: React <019-react>`
- :doc:`ADR-020: Semantic Versioning <020-semantic-versioning>`
- :doc:`ADR-023: API Versioning <023-api-versioning>`
- :doc:`ADR-032: Url Names <032-url-names>`
- :doc:`ADR-033: DRY <033-dry>`
