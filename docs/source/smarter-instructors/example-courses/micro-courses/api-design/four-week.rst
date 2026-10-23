API Design and Integration: Four-Week Online Course
===================================================

A four-week online course on designing and consuming REST APIs, taught on Smarter's API from both
sides. Smarter's API has sixteen commands under `/api/v1/cli/
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/api/v1/cli/urls.py>`__ that
apply, describe and delete every resource from a YAML manifest, resource-style endpoints for the web
console, API keys of which only a hash is stored, one error format for every failure, and a typed
OpenAPI contract generated from the code. Its clients are real and public: the Go `smarter-cli
<https://github.com/smarter-sh/smarter-cli>`__, the React web console, the `@smarter.sh/ui-chat
<https://github.com/smarter-sh/smarter/tree/main/smarter/react/packages/smarter.sh-chat>`__ npm package, whose types are generated from the chat
API's Pydantic contract, and a `Python SDK <https://github.com/smarter-sh/smarter-python>`__ that
tests every request it sends against a pinned copy of the API's OpenAPI document. There are twelve 30-minute recorded lectures and a 90-minute live
session each week. Week 1 covers consuming an API, week 2 building clients, week 3 the server side,
and week 4 evolving, securing and operating an API. See :doc:`../course-formats` for the format, the
grading scale and the course policies, and :doc:`../api-design` for an overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Developers who build or integrate with web APIs.
   * - **Deployment**
     - A shared Smarter instance with an API key for each student in weeks 1 and 2. Students
       install Smarter from source for week 3.
   * - **Workload**
     - 3 hours of instruction and 4 to 6 hours of assignments each week.
   * - **Cost**
     - Free, apart from small model charges.

Learning Objectives
-------------------

By the end of the course, students can:

1. Apply REST principles, and explain where real APIs depart from them.
2. Call authenticated APIs, handle errors, and write robust client libraries.
3. Read and write OpenAPI descriptions, and generate clients and documentation from them.
4. Implement an endpoint in Django REST Framework with authentication, validation and consistent
   errors.
5. Evaluate an API against a style guide and the OWASP API Security Top 10.
6. Design API changes with versioning, deprecation and migration plans.

Technical Prerequisites
-----------------------

- **Required:** structured programming in at least one language, including HTTP requests and
  JSON parsing.
- **Required:** HTTP, JSON and YAML.
- **Required:** the command line, ``curl``, Git and a GitHub account.
- **Required by week 3:** basic Python, Docker basics, and Smarter installed from source (see the
  :doc:`Developer Setup Guide </smarter-framework/guides/developer-setup>`).
