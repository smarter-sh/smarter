Backend Development: Four-Week Online Course
============================================

A four-week online course on backend development with Python, Django, Django REST Framework and
Pydantic, taught on Smarter's code base, with twelve 30-minute recorded lectures and a 90-minute
live session each week. Week 1 covers Django and the ORM, week 2 the API layer, week 3 manifests,
models and testing, and week 4 background work, caching and performance. The course ends with a
new feature, or a new resource kind, delivered as a pull request. See :doc:`../course-formats` for
the format, the grading scale and the course policies, and :doc:`../backend-development` for an
overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Software developers who know Python and want to learn Django and the patterns of a large
       backend.
   * - **Deployment**
     - Each student runs Smarter from source on their own computer. Week 1 includes time for
       installation.
   * - **Workload**
     - 3 hours of instruction and 4 to 6 hours of assignments each week.
   * - **Cost**
     - Free, apart from small model charges when students chat with their LLMClients.

Learning Objectives
-------------------

By the end of the course, students can:

1. Explain the Django request lifecycle, and navigate a large Django project.
2. Write efficient ORM queries, and find and fix query performance problems.
3. Build REST endpoints with Django REST Framework, with authentication, permissions and
   consistent errors.
4. Model data and contracts with Pydantic, and explain the broker layer that connects manifests to
   models.
5. Add fields and resources end to end, with migrations, tests and documentation.
6. Write management commands, Celery tasks and cached functions, and test them.

Technical Prerequisites
-----------------------

- **Required:** Python: functions, classes, decorators, exceptions, type hints and virtual
  environments.
- **Required:** Git and GitHub: clone, branch, commit, push and pull requests.
- **Required:** the Linux or macOS command line, and Docker basics.
- **Required:** HTTP and JSON.
- **Required by the end of week 1:** Smarter installed from source, following the
  :doc:`Developer Setup Guide </smarter-framework/guides/developer-setup>`.
- **Helpful:** SQL and relational databases, YAML, and Visual Studio Code with the Python
  extension.

Schedule
--------

.. list-table::
   :header-rows: 1
   :widths: 10 18 72

   * - Week
     - Item
     - Content
   * - 1
     - Lecture 1
     - **Installing Smarter from source.** What each container does, the ``Makefile``, and how to
       get code changes into the containers.
   * - 1
     - Lecture 2
     - **Django in one picture.** Projects, apps, settings, URLs, middleware, views, models and the
       ORM. The structure of Smarter's apps.
   * - 1
     - Lecture 3
     - **The ORM in depth.** Querysets, relationships, aggregation, ``select_related``,
       ``prefetch_related``, and the N+1 query problem.
   * - 1
     - Live session 1
     - Installation triage, then an ORM exploration in the Django shell, in pairs. Start
       Assignment 1.
   * - 2
     - Lecture 4
     - **Django REST Framework.** Serializers, views, routers and the browsable API.
   * - 2
     - Lecture 5
     - **Authentication and permissions.** Sessions, API keys, and how Smarter scopes every
       request to an account. :doc:`/smarter-framework/smarter-api/authentication`.
   * - 2
     - Lecture 6
     - **Errors, versioning and documentation.** Smarter's
       :doc:`error format </smarter-framework/smarter-api/error-handling>`,
       :doc:`API versioning </adr/023-api-versioning>`, rate limiting and Swagger.
   * - 2
     - Live session 2
     - Review of Assignment 1. Live trace of an ``apply`` request with a debugger. Start
       Assignment 2.
   * - 3
     - Lecture 7
     - **Pydantic.** Models, validators, serialization, and
       :doc:`ADR 031 </adr/031-pydantic-over-json>` on Pydantic over raw JSON.
   * - 3
     - Lecture 8
     - **Manifests and brokers.** The :doc:`broker model </smarter-framework/smarter-broker-model>`,
       from YAML to Pydantic to the Django model and back.
   * - 3
     - Lecture 9
     - **Testing.** Django's test runner, ``SmarterTestBase``, fixtures, cleanup without
       transaction rollback, mocking external calls, and coverage.
   * - 3
     - Live session 3
     - Review of Assignment 2. Live addition of a field, with tests. Capstone proposals discussed.
       Start Assignment 3.
   * - 4
     - Lecture 10
     - **Management commands.** ``SmarterCommand``, arguments, exit codes, and built-in data.
   * - 4
     - Lecture 11
     - **Background work.** Celery tasks, the beat scheduler, retries, and why tasks must be
       idempotent. :doc:`ADR 030 </adr/030-task-queues>`.
   * - 4
     - Lecture 12
     - **Caching and performance.** Redis, ``@cache_results``, what to cache and what never to
       cache, and profiling a slow view.
   * - 4
     - Live session 4
     - Capstone presentations: each student walks through their pull request for 6 minutes, with
       2 minutes of review questions.

