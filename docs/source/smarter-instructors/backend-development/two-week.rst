Backend Development: Two-Week Online Course
===========================================

A two-week online course on backend development with Python, Django, Django REST Framework and
Pydantic, taught on Smarter's code base, with six 30-minute recorded lectures and a 90-minute live
session each week. Week 1 covers Django and its API layer, and week 2 covers manifests, models,
testing and background work. See :doc:`../course-formats` for the format, the grading scale and
the course policies, and :doc:`../backend-development` for an overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Software developers who know Python and want to learn Django and the patterns of a large
       backend.
   * - **Deployment**
     - Each student runs Smarter from source on their own computer, installed before Live
       session 1. Live session 1 opens with 15 minutes of installation triage.
   * - **Workload**
     - 3 hours of instruction and 4 to 6 hours of assignments each week.
   * - **Cost**
     - Free, apart from small model charges when students chat with their LLMClients.

Learning Objectives
-------------------

By the end of the course, students can:

1. Explain the Django request lifecycle, and navigate a large Django project.
2. Build and call REST endpoints with Django REST Framework, with authentication and consistent
   errors.
3. Explain how Smarter's brokers turn Pydantic-validated manifests into database rows.
4. Add a field to a resource end to end, with a migration and tests.
5. Write management commands and Celery tasks, and test them.

Technical Prerequisites
-----------------------

- **Required:** Python: functions, classes, decorators, exceptions, type hints and virtual
  environments.
- **Required:** Git and GitHub: clone, branch, commit, push and pull requests.
- **Required:** the Linux or macOS command line, and Docker basics (images, containers,
  ``docker exec`` and ``docker logs``).
- **Required:** HTTP and JSON.
- **Required:** Smarter installed from source, following the
  :doc:`Developer Setup Guide </smarter-framework/guides/developer-setup>`, before Live session 1.
- **Helpful:** SQL, YAML, and Visual Studio Code with the Python extension.

Schedule
--------

.. list-table::
   :header-rows: 1
   :widths: 10 18 72

   * - Week
     - Item
     - Content
   * - 1
     - Lecture 1 (30 min)
     - **Django in one picture.** Projects, apps, settings, URLs, middleware, views, models and the
       ORM. The structure of Smarter's apps, using ``guardrail`` and ``secret``.
   * - 1
     - Lecture 2 (30 min)
     - **The ORM in practice.** Querysets, relationships, ``select_related`` and
       ``prefetch_related``, and the Django shell.
   * - 1
     - Lecture 3 (30 min)
     - **Django REST Framework.** Serializers, views, authentication, permissions, and Smarter's
       :doc:`REST API </smarter-framework/smarter-api>` and error format.
   * - 1
     - Live session 1 (90 min)
     - Installation triage, then a live trace of a ``smarter apply`` request with a debugger. Pairs
       trace a ``describe`` request. Start Assignment 1.
   * - 2
     - Lecture 4 (30 min)
     - **Pydantic, manifests and brokers.** Validation, models and the
       :doc:`broker model </smarter-framework/smarter-broker-model>`.
   * - 2
     - Lecture 5 (30 min)
     - **Models, migrations and tests.** Adding a field, migrations, ``SmarterTestBase``, and
       running tests in the container.
   * - 2
     - Lecture 6 (30 min)
     - **Beyond the request.** Management commands, Celery tasks, the beat scheduler, caching with
       ``@cache_results``, and signals.
   * - 2
     - Live session 2 (90 min)
     - Capstone presentations: each student walks through their pull request for 5 minutes, with
       2 minutes of review questions.

Assignment 1 is due at the end of week 1, Assignment 2 in the middle of week 2, and Assignment 3
and the capstone at the start of Live session 2.

Graded Assignments
------------------

Assignment 1: Request Trace
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students trace an ``apply`` request and a ``describe`` request from the HTTP call to the database,
and draw both as sequence diagrams with file and function names.

**Turn in:** the diagrams and the ``curl`` commands and responses, in a Markdown file in their
fork.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Accuracy
     - 8
     - Every step correct, with file and function names.
     - Steps missing or out of order.
   * - Evidence
     - 4
     - Confirmed with logs or a debugger.
     - Inferred only.
   * - Comparison
     - 4
     - Explains where the two requests share code and where they differ.
     - Two unrelated diagrams.
   * - API calls
     - 4
     - Correct calls and explained responses.
     - Incorrect or unexplained.

Assignment 2: ORM Report
~~~~~~~~~~~~~~~~~~~~~~~~

Students write a function that reports, for each account, the number of resources of each kind,
first naively, then with as few queries as possible, and measure the number of queries of each
version.

