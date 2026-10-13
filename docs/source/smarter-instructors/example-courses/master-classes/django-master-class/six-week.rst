Django Master Class: Six-Week Online Course
===========================================

A six-week online master class for experienced Django developers, taught on the code of a
production Django platform. Over 18 hours, students take apart the parts of Smarter that go past
Django's defaults: settings validated before Django reads them, a startup sequence that copes
without a database, ten custom middleware classes, many hosts in one site, an ORM extended for
resource ownership, signals, caching, Celery, async streaming over Redis publish-subscribe, API
contracts in Pydantic, OAuth, template tags that host React apps, and the tests and hooks that
keep it all honest. Each topic is a one-hour module: a 30-minute recorded lecture, and a lab done
together in the week's live session on the student's own running copy of Smarter. Week 1 covers
configuration and startup, week 2 the request, week 3 data, week 4 asynchrony and Redis, week 5
APIs and identity, and week 6 the front end, quality and one feature that uses it all. See
:doc:`/smarter-instructors/example-courses/micro-courses/course-formats` for the grading scale and the course policies, and
:doc:`../django-master-class` for an overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Professional Python developers with prior Django experience who maintain, or will maintain,
       a large Django codebase.
   * - **Format**
     - Each week, three 30-minute recorded lectures (1 hour 30) and one 90-minute live session for
       the week's three labs: 3 hours of instruction a week, 18 in all.
   * - **Deployment**
     - Smarter from source on each student's computer, under Docker Compose, working before the
       first live session.
   * - **Workload**
     - 3 hours of instruction and 3 to 5 hours of assignments each week, and 8 to 12 hours for the
       capstone, in week 6 and the week after.
   * - **Cost**
     - Free, plus an LLM provider API key for the modules that send prompts: a few dollars at
       most.

Learning Objectives
-------------------

By the end of the course, students can:

1. Manage a Django project's configuration from the environment through a validated settings
   class, in keeping with the twelve factors.
2. Explain Django's startup sequence and the request's path through middleware, and write
   middleware, host routing and feature flags that fit into them safely.
3. Extend the ORM with abstract models, managers and querysets, including ownership and sharing
   of resources between accounts.
4. Choose between signals, caching, Celery tasks and async views for a given job, and implement
   each correctly, including invalidation, routing and streaming over Redis publish-subscribe.
5. Build APIs with Django REST Framework, Pydantic contracts and custom authentication, and add
   OAuth sign-in.
6. Write template tags, serve complex static assets such as React apps, and style pages with
   Bootstrap or Tailwind.
7. Keep a large codebase healthy with tests, pre-commit hooks and coverage targets.

Technical Prerequisites
-----------------------

- **Required:** proficient Python programming.
- **Required:** prior experience building a Django application: models, views, templates, URLs
  and the admin.
- **Required:** the Model-View-Template pattern, LAMP and similar web application stacks.
- **Required:** working in a terminal with common Linux commands, and Git.
- **Required:** familiarity with `The Twelve-Factor App <https://12factor.net/>`__.
- **Required by the first live session:** Docker, and Smarter running from source as described
  in :doc:`/smarter-framework/guides/developer-setup`.
- **Helpful:** Redis, Celery, and reading React and TypeScript.

Schedule
--------

Students watch the week's three lectures before its live session. Each module is described under
`The Modules`_.

.. list-table::
   :header-rows: 1
   :widths: 10 45 45

   * - Week
     - Lectures
     - Assignment
   * - 1
     - Modules 1 to 3: 12-Factor and settings; the startup sequence; logging.
     - Assignment 1: Configuration, Startup and Logging.
   * - 2
     - Modules 4 to 6: the request and middleware chain; writing middleware; many hosts and
       Waffle.
     - Assignment 2: The Request Pipeline.
   * - 3
     - Modules 7 to 9: customizing the ORM; the user and ownership; signals and receivers.
     - Assignment 3: An Owned Resource.
   * - 4
     - Modules 10 to 12: caching complex objects; Celery and Beat; ASGI and publish-subscribe.
     - Assignment 4: Cached and Asynchronous.
   * - 5
     - Modules 13 to 15: API best practices; OAuth; mixins, enums and data helpers.
     - Assignment 5: An API with a Contract. Capstone choice.
   * - 6
     - Modules 16 to 18: template tags, static assets and styles; testing and quality; the
       terminal window.
     - Capstone, due one week after the last live session.

Live Sessions
~~~~~~~~~~~~~

This course's live sessions differ from the standard session in :doc:`/smarter-instructors/example-courses/micro-courses/course-formats`, because
they hold the labs:

- **15 minutes:** questions on the week's lectures, and common problems seen in the previous
  week's assignment.
- **75 minutes:** the week's three labs, 25 minutes each. The instructor demonstrates the start
  of each lab, then students work in pairs in breakout rooms, sharing one screen.

Students finish any lab that runs over on their own, before starting the week's assignment.
Assignments are due before the next live session.

The Modules
-----------

.. include:: modules.txt

The Modules in the Source Code
------------------------------

.. include:: source-code.txt

