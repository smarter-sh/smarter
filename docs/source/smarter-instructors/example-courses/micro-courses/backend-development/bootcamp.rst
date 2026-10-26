Backend Development: Classroom Bootcamp
=======================================

An eight-hour classroom bootcamp on backend development with Python, Django, Django REST Framework
and Pydantic, taught on Smarter's code base. Smarter is a large Django project, with eighteen apps
in `smarter/smarter/apps/ <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps>`__
that share one deliberately rigid layout, more than five thousand unit tests, and patterns that
tutorial projects never reach: a `broker layer
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/lib/manifest/broker/abstract_broker_class.py>`__
that turns YAML manifests into database rows, Pydantic models for every manifest and contract, a
Pydantic `Settings
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/common/conf/settings.py>`__ class,
Celery workers and a `beat schedule
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/workers/celerybeat.py>`__, and
caching with `@cache_results
<https://github.com/smarter-sh/cache-results/blob/main/src/cache_results/decorators.py>`__. The
``guardrail`` app, the newest and cleanest, is the reference that the labs read and change. Students
trace a request through it, add a field to a resource end to end, and write a management command,
with tests. See :doc:`../course-formats` for the standard bootcamp day, the grading scale and the
course policies, and :doc:`../backend-development` for an overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Software developers who know Python and want to learn Django and the patterns of a large
       backend.
   * - **Deployment**
     - Each student runs Smarter from source on their own laptop. The installation must be done
       and working **before** the bootcamp.
   * - **Cost**
     - Free, apart from model charges when students chat with their LLMClients: less than $1 USD
       each with a small model.

Learning Objectives
-------------------

By the end of the bootcamp, students can:

1. Explain the request lifecycle in Django: URL routing, middleware, views, serializers, models and
   the ORM.
2. Read and navigate a large Django project that follows a consistent app structure.
3. Explain how Smarter's broker layer turns a YAML manifest, validated by Pydantic, into database
   rows.
4. Add a field to a resource end to end: Pydantic model, Django model, migration, broker and tests.
5. Write a Django management command, and a unit test for it.

Technical Prerequisites
-----------------------

- **Required:** Python: functions, classes and inheritance, decorators, exceptions, type hints and
  virtual environments.
- **Required:** Git: clone, branch, commit, diff and push, and a GitHub account.
- **Required:** the Linux or macOS command line: navigating directories, environment variables,
  running scripts.
- **Required:** Docker basics: what an image and a container are, ``docker ps``, ``docker logs``
  and ``docker exec``.
- **Required:** HTTP and JSON: methods, status codes, headers, request and response bodies.
- **Required:** Smarter installed from source and running, following the
  :doc:`Developer Setup Guide </smarter-framework/guides/developer-setup>`. Allow an hour, and
  ask students to send a screenshot of ``docker ps`` beforehand.
- **Helpful:** SQL and relational databases, YAML, and an editor such as Visual Studio Code with
  the Python extension.

Schedule
--------

The files that the lectures refer to are listed in full under `Smarter in the Source Code`_.

.. list-table::
   :header-rows: 1
   :widths: 8 8 84

   * - Block
     - Min
     - Content
   * - 1
     - 45
     - **Lecture 1: Django in one picture.** Projects and apps, settings, URL routing, middleware,
       views, templates, models and the ORM. How Smarter's apps in ``smarter/smarter/apps/`` follow
       one rigid structure, using ``guardrail`` and ``secret`` as the examples.
   * - 2
     - 45
     - **Lab 1: Find your way around.** Use the Django shell (``python manage.py shell`` in the
       ``smarter-app`` container) to query guardrails and secrets, follow a URL to its view, and
       map the files of the ``secret`` app. Produces Assignment 1.
   * - 3
     - 45
     - **Lecture 2: APIs with Django REST Framework.** Serializers, views and viewsets,
       authentication and permissions. Smarter's :doc:`REST API </smarter-framework/smarter-api>`,
       its API key authentication and its error format.
   * - 4
     - 45
     - **Lab 2: Trace a request.** Send an ``apply`` request with ``curl`` and an API key, then
       follow it through the URL route, the DRF view, the broker and the model, with log lines and
       a debugger. Produces Assignment 2.
   * - 5
     - 45
     - **Lecture 3: Pydantic and manifests.** Data validation, models, field validators, and why
       Smarter models every manifest and API contract with Pydantic
       (:doc:`ADR 031 </adr/031-pydantic-over-json>`). The
       :doc:`broker model </smarter-framework/smarter-broker-model>`.
   * - 6
     - 45
     - **Lecture 4: Models and migrations.** Fields, relationships, ``Meta`` options, and how
       migrations work. Adding a field to a resource: the checklist of files it touches, and why
       Smarter adds a new migration, rather than regenerating ``0001_initial.py``, for an app that
       holds production data.
   * - 7
     - 45
     - **Lab 3: Add a field.** Add an optional field to the Guardrail manifest, through the
       Pydantic model, Django model, migration and broker, and show it round-trip through
       ``apply`` and ``describe``. Produces Assignment 3.
   * - 8
     - 45
     - **Lecture 5: Testing Django.** Django's test runner, Smarter's ``SmarterTestBase``, fixtures
       created once per class, cleaning up without transaction rollback, and running tests in the
       container.
   * - 9
     - 45
     - **Lab 4: Test what you built.** Write tests for the new field: manifest validation, broker
       round trip and an invalid value. Ungraded, but leads into the capstone.
   * - 10
     - 45
     - **Lecture 6: Beyond the request.** Management commands, Celery tasks and the beat
       scheduler, caching with ``@cache_results``, and signals. Reading
       ``smarter/smarter/apps/account/management/commands/``.
   * - 11
     - 30
     - **Capstone kickoff.** Students choose a capstone, create a branch, and write a plan of the
       files they will change.

