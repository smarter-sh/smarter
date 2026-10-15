API Design and Integration: Two-Week Online Course
==================================================

A two-week online course on designing and consuming REST APIs, taught on Smarter's API from both
sides. Smarter's API has sixteen commands under `/api/v1/cli/
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/api/v1/cli/urls.py>`__ that
apply, describe and delete every resource from a YAML manifest, resource-style endpoints for the web
console, API keys of which only a hash is stored, one error format for every failure, and Swagger
and ReDoc pages generated from the code. Its clients are real and public: the Go `smarter-cli
<https://github.com/smarter-sh/smarter-cli>`__, the React web console, the `@smarter.sh/ui-chat
<https://github.com/smarter-sh/smarter-chat>`__ npm package, whose types are generated from the chat
API's Pydantic contract, and a `Python SDK <https://github.com/smarter-sh/smarter-python>`__ that
tests every request it sends against a pinned copy of the API's OpenAPI document. There are six 30-minute recorded lectures and a 90-minute live
session each week. Week 1 covers consuming an API, and week 2 covers designing, evolving and
operating one. See :doc:`../course-formats` for the format, the grading scale and the course
policies, and :doc:`../api-design` for an overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Developers in any language who build or integrate with web APIs.
   * - **Deployment**
     - A shared Smarter instance with an API key for each student, or students' own installations.
       Students who choose the server-side capstone need Smarter installed from source.
   * - **Workload**
     - 3 hours of instruction and 4 to 6 hours of assignments each week.
   * - **Cost**
     - Free, apart from small model charges.

Learning Objectives
-------------------

By the end of the course, students can:

1. Apply REST principles, and explain where real APIs depart from them and why.
2. Call authenticated APIs, handle their errors, and write a client library.
3. Read and write OpenAPI descriptions.
4. Evaluate an API against a style guide.
5. Design API changes with versioning and migration plans.

Technical Prerequisites
-----------------------

- **Required:** structured programming in at least one language, including HTTP requests and
  JSON parsing.
- **Required:** HTTP, JSON and YAML.
- **Required:** the command line, ``curl``, Git and a GitHub account.
- **Helpful:** Postman or a similar API client; Python and Django for the server-side capstone.

Schedule
--------

The files that the lectures refer to are listed in full under `Smarter in the Source Code`_.

.. list-table::
   :header-rows: 1
   :widths: 10 18 72

   * - Week
     - Item
     - Content
   * - 1
     - Lecture 1 (30 min)
     - **What makes an API good.** REST principles, resources, methods, idempotence, status codes
       and consistency. A first look at Smarter's :doc:`REST API </smarter-framework/smarter-api>`.
   * - 1
     - Lecture 2 (30 min)
     - **Authentication and errors.** API keys, tokens and sessions, Smarter's
       :doc:`error format </smarter-framework/smarter-api/error-handling>`, and RFC 9457.
   * - 1
     - Lecture 3 (30 min)
     - **Writing a client.** Configuration, retries, timeouts, pagination and typed responses, and
       how the Go `smarter-cli <https://github.com/smarter-sh/smarter-cli>`__ calls the API.
   * - 1
     - Live session 1 (90 min)
     - Live ``curl`` session through a resource's lifecycle, then an error hunt in pairs. Start
       Assignment 1.
   * - 2
     - Lecture 4 (30 min)
     - **Describing an API.** OpenAPI and Swagger, schemas, and generating clients and
       documentation.
   * - 2
     - Lecture 5 (30 min)
     - **Evolving an API.** Versioning strategies, deprecation, breaking changes, and
       :doc:`ADR 023 </adr/023-api-versioning>`.
   * - 2
     - Lecture 6 (30 min)
     - **Operating an API.** Rate limiting, and why Smarter relies on Budgets and middleware
       instead of DRF throttling, logging, chat and streaming APIs, OpenAI-compatible
       :doc:`Proxies </smarter-resources/smarter-proxy>`, and the OWASP API Security Top 10.
   * - 2
     - Live session 2 (90 min)
     - Capstone presentations (about 5 minutes each, with 2 minutes of questions).

Assignment 1 is due at the end of week 1, Assignment 2 in the middle of week 2, and Assignment 3
and the capstone at the start of Live session 2.

Smarter in the Source Code
--------------------------

.. include:: source-code.txt

Graded Assignments
------------------

Assignment 1: Lifecycle and Error Catalog
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students take a resource through apply, get, describe and delete with ``curl``, then trigger and
catalog at least five distinct errors, judging whether each tells a client how to recover.