Grading
-------

.. list-table::
   :header-rows: 1
   :widths: 60 40

   * - Component
     - Weight
   * - Graded assignments
     - 50% (5 × 10%)
   * - Participation (live sessions and labs)
     - 10%
   * - Capstone project
     - 40%

The grading scale, the rubric levels and the course policies are those of
:doc:`/smarter-instructors/example-courses/micro-courses/course-formats`.

Graded Assignments
------------------

Each assignment builds on the week's labs, on the student's branch of Smarter, and is submitted
as a pull request against their own fork.

Assignment 1: Configuration, Startup and Logging
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students add a validated setting that limits requests per account, write a note that traces the
startup sequence from ``asgi.py`` to the first request with the file and line of each step, and
add a Waffle-switched logger for the code they will write in week 2.

**Turn in:** the pull request, and the two-page trace.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Configuration
     - 6
     - Typed, defaulted and validated in ``smarter_settings``, with a test for an invalid value.
     - Read from ``os.environ`` directly.
   * - Startup trace
     - 8
     - Every step, in order, with references, including what is not yet ready.
     - Steps missing or out of order.
   * - Logging
     - 6
     - Switch and logger registered, records carry the user.
     - ``print()``, or always on.

Assignment 2: The Request Pipeline
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students add a middleware that enforces the week 1 setting, behind a Waffle switch, for the API
host only, and log each refusal with the week 1 logger.

**Turn in:** the pull request, with tests, and a paragraph on where the middleware sits in the
chain and why.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Middleware
     - 8
     - Correct place in the chain, with the reason; short-circuits with a proper response.
     - Appended to the end of ``MIDDLEWARE``.
   * - Hosts and flags
     - 6
     - API host only, and the switch works both ways.
     - Runs everywhere, or hard-coded on.
   * - Tests
     - 6
     - Both sides of the switch and the limit, with ``RequestFactory`` or the test client.
     - None.

Assignment 3: An Owned Resource
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students finish the model of Module 8 with a queryset method of their own, a custom signal sent
when a row is shared, and a receiver that writes an entry to the log.

**Turn in:** the pull request, with tests.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Ownership
     - 8
     - Uses the ownership manager, with tests across two accounts and a shared row.
     - Filters by hand.
   * - ORM
     - 6
     - The queryset method chains, and the list page has no N+1 queries.
     - Logic in the view.
   * - Signals
     - 6
     - Declared in ``signals.py``, received in ``receivers.py``, loaded from ``ready()``.
     - Receivers that never connect.

Assignment 4: Cached and Asynchronous
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students add a cached per-account count for the week 3 model, invalidated by receivers, a Celery
task that recalculates it on a Beat schedule, and an event published to Redis and streamed to the
browser whenever it changes.

**Turn in:** the pull request, with tests.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Caching
     - 6
     - Plain-value cache key, invalidated by receivers, tested.
     - Stale values, or a model instance in the key.
   * - Task
     - 6
     - Idempotent, passes ids, on the right queue and schedule.
     - Passes model instances.
   * - Streaming
     - 8
     - Async view, one channel per account, keepalives, published after commit.
     - Polling, or one channel for everyone.

Assignment 5: An API with a Contract
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students expose the week 3 model through an API endpoint whose response is a Pydantic model,
authenticated by API key, validate its fields with the validator of Module 15, and add a step to
the OAuth pipeline that logs each sign-in.

**Turn in:** the pull request, with tests.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Contract
     - 8
     - Built from the model and dumped, with ``extra="forbid"``.
     - A dict validated afterwards.
   * - Authentication
     - 6
     - API key required, with a test for refusal; pipeline step tested.
     - Session only.
   * - Validation
     - 6
     - A reusable validator with tests, and an enumerated class for choices.
     - Validation in the view.

Capstone Projects
-----------------

Students choose one in week 5, work on it in week 6, and submit it one week after the last live
session.

.. include:: capstones.txt

Recommended Texts
-----------------

- **Required:** Daniel Feldroy and Audrey Feldroy, *Two Scoops of Django 3.x* (Two Scoops Press,
  2020): settings in week 1, models, queries, the user model and signals in week 3, and testing
  in week 6.
- **Required:** Adam Wiggins, `The Twelve-Factor App <https://12factor.net/>`__, before week 1.
- **Reference:** William S. Vincent, *Django for Professionals* (latest edition), for deployment,
  security and performance.
- **Reference:** Adam Johnson, *Boost Your Django DX* (2023), on pre-commit and developer tooling,
  and *Speed Up Your Django Tests* (2020).
- **Reference:** Harry Percival and Bob Gregory, *Architecture Patterns with Python* (O'Reilly,
  2020), free at `cosmicpython.com <https://www.cosmicpython.com/>`__.
- **Smarter documentation:** :doc:`/adr`, :doc:`/smarter-framework/guides/12-factor-app`,
  :doc:`/smarter-framework/guides/developer-guidelines`, :doc:`/smarter-platform/url-patterns`
  and :doc:`/smarter-platform/security`.

Further Study
-------------

.. include:: further-study.txt