Smarter in the Source Code
--------------------------

.. include:: source-code.txt

Graded Assignments
------------------

Assignment 1: App Map
~~~~~~~~~~~~~~~~~~~~~

Students document the structure of the ``secret`` app: what each file and folder holds, and how it
connects to the rest of Smarter, and answer five questions with queries in the Django shell.

**Turn in:** a Markdown file in their fork with the map and the shell session.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Structure
     - 6
     - Every file and folder explained correctly.
     - Several files missing or misdescribed.
   * - Connections
     - 4
     - Shows how the app's URLs, broker and models plug into the project.
     - The app is described in isolation.
   * - Shell queries
     - 6
     - All five answered with correct ORM queries.
     - Queries wrong or answers copied from the web console.
   * - Clarity
     - 4
     - A newcomer could use it as a guide.
     - Disorganized.

Assignment 2: Request Trace
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students trace one ``apply`` request from the HTTP call to the database row, and draw it as a
sequence diagram, naming the file and function at each step.

**Turn in:** the diagram (Mermaid, PlantUML or an image) and the ``curl`` command and response.

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
     - Confirmed with log lines or a debugger.
     - Inferred from reading only.
   * - Diagram
     - 4
     - Readable, with request and response shown.
     - Cluttered or one-directional.
   * - API call
     - 4
     - Correct ``curl`` with an API key, and the response explained.
     - Incorrect call, or response unexplained.

Assignment 3: A New Field
~~~~~~~~~~~~~~~~~~~~~~~~~

Students add an optional field to the Guardrail resource, end to end.

**Turn in:** a pull request against their own fork.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Completeness
     - 8
     - Pydantic model, Django model, migration and broker all updated.
     - One layer missing, so the field is lost on the round trip.
   * - Round trip
     - 4
     - ``apply`` then ``describe`` returns the field.
     - Not demonstrated.
   * - Conventions
     - 4
     - Naming, docstrings and style follow the existing code; pre-commit passes.
     - Inconsistent with neighbors, or hooks fail.
   * - Pull request
     - 4
     - Clear description of what, why and how it was tested.
     - Empty or one-line description.

Capstone Projects
-----------------

Students choose one. Capstones are due one week after the bootcamp, as a pull request against their
own fork.

Capstone A: A Field with Validation and Tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Make a complete, tested, documented change to a resource, as a
professional pull request.

Students extend Assignment 3 into a feature: the new field gets validation rules (with clear error
messages), is used by the code (for example a guardrail ``owner`` email that appears in the
journal entry when it triggers), and is covered by tests and documentation.

**What students turn in:**

- A pull request with the code, migration, tests and an update to the Guardrail page in
  ``docs/source/``.
- Passing tests for the app (``python manage.py test smarter.apps.guardrail``) and passing
  pre-commit hooks, shown in the pull request.
- A short design note in the pull request description.

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
     - Works end to end, including invalid input.
     - Works for the happy path only.
   * - Tests
     - 25
     - Validation, round trip and use are tested; the app's tests all pass.
     - Few tests, or existing tests broken.
   * - Code quality
     - 20
     - Follows the app's patterns, with docstrings and type hints.
     - Works, but unlike the surrounding code.
   * - Documentation
     - 15
     - The docs page explains the field, with an example.
     - No documentation.
   * - Pull request
     - 15
     - Clear description, small focused commits.
     - One large commit with no description.

Capstone B: A Management Command
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Write an operational tool that uses the ORM safely, handles errors, and is
tested.

Students write a ``manage.py`` command that a platform operator would use, for example a report of
each account's resource counts by kind, or a command that lists API keys unused for a number of
days. It follows the existing commands in ``smarter/smarter/apps/account/management/commands/``.

**What students turn in:**

- A pull request with the command, its tests and a docs entry.
- Example output from running it in the container.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Usefulness
     - 15
     - Solves a real operator need, with sensible arguments.
     - A toy command.
   * - Correctness and queries
     - 25
     - Correct results, efficient queries (no query per row).
     - Correct, but with a query for every row.
   * - Error handling
     - 15
     - Bad arguments and empty results handled with clear messages and exit codes.
     - Crashes on bad input.
   * - Tests
     - 25
     - Normal, edge and error cases; fixtures cleaned up.
     - Happy path only, or leaves data behind.
   * - Conventions and documentation
     - 20
     - Follows the existing commands; help text and docs.
     - Inconsistent, undocumented.

Recommended Texts
-----------------

- **Pre-reading:** the official `Django tutorial
  <https://docs.djangoproject.com/en/stable/intro/tutorial01/>`__, parts 1 to 4, for students who
  have never used Django.
- **Reference:** William S. Vincent, *Django for APIs* (latest edition, self-published), for Django
  REST Framework.
- **Reference:** Daniel Feldroy and Audrey Feldroy, *Two Scoops of Django 3.x* (Two Scoops Press,
  2020), for conventions and best practices that still apply.
- **Smarter documentation:** :doc:`/smarter-framework/smarter-broker-model`,
  :doc:`/smarter-framework/smarter-api`, :doc:`/smarter-framework/technologies/pydantic`,
  :doc:`/smarter-framework/guides/developer-feature-checklist` and
  :doc:`/smarter-framework/getting-started`.

Further Study
-------------

.. include:: further-study.txt