**Turn in:** a pull request against their fork with both versions, a test, and the query counts.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Correctness
     - 6
     - Both versions give the same, correct results.
     - Results differ or are wrong.
   * - Optimization
     - 6
     - Uses aggregation or prefetching; query count is constant.
     - Fewer queries, but still one per account.
   * - Measurement
     - 4
     - Query counts measured, for example with ``assertNumQueries``.
     - Guessed.
   * - Test
     - 4
     - Tests results and cleans up its data.
     - No test, or leaves data behind.

Assignment 3: A New Field
~~~~~~~~~~~~~~~~~~~~~~~~~

Students add an optional field to the Guardrail resource end to end, with tests.

**Turn in:** a pull request against their fork, with passing tests and hooks.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Completeness
     - 7
     - Pydantic model, Django model, migration and broker updated.
     - A layer missing.
   * - Tests
     - 6
     - Validation and round trip tested; app tests pass.
     - No tests, or existing tests broken.
   * - Conventions
     - 4
     - Matches the surrounding code; pre-commit passes.
     - Inconsistent, or hooks fail.
   * - Pull request
     - 3
     - Clear description of what, why and how tested.
     - Empty description.

Capstone Projects
-----------------

Students choose one, and present the pull request in Live session 2.

Capstone A: A Feature with an API, a Command and a Task
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Build a feature that crosses the layers of a backend, from model to API to
background work, with tests and documentation.

Students add a "last used" timestamp to Secrets: it is updated when a secret is read by a plugin or
connection, reported by ``describe``, and a management command and a scheduled Celery task list
secrets unused for a configurable number of days.

**What students turn in:**

- A pull request with the model change and migration, the broker and API changes, the command,
  the task, tests and documentation.
- Passing tests (``python manage.py test smarter.apps.secret``) and hooks.
- A five-minute walkthrough in Live session 2.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Correctness
     - 25
     - Timestamp updated in every read path; command and task correct.
     - Some read paths missed.
   * - Design
     - 15
     - Writes are cheap and do not slow reads noticeably; explained.
     - A write on every read, with no thought to cost.
   * - Tests
     - 25
     - Model, API, command and task tested; Celery and time mocked properly.
     - Partial tests, or tests that depend on the clock.
   * - Code quality and docs
     - 20
     - Follows the app's patterns; docstrings and docs page updated.
     - Inconsistent or undocumented.
   * - Walkthrough
     - 15
     - Clear explanation of the design and trade-offs.
     - Reads the diff aloud.

Capstone B: A Read-Only Reporting Endpoint
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Design and build a REST endpoint that is secure, efficient, documented and
tested.

Students add an endpoint under Smarter's API that returns a summary of the caller's account: the
number of resources of each kind, prompts in the last 30 days, and spending against budgets. It
must authenticate with an API key, show only the caller's account, be built from a Pydantic
response model, and appear in the Swagger documentation.

**What students turn in:**

- A pull request with the view, the URL, the Pydantic response model, tests and documentation.
- Example ``curl`` calls and responses.
- A five-minute walkthrough in Live session 2.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Security
     - 25
     - Authenticated, and scoped to the caller's account, with a test that proves it.
     - Authenticated, but leaks other accounts' data or is untested.
   * - Correctness and efficiency
     - 20
     - Correct figures; constant number of queries.
     - Correct, but one query per resource.
   * - API design
     - 15
     - Pydantic response model, consistent with the existing API and errors.
     - Hand-built dictionaries, inconsistent naming.
   * - Tests
     - 25
     - Success, empty account, unauthenticated and other-account cases.
     - Happy path only.
   * - Docs and walkthrough
     - 15
     - Appears in Swagger and the docs; clear walkthrough.
     - Undocumented.

Recommended Texts
-----------------

- **Required:** William S. Vincent, *Django for APIs* (latest edition, self-published). Week 1:
  the chapters on Django REST Framework, serializers, permissions and authentication.
- **Required:** Patrick Viafore, *Robust Python* (O'Reilly, 2021). Week 2: part 1 on types, and
  the chapters on Pydantic and testing.
- **Reference:** Daniel Feldroy and Audrey Feldroy, *Two Scoops of Django 3.x* (Two Scoops Press,
  2020).
- **Smarter documentation:** :doc:`/smarter-framework/smarter-broker-model`,
  :doc:`/smarter-framework/smarter-api`, :doc:`/smarter-framework/technologies/pydantic`,
  :doc:`/smarter-framework/guides/developer-feature-checklist`, and the ADRs on
  :doc:`Django </adr/001-django>`, :doc:`management commands </adr/010-management-commands>`,
  :doc:`caching </adr/018-caching>` and :doc:`task queues </adr/030-task-queues>`.

Further Study
-------------

.. include:: further-study.txt