Assignments 1 to 3 are due before the next live session. Assignment 4 is due in the middle of week
4. The capstone proposal is due before Live session 3, and the capstone at the start of Live
session 4.

Graded Assignments
------------------

Assignment 1: App Map and ORM Queries
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students document the structure of the ``secret`` app, and answer eight questions about the data
with ORM queries in the Django shell, including two that need aggregation.

**Turn in:** a Markdown file in their fork with the map and the shell session.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - App map
     - 6
     - Every file explained, with connections to the project.
     - Files missing or misdescribed.
   * - Queries
     - 8
     - All eight correct, using aggregation where needed.
     - Several wrong, or done in Python loops.
   * - Clarity
     - 6
     - Organized as a guide for a newcomer.
     - Disorganized.

Assignment 2: Request Trace and Query Optimization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students trace an ``apply`` request as a sequence diagram, then find a view or serializer whose
query count grows with the data, and reduce it, measuring before and after.

**Turn in:** the diagram, and a pull request against their fork with the optimization and a test
using ``assertNumQueries``.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Trace
     - 6
     - Correct, with file and function names, confirmed with a debugger.
     - Steps missing.
   * - Optimization
     - 6
     - Constant query count, results unchanged.
     - Fewer queries, but still growing.
   * - Measurement and test
     - 5
     - Before and after counts; test locks in the improvement.
     - No measurement or test.
   * - Explanation
     - 3
     - Explains the cause of the extra queries.
     - Not explained.

Assignment 3: A New Field
~~~~~~~~~~~~~~~~~~~~~~~~~

Students add an optional, validated field to a resource of their choice, end to end, with tests and
documentation.

**Turn in:** a pull request against their fork, with passing tests and hooks.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Completeness
     - 6
     - Pydantic model, Django model, migration, broker and docs updated.
     - A layer missing.
   * - Validation
     - 4
     - Invalid values rejected with a clear error.
     - No validation.
   * - Tests
     - 6
     - Validation, round trip and invalid input tested; app tests pass.
     - Few tests, or existing ones broken.
   * - Conventions
     - 4
     - Matches the surrounding code; pre-commit passes.
     - Inconsistent, or hooks fail.

Assignment 4: A Command and a Scheduled Task
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students write a management command that reports API keys unused for a given number of days, and a
Celery beat task that runs the same check daily and logs a warning for each one.

**Turn in:** a pull request against their fork with the command, the task, the schedule entry and
tests.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Shared logic
     - 4
     - Command and task share one function.
     - Logic duplicated.
   * - Command
     - 5
     - Arguments, help, exit codes and error handling.
     - Crashes on bad input.
   * - Task
     - 5
     - Idempotent, scheduled, and logs clearly.
     - Not scheduled, or not idempotent.
   * - Tests
     - 6
     - Command and task tested, with time controlled.
     - Tests depend on the clock.

Capstone Projects
-----------------

Students choose one, propose it before Live session 3, and present the pull request in Live
session 4.