- **Helpful:** Postman, and basic Django.

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
     - Lecture 1
     - **What makes an API good.** REST principles, resources, methods, idempotence and status
       codes.
   * - 1
     - Lecture 2
     - **Smarter's API.** The :doc:`REST API </smarter-framework/smarter-api>`, its commands,
       OpenAPI contract, and the manifest-based design.
   * - 1
     - Lecture 3
     - **Authentication and errors.** API keys and sessions,
       :doc:`authentication </smarter-framework/smarter-api/authentication>`, the
       :doc:`error format </smarter-framework/smarter-api/error-handling>`, and RFC 9457.
   * - 1
     - Live session 1
     - Live ``curl`` session through a resource's lifecycle, and an error hunt in pairs. Start
       Assignment 1.
   * - 2
     - Lecture 4
     - **Client design.** Configuration, authentication, typed responses, and idiomatic
       interfaces.
   * - 2
     - Lecture 5
     - **Resilient clients.** Timeouts, retries, backoff, idempotency keys, and rate limits.
   * - 2
     - Lecture 6
     - **Chat and streaming APIs.** Smarter's :doc:`chat API </smarter-framework/smarter-api/chat>`,
       streaming, and OpenAI-compatible :doc:`Proxies </smarter-resources/smarter-proxy>`.
   * - 2
     - Live session 2
     - Review of Assignment 1. Code review of clients in small groups. Start Assignment 2.
   * - 3
     - Lecture 7
     - **Inside the server.** How Smarter's API is built with Django REST Framework: URLs, views,
       authentication classes and brokers, and the three styles side by side: command-style
       ``/api/v1/cli/``, resource-style ``/api/v1/guardrails/``, and the console's
       ``react-integration/api/``.
   * - 3
     - Lecture 8
     - **Contracts.** Pydantic request and response models, OpenAPI generation, and contract tests.
   * - 3
     - Lecture 9
     - **Describing an API.** Writing OpenAPI by hand, generating clients, and documentation that
       developers enjoy.
   * - 3
     - Live session 3
     - Review of Assignment 2. Live addition of an endpoint, with tests. Capstone proposals
       discussed. Start Assignment 3.
   * - 4
     - Lecture 10
     - **Evolving an API.** Versioning strategies, deprecation, breaking changes, and
       :doc:`ADR 023 </adr/023-api-versioning>`.
   * - 4
     - Lecture 11
     - **Securing an API.** The OWASP API Security Top 10: object-level authorization, excessive
       data exposure, mass assignment and rate limiting.
   * - 4
     - Lecture 12
     - **Operating an API.** Rate limiting: DRF's throttling classes
       (:doc:`/smarter-framework/smarter-api/rate-limiting`), which Smarter does not configure,
       against what it uses instead: Budgets that limit spending and tokens, and middleware that
       blocks probing clients. Is that enough?
       :doc:`Logging </smarter-framework/smarter-api/logging>`, monitoring and service level
       objectives.
   * - 4
     - Live session 4
     - Capstone presentations (about 6 minutes each, with 2 minutes of questions), and a course
       retrospective.

Assignments 1 to 3 are due before the next live session. Assignment 4 is due in the middle of week
4. The capstone proposal is due before Live session 3, and the capstone at the start of Live
session 4.

Smarter in the Source Code
--------------------------

.. include:: source-code.txt

Graded Assignments
------------------

Assignment 1: Lifecycle and Error Catalog
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students take a resource through its lifecycle with ``curl`` and the CLI, and catalog at least six
distinct errors, judging each against what a client needs.

**Turn in:** a Markdown file with commands, responses and an error table.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Lifecycle
     - 5
     - All steps with ``curl`` and the CLI; no key committed.
     - Steps missing.
   * - Error variety
     - 5
     - Six or more classes.
     - Variations of one.
   * - Assessment
     - 6
     - Judged against recovery needs.
     - None.
   * - Improvement
     - 4
     - Better responses proposed.
     - None.

Assignment 2: A Resilient Client
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students write a client that lists LLMClients, applies a manifest and chats, with timeouts,
retries with backoff for transient errors only, and typed responses, tested with mocked responses.

**Turn in:** a Git repository with the client, tests and a ``README.md``.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Works
     - 5
     - All three operations.
     - Some.
   * - Resilience
     - 6
     - Timeouts; retries only for transient, safe failures.
     - No timeouts, or retries everything.
   * - Tests
     - 5
     - Mocked, including failures.
     - Needs a live server.
   * - Interface and docs
     - 4
     - Idiomatic and documented.
     - Raw HTTP exposed.

Assignment 3: A New Endpoint
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students add a small read-only endpoint to their fork of Smarter, for example one that returns the
caller's API keys with their creation and last-used dates (never the key itself), with a Pydantic
response model, authentication, tests, and its operation in the OpenAPI contract.

**Turn in:** a pull request against their fork.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Security
     - 6
     - Authenticated, scoped to the caller, no secrets exposed, tested.
     - Exposes other users' data or secrets.
   * - Consistency
     - 5
     - Matches the existing API's conventions and errors.
     - Inconsistent.
   * - Tests
     - 5
     - Success, unauthenticated and other-user cases.
     - Happy path only.
   * - Documentation
     - 4
     - Documented correctly in the OpenAPI contract.
     - Missing.

