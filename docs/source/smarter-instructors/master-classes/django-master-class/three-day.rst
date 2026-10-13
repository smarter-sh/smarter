Django Master Class: Three-Day Classroom Course
===============================================

A three-day classroom master class for experienced Django developers, taught on the code of a
production Django platform. Over 18 hours, students take apart the parts of Smarter that go past
Django's defaults: settings validated before Django reads them, a startup sequence that copes
without a database, ten custom middleware classes, many hosts in one site, an ORM extended for
resource ownership, signals, caching, Celery, async streaming over Redis publish-subscribe, API
contracts in Pydantic, OAuth, template tags that host React apps, and the tests and hooks that
keep it all honest. Each topic is a one-hour module, a 30-minute lecture and a 30-minute lab on
the student's own running copy of Smarter. Day 1 covers configuration, startup and the request,
day 2 data, asynchrony and Redis, and day 3 APIs, identity, the front end and quality. See
:doc:`/smarter-instructors/micro-courses/course-formats` for the grading scale and the course policies, and
:doc:`../django-master-class` for an overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Professional Python developers with prior Django experience who maintain, or will maintain,
       a large Django codebase.
   * - **Format**
     - Three days of six hours of instruction, each day six one-hour modules. Breaks and lunch are
       not counted.
   * - **Deployment**
     - Smarter from source on each student's laptop, under Docker Compose, working before day 1.
   * - **Workload**
     - About 2 hours each evening for the day's assignment, and 8 to 12 hours for the capstone in
       the week after the course.
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
- **Required before day 1:** Docker, and Smarter running from source as described in
  :doc:`/smarter-framework/guides/developer-setup`. Send students the instructions at least a
  week ahead, and ask for a screenshot of the running web console.
- **Helpful:** Redis, Celery, and reading React and TypeScript.

Schedule
--------

Each module is described under `The Modules`_.

.. list-table::
   :header-rows: 1
   :widths: 10 30 30 30

   * - Day
     - Morning (3 hours)
     - Afternoon (3 hours)
     - Evening
   * - 1
     - Modules 1 to 3: 12-Factor and settings; the startup sequence; logging.
     - Modules 4 to 6: the request and middleware chain; writing middleware; many hosts and
       Waffle.
     - Assignment 1, due at the start of day 2.
   * - 2
     - Modules 7 to 9: customizing the ORM; the user and ownership; signals and receivers.
     - Modules 10 to 12: caching complex objects; Celery and Beat; ASGI and publish-subscribe.
     - Assignment 2, due at the start of day 3.
   * - 3
     - Modules 13 to 15: API best practices; OAuth; mixins, enums and data helpers.
     - Modules 16 to 18: template tags, static assets and styles; testing and quality; the
       terminal window.
     - Assignment 3, due two days after the course. Capstone choice.

Each day opens with 10 minutes of questions on the previous evening's assignment, taken from the
first lecture's time. The capstone is due one week after the course.

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
     - 45% (3 × 15%)
   * - Participation (labs and questions)
     - 10%
   * - Capstone project
     - 45%

The grading scale, the rubric levels and the course policies are those of
:doc:`/smarter-instructors/micro-courses/course-formats`.

Graded Assignments
------------------

Each assignment builds on the day's labs, on the student's branch of Smarter, and is submitted as
a pull request against their own fork.

Assignment 1: Configuration and the Request
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students add a middleware that enforces a per-account request limit read from a new, validated
setting in ``smarter_settings``. A Waffle switch turns it on, a Waffle-switched logger records
each refusal, and the middleware runs only for the API host.

**Turn in:** the pull request, with tests, and a paragraph on where the middleware sits in the
chain and why.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Configuration
     - 5
     - Typed, defaulted and validated in ``smarter_settings``.
     - Read from ``os.environ`` directly.
   * - Middleware
     - 7
     - Correct place in the chain, with the reason; API host only.
     - Appended to the end of ``MIDDLEWARE``.
   * - Flags and logging
     - 4
     - Switch and logger both registered and working.
     - Hard-coded on.
   * - Tests
     - 4
     - Both sides of the switch and the limit.
     - None.

Assignment 2: An Owned, Cached, Asynchronous Resource
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students finish the model of Module 8: a cached per-account count, invalidated by receivers, a
Celery task that recalculates it on a Beat schedule, and an event published to Redis whenever it
changes.

**Turn in:** the pull request, with tests.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Ownership
     - 5
     - Uses the ownership manager, with a test across two accounts.
     - Filters by hand.
   * - Caching
     - 6
     - Plain-value cache key, invalidated by receivers, tested.
     - Stale values, or a model instance in the key.
   * - Task
     - 5
     - Idempotent, passes ids, on the right queue and schedule.
     - Passes model instances.
   * - Publishing
     - 4
     - One channel per account, published after commit.
     - One channel for everyone.

Assignment 3: An API with a Contract
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students expose the Module 8 model through an API endpoint whose response is a Pydantic model,
authenticated by API key, show it on a console page with a template tag of their own, and bring
everything they have written in the course through the pre-commit hooks and to 90% coverage.

**Turn in:** the pull request, and the coverage report.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Contract
     - 6
     - Built from the model and dumped, with ``extra="forbid"``.
     - A dict validated afterwards.
   * - Authentication
     - 4
     - API key required, with a test for refusal.
     - Session only.
   * - Template tag
     - 4
     - Small, tested, and used on a page.
     - Logic in the template.
   * - Quality
     - 6
     - Hooks pass, 90% coverage.
     - Hooks skipped.

Capstone Projects
-----------------

Students choose one at the end of day 3, and submit it one week after the course.

.. include:: capstones.txt

Recommended Texts
-----------------

- **Required:** Daniel Feldroy and Audrey Feldroy, *Two Scoops of Django 3.x* (Two Scoops Press,
  2020), the chapters on settings, models, queries, the user model, signals and testing, before
  and during the course.
- **Required:** Adam Wiggins, `The Twelve-Factor App <https://12factor.net/>`__, before day 1.
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