**Turn in:** a Markdown file with commands, responses and an error table.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Lifecycle
     - 6
     - All four steps, correct requests, no key committed.
     - Steps missing, or a real key in the file.
   * - Error variety
     - 4
     - Five or more distinct classes.
     - Variations of one.
   * - Error assessment
     - 6
     - Judged against what a client needs to recover.
     - No assessment.
   * - Improvement
     - 4
     - A better response proposed for the weakest error.
     - None.

Assignment 2: A Small Client
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students write a client in the language of their choice that lists their LLMClients and chats with
one, with error handling and the key read from the environment.

**Turn in:** a Git repository with the client and a ``README.md``.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Works
     - 6
     - Both operations work.
     - One works.
   * - Error handling
     - 5
     - Bad keys, timeouts and server errors handled.
     - Crashes.
   * - Secrets
     - 4
     - Key from the environment.
     - Key in the code.
   * - Documentation
     - 5
     - Runnable from the ``README.md``.
     - Missing steps.

Assignment 3: Style Guide Review
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students review part of Smarter's API against Google's, Microsoft's or Zalando's guidelines, and
report where it complies, where it does not, and which departures are justified.

**Turn in:** a two-page review with a table of rules, findings and evidence.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Coverage
     - 5
     - At least ten relevant rules checked.
     - A handful.
   * - Evidence
     - 6
     - Each finding backed by a real request and response.
     - Assertions without evidence.
   * - Judgment
     - 6
     - Distinguishes justified departures from mistakes.
     - Treats every departure as a mistake.
   * - Writing
     - 3
     - Clear and organized.
     - Disorganized.

Capstone Projects
-----------------

Students choose one, and present it in Live session 2.

Capstone A: A Client Library
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Design a client library that makes an API easy and safe to use.

Students write a client library for part of the Smarter API (authentication, ``apply``, ``get``,
``describe``, ``delete`` and chat) with typed responses, mapped exceptions, retries for transient
failures, and tests with mocked or recorded responses.

**What students turn in:**

- A Git repository with the library, tests, an example program and a ``README.md``.
- A one-page design note.
- A five-minute presentation.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Interface design
     - 25
     - Idiomatic, consistent, hard to misuse.
     - Thin wrapper over HTTP.
   * - Errors and retries
     - 20
     - Mapped exceptions; safe retries only.
     - Generic exceptions.
   * - Typed responses
     - 15
     - Parsed into types.
     - Raw dictionaries.
   * - Tests
     - 20
     - Mocked, including errors.
     - Needs a live server.
   * - Documentation and presentation
     - 20
     - Examples for every operation; clear presentation.
     - Sparse.

Capstone B: An API Change, Designed and Built
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Design a backward-compatible improvement to a real API, document it, and
build it.

Students take one finding from their style guide review and propose a fix as an Architecture
Decision Record with an OpenAPI fragment and a migration plan. Students with Python experience
implement it on a fork of Smarter, with tests; others build a mock server that demonstrates both
the old and the new behavior.

**What students turn in:**

- An ADR in the format of :doc:`/adr`, the OpenAPI fragment, and the migration plan.
- The implementation (a pull request against their fork, or a mock server), with tests showing
  that old clients still work.
- A five-minute presentation.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Problem and design
     - 25
     - Real weakness; consistent design.
     - Taste only; inconsistent.
   * - Alternatives
     - 15
     - Two or more, fairly compared.
     - None.
   * - Compatibility
     - 25
     - Tests prove old clients still work.
     - Breaks clients, or untested.
   * - Implementation
     - 20
     - Works and is tested.
     - Partial.
   * - Presentation
     - 15
     - Clear and on time.
     - Overruns.

Recommended Texts
-----------------

- **Required:** Arnaud Lauret, *The Design of Web APIs* (Manning, 2019). Week 1: parts 1 and 2.
  Week 2: part 3.
- **Required:** Google's `API Design Guide <https://cloud.google.com/apis/design>`__, in week 1.
- **Reference:** JJ Geewax, *API Design Patterns* (Manning, 2021).
- **Smarter documentation:** :doc:`/smarter-framework/smarter-api`,
  :doc:`/smarter-framework/smarter-api/authentication`,
  :doc:`/smarter-framework/smarter-api/error-handling`,
  :doc:`/smarter-framework/smarter-api/rate-limiting` and :doc:`/adr/023-api-versioning`.

Further Study
-------------

.. include:: further-study.txt
