Django Master Class
===================

**Why Smarter.** Most Django courses end where real projects begin: one host, one settings file,
the default ``User`` model, synchronous views and a ``models.py`` with no manager of its own.
Smarter is a production Django platform that has had to go past every one of those defaults, and
its code is public. It serves a web console, an API, and every deployed chatbot on a host of its
own, from `one site with many hosts
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/hosts.py>`__. It
validates every setting with a `Pydantic Settings class
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/common/conf/settings.py>`__
before Django reads it. It extends the ORM with an `ownership manager
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/account/models/metadata_with_ownership.py>`__
that makes every resource belong to an account and lets accounts share them. It runs ten
`custom middleware
<https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/lib/django/middleware>`__
classes, Celery workers on two queues and a Beat schedule, `streams LLM progress
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/prompt/progress.py>`__ from
an async ASGI view, and uses Redis for publish-subscribe as well as caching. Its web console's
pages are React apps that Django hosts through `a template tag of its own
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/lib/django/templatetags/smarter_react_templatetag_manager.py>`__.

Each of these is a decision that an experienced Django developer will meet sooner or later, and
each is taught here from code that runs in production, with its tests, its docstrings and the
:doc:`Architecture Decision Record </adr>` that explains it. Students read the code, change it,
break it, and test it, on their own copy of Smarter running in Docker.

**What the course covers.** Eighteen one-hour modules, each a 30-minute lecture and a 30-minute
lab, in six themes:

- **Configuration and startup.** Django and the twelve factors; settings managed by
  ``smarter.common.conf`` rather than by settings files alone; the app startup sequence,
  ``AppConfig.ready()``, and why the database and the cache may not be ready when it runs; and
  getting more out of Python logging.
- **The request.** The request object and how middleware mutates it; the middleware execution
  chain; writing middleware of your own; many hosts in one site with ``django-hosts``; and
  feature flags with Waffle.
- **Data.** Customizing the ORM with managers, querysets and abstract models; customizing the
  user with a profile model; resource ownership and shared resources; and signals and receivers.
- **Asynchrony and Redis.** Caching complex objects; Celery and Celery Beat; asynchronous ASGI
  request handling; and Redis publish-subscribe.
- **APIs and identity.** API best practices with Django REST Framework, Pydantic for API
  contracts, and custom authentication; OAuth with Python Social Auth; and the mixins,
  enumerated classes and Django data helpers (dates and times, conversion, validators and files)
  that hold a large codebase together.
- **Front end, quality and the whole.** Writing template tags; serving complex static assets such
  as React apps; Bootstrap and Tailwind; testing; pre-commit and coverage; and, to finish, one
  feature that uses nearly all of the above: the web console's terminal window.

**Look at.**

- `smarter/smarter/common/conf/ <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/common/conf>`__
  and `smarter/smarter/settings/ <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/settings>`__,
  configuration from environment to Django.
- `smarter/smarter/lib/django/ <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/lib/django>`__,
  the middleware, abstract models, Waffle helpers and template tags.
- `smarter/smarter/apps/account/models/ <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/account/models>`__,
  the user profile and the ownership manager.
- `smarter/smarter/apps/dashboard/views/terminal_emulator/ <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/dashboard/views/terminal_emulator>`__
  and `smarter/react/packages/smarter-terminal-emulator/ <https://github.com/smarter-sh/smarter/tree/main/smarter/react/packages/smarter-terminal-emulator>`__,
  the terminal window, end to end.

Each course plan lists every file that it uses, module by module, under *The Modules in the
Source Code*.

**Read.** :doc:`/adr`, :doc:`/smarter-framework/guides/12-factor-app`,
:doc:`/smarter-framework/guides/developer-setup`, :doc:`/smarter-framework/guides/developer-guidelines`,
:doc:`/smarter-platform/url-patterns`, :doc:`/smarter-platform/security`.

**Exercises.**

- Add a setting to ``smarter_settings``, with a type, a default and validation, and follow it from
  the environment to the code that reads it.
- Write a middleware that adds an attribute to the request, place it in the chain, and show what
  the middleware before and after it can see.
- Give a new model the ownership manager, and test that one account cannot read another
  account's rows unless they are shared.
- Cache an expensive query with ``@cache_results``, and invalidate it from a ``post_save``
  receiver.
- Publish an event to Redis from a Celery task, and stream it to the browser from an async view.
- Add an API endpoint whose response is a Pydantic model, authenticated by API key, with tests
  that cover it to 90%.

**Course plans.** Two complete, ready-to-teach plans of 18 hours each, with a schedule, graded
assignments and rubrics, two capstone projects, recommended texts, further study and technical
prerequisites. This course is longer than the others in this guide, and has formats of its own,
described in each plan. The grading scale and the course policies are those of
:doc:`/smarter-instructors/example-courses/micro-courses/course-formats`.

.. toctree::
   :maxdepth: 1

   Three-day classroom course: 18 hours <django-master-class/three-day>
   Six-week online course: 18 hours <django-master-class/six-week>

See the :doc:`Smarter Instructor Guide </smarter-instructor>` to install Smarter and set up
a class.
