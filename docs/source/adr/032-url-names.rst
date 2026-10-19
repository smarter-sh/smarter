ADR-032: Url Names Derived From View Classes
============================================

Status
------
Accepted

Context
-------
Django names each url pattern with a string, ``path(..., name="...")``, and code finds the url by that
string, with ``reverse()`` or the ``{% url %}`` template tag. Nothing ties the string to the view that
serves the url, so names drift: a view is renamed and its url name isn't, two modules pick the same
convention differently, and a typo in a caller fails only when that line runs.

Smarter has about 60 ``urls.py`` modules, and most of them already solved this the same way: a class
beside the url patterns whose attributes are the names, each computed from the view class with
``to_snake_case(View.__name__)``, and callers that reverse through the class. A survey of the code
found the rest in several older shapes:

- literal names in upper-case constants (``ACCOUNT_LOGIN = "account_login"``) or lower-case ones
  (``chathistory = "chathistory"``), and ``name="..."`` literals with no class at all, mostly in
  ``api/v1`` modules;
- a namespace with a trailing colon (``"api:v1:cli:"``), used as ``namespace + name``, beside
  namespaces without one, used as ``f"{namespace}:{name}"``;
- ``_by_id`` suffixes written with and without their underscore, which gives names such as
  ``llm_client_viewby_id``;
- ``{% url 'namespace:name' %}`` tags in templates, which hard-code the derived string.

Decision
--------
Every url name is derived from the view class that serves it, in one place, and every caller reads it
from there.

1. **The namespace is a constant**, ``namespace`` in the module's ``const.py``. The urls module sets
   ``app_name = namespace``, and its parent includes it with the same constant.
2. **Each urls module has one class of names**, ``<App>ReverseNames`` (``<App>ApiV1ReverseViews`` for
   an api version). Its first attribute is ``namespace``, without a trailing colon.
3. **Each name is** ``to_snake_case(<View>.__name__)``, or the function's ``__name__`` for a function
   view. The attribute's name is the route's role (``listview``, ``deployment_by_hashed_id``), so that
   callers don't change when a view is renamed.
4. **A view with several routes** adds a suffix to its derived name: ``_all``, ``_by_id``,
   ``_by_hashed_id``, each starting with an underscore.
5. **Every** ``path()`` **names its route with a class attribute**, and every caller reverses through
   the class, with :func:`smarter.lib.django.shortcuts.reverse`: the namespaces and the name as
   separate arguments, or, with url kwargs, one string joined with an f-string.
6. **Templates receive urls, not names.** A view or context processor reverses the url and passes it
   in the context.
7. **Code that can run on a deployed LLMClient's host** reverses with
   ``urlconf=settings.ROOT_URLCONF``, because that host's urlconf has none of the console's names, and
   a url that leaves the console is made absolute on the platform's domain.

The newest modules are the reference: ``smarter.apps.guardrail.urls``, ``smarter.apps.llmclient.urls``,
``smarter.apps.prompt.urls`` and ``smarter.apps.guardrail.api.v1.urls``. The ``smarter-url-names``
Agent Skill, in ``skills/``, gives the recipe, and lists the older modules that don't follow it yet.

Alternatives Considered
-----------------------
- **Literal names, by convention.** Django's default. It works while one person writes the code, and
  drifts as soon as several do, which is what the survey found.
- **Names derived from the url path.** Paths change for users' sake (a new prefix, a renamed
  segment), and a path with parameters makes an awkward name.
- **No names: hard-coded paths.** Every route move would be a search through the codebase and the
  templates, with no failure when one is missed.

Consequences
------------
- **Positive:**

  - A name can't drift from its view, and a typo in a caller fails at import, not at runtime.
  - Names are predictable: anyone who knows the view knows its name, and nobody has to choose one.
  - One grep for the class attribute finds every caller of a route.

- **Negative:**

  - Renaming a view renames its url name. Callers that go through the class follow, but a literal
    copy of the old string, in a template or a test, breaks, so a rename must grep for the string too.
  - ``to_snake_case`` splits acronyms into words (``LLMClient`` → ``llm_client``), so the derived
    names are long, and occasionally surprising when read in a log.
  - A urls module must import its views, so a module whose views import it back needs its names
    class in a separate ``names.py``.
  - The older modules remain until someone changes them for another reason.

Related ADRs
------------
- :doc:`ADR-001: Django <001-django>`
- :doc:`ADR-006: REST API <006-rest-api>`
- :doc:`ADR-023: API Versioning <023-api-versioning>`
- :doc:`ADR-025: Templates <025-templates>`