Assignment 4: Security Review
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students review part of Smarter's API against the OWASP API Security Top 10, with evidence from
real requests, and report findings by severity. Any real weakness is reported privately to the
maintainers, as described in the project's security policy, not in the assignment.

**Turn in:** a two-page review.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Coverage
     - 5
     - Every relevant category examined.
     - A few categories.
   * - Evidence
     - 6
     - Real requests and responses.
     - Assertions.
   * - Analysis
     - 5
     - Explains which defenses exist, and where.
     - Lists categories without analysis.
   * - Responsible handling
     - 4
     - Real weaknesses reported privately.
     - Weakness details published.

Capstone Projects
-----------------

Students choose one, propose it before Live session 3, and present it in Live session 4.

Capstone A: A Published SDK
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Design, test, document and publish a client SDK as an open source package.

Students write an SDK for the Smarter API in a language that lacks one, with typed responses,
mapped errors, resilient transport, tests, documentation and continuous integration, and publish a
pre-release version to the language's package registry (for example a ``0.1.0`` on npm, PyPI,
crates.io or pkg.go.dev).

**What students turn in:**

- A public Git repository with the SDK, tests, CI and documentation.
- A link to the published package.
- A six-minute presentation with a live demonstration.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Interface
     - 20
     - Idiomatic and consistent.
     - Thin HTTP wrapper.
   * - Robustness
     - 20
     - Typed, mapped errors, safe retries, timeouts.
     - Fragile.
   * - Tests and CI
     - 20
     - Mocked tests run in CI on every push.
     - No CI, or live-server tests.
   * - Documentation
     - 20
     - Quick start and reference for every operation.
     - Sparse.
   * - Publishing and presentation
     - 20
     - Published with a license and changelog; clear demonstration.
     - Not published.

Capstone B: An API Improvement, from ADR to Release
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Take an API change from design to implementation, with compatibility proven
by tests and a deprecation plan.

Students choose a weakness found in their reviews, write an ADR with an OpenAPI fragment and
migration plan, implement the change on their fork of Smarter, add deprecation warnings for the old
behavior, and write tests that run old and new clients against it.

**What students turn in:**

- An ADR in the format of :doc:`/adr`.
- A pull request against their fork with the implementation, tests and documentation.
- A migration guide for client developers.
- A six-minute presentation.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - ADR
     - 20
     - Real problem, alternatives compared, consequences stated.
     - Thin.
   * - Implementation
     - 20
     - Correct and consistent with the API.
     - Inconsistent.
   * - Compatibility
     - 25
     - Tests prove old clients work; deprecation signaled.
     - Untested.
   * - Migration guide
     - 20
     - A client developer could follow it.
     - Vague.
   * - Presentation
     - 15
     - Clear and on time.
     - Overruns.

Recommended Texts
-----------------

- **Required:** Arnaud Lauret, *The Design of Web APIs* (Manning, 2019), in weeks 1 and 2.
- **Required:** JJ Geewax, *API Design Patterns* (Manning, 2021), selected chapters on standard
  methods, pagination and versioning, in weeks 3 and 4.
- **Required:** the `OWASP API Security Top 10 <https://owasp.org/API-Security/>`__, in week 4.
- **Reference:** William S. Vincent, *Django for APIs* (latest edition, self-published), for week
  3.
- **Smarter documentation:** :doc:`/smarter-framework/smarter-api`, its pages on
  :doc:`authentication </smarter-framework/smarter-api/authentication>`,
  :doc:`errors </smarter-framework/smarter-api/error-handling>`,
  :doc:`rate limiting </smarter-framework/smarter-api/rate-limiting>` and
  :doc:`chat </smarter-framework/smarter-api/chat>`, and :doc:`ADR 006 </adr/006-rest-api>` and
  :doc:`ADR 023 </adr/023-api-versioning>`.

Further Study
-------------

.. include:: further-study.txt