Capstone A: A New Resource Kind
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Build a complete backend feature in a large code base by following its
established patterns, from manifest to database to API to documentation.

Students add a small new resource kind end to end, following
:doc:`/smarter-framework/guides/developer-feature-checklist` and the ``guardrail`` and ``secret``
apps. A suitable example is a ``Bookmark`` resource that stores a named link with tags, or a
``Note`` resource attached to an LLMClient. It must support ``apply``, ``get``, ``describe`` and
``delete``.

**What students turn in:**

- A pull request with the Django app, Pydantic manifest models, broker, migration, admin, API
  registration, tests and a documentation page.
- An example manifest, and a recording or log of the four commands working.
- Coverage of at least 90% for the new app, shown with ``make coverage`` output.
- A six-minute walkthrough in Live session 4.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Completeness
     - 25
     - All four commands work; every item on the checklist done.
     - Some commands or checklist items missing.
   * - Follows the patterns
     - 20
     - Structure, naming, docstrings and logging match ``guardrail`` and ``secret``.
     - Works, but invents its own patterns.
   * - Tests and coverage
     - 25
     - 90% or more, with meaningful tests of validation, broker and API.
     - Below 90%, or tests that only execute code.
   * - Documentation
     - 15
     - A resource page in the existing structure, with a valid manifest.
     - Missing or incomplete.
   * - Walkthrough
     - 15
     - Explains the design and what was hard.
     - Reads the diff.

Capstone B: A Feature with an API, a Command and a Task
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Build a feature that crosses the layers of a backend, with attention to
performance, security and testability.

Students add usage tracking to Secrets: a "last used" timestamp updated cheaply whenever a secret is
read, reported by ``describe`` and a new read-only API endpoint, and a management command and daily
task that list secrets unused for a configurable number of days. The endpoint returns a Pydantic
response model and is scoped to the caller's account.

**What students turn in:**

- A pull request with the model change and migration, broker, endpoint, command, task, tests and
  documentation.
- A short design note on how reads stay fast.
- A six-minute walkthrough in Live session 4.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Correctness
     - 20
     - Every read path updates the timestamp; command, task and endpoint correct.
     - Read paths missed.
   * - Performance
     - 15
     - Writes throttled or deferred, with the trade-off explained.
     - A database write on every read, unexplained.
   * - Security
     - 15
     - Endpoint scoped to the account, with a test that proves it.
     - Untested scoping.
   * - Tests
     - 25
     - All layers tested, with Celery and time mocked.
     - Partial or clock-dependent.
   * - Code quality, docs and walkthrough
     - 25
     - Follows the patterns; documented; clear walkthrough.
     - Inconsistent or undocumented.

Recommended Texts
-----------------

- **Required:** William S. Vincent, *Django for APIs* (latest edition, self-published), in week 2.
- **Required:** Patrick Viafore, *Robust Python* (O'Reilly, 2021), parts 1 and 2, in week 3.
- **Required:** Harry Percival and Bob Gregory, *Architecture Patterns with Python* (O'Reilly,
  2020, free online at `cosmicpython.com <https://www.cosmicpython.com/>`__), chapters 1 to 6, in
  weeks 3 and 4, to compare its patterns with Smarter's brokers.
- **Reference:** Daniel Feldroy and Audrey Feldroy, *Two Scoops of Django 3.x* (Two Scoops Press,
  2020), and Luciano Ramalho, *Fluent Python* (2nd edition, O'Reilly, 2022).
- **Smarter documentation:** :doc:`/smarter-framework/smarter-broker-model`,
  :doc:`/smarter-framework/smarter-api`, :doc:`/smarter-framework/technologies/pydantic`,
  :doc:`/smarter-framework/guides/developer-feature-checklist`, :doc:`/smarter-framework/getting-started`,
  and the :doc:`Architecture Decision Records </adr>`.

Further Study
-------------

.. include:: further-study.txt
