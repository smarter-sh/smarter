API Design and Integration: Classroom Bootcamp
==============================================

An eight-hour classroom bootcamp on designing and consuming REST APIs, taught on Smarter's versioned
and documented API, from both sides: the server that provides it and the clients built on it.
Smarter's API has sixteen commands under `/api/v1/cli/
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/api/v1/cli/urls.py>`__ that
apply, describe and delete every resource from a YAML manifest, resource-style endpoints for the web
console, API keys of which only a hash is stored, one error format for every failure, and Swagger
and ReDoc pages generated from the code. Its clients are real and public: the Go `smarter-cli
<https://github.com/smarter-sh/smarter-cli>`__, the React web console, the `@smarter.sh/ui-chat
<https://github.com/smarter-sh/smarter/tree/main/smarter/react/packages/smarter.sh-chat>`__ npm package, whose types are generated from the chat
API's Pydantic contract, and a `Python SDK <https://github.com/smarter-sh/smarter-python>`__ that
tests every request it sends against a pinned copy of the API's OpenAPI document. Students call the API by hand, write a client, review the API
against a style guide, and design an improvement that does not break existing clients. See
:doc:`../course-formats` for the standard bootcamp day, the grading scale and the course policies,
and :doc:`../api-design` for an overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Developers in any language who build or integrate with web APIs.
   * - **Deployment**
     - A shared Smarter instance run by the instructor, with an API key for each student, or
       students' own installations from the Quick Start.
   * - **Cost**
     - Free, apart from small model charges for chat requests.

Learning Objectives
-------------------

By the end of the bootcamp, students can:

1. Explain the principles of REST: resources, methods, status codes, representations and
   statelessness.
2. Call an authenticated API with ``curl`` and a client library, and handle its errors.
3. Read and use OpenAPI (Swagger) documentation.
4. Evaluate an API against a published style guide.
5. Design a change to an API, with a versioning and migration plan that does not break clients.

Technical Prerequisites
-----------------------

- **Required:** structured programming in at least one language (Python, JavaScript, Go, Java or
  similar), including making HTTP requests and parsing JSON.
- **Required:** HTTP: methods, status codes, headers and bodies.
- **Required:** JSON and YAML.
- **Required:** the command line and ``curl``.
- **Required:** Git and a GitHub account.
- **Helpful:** Postman or a similar API client, and the
  `smarter CLI <https://smarter.sh/cli>`__.

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
     - **Lecture 1: What makes an API good.** REST principles, resources and representations,
       methods and idempotence, status codes, and consistency. A first look at Smarter's
       :doc:`REST API </smarter-framework/smarter-api>` and its Swagger documentation.
   * - 2
     - 45
     - **Lab 1: Call it by hand.** With ``curl`` and an API key, apply, get, describe and delete a
       resource through ``/api/v1/cli/``, then do the same with the ``smarter`` CLI, and compare.
       Produces Assignment 1.
   * - 3
     - 45
     - **Lecture 2: Authentication and errors.** API keys, tokens and sessions; Smarter's
       :doc:`authentication </smarter-framework/smarter-api/authentication>` and its
       :doc:`error format </smarter-framework/smarter-api/error-handling>`. Problem details
       (RFC 9457), and what a client needs from an error.
   * - 4
     - 45
     - **Lab 2: Make it fail.** Trigger at least five different errors (bad key, missing resource,
       invalid manifest, wrong method, a budget limit) and record each status code and body.
       Produces Assignment 2.
   * - 5
     - 45
     - **Lecture 3: Writing a client.** Wrapping an API in a small library: configuration,
       authentication, retries, timeouts, pagination and typed responses. A tour of how the Go
       `smarter-cli <https://github.com/smarter-sh/smarter-cli>`__ calls the API
       (`cmd/api.go <https://github.com/smarter-sh/smarter-cli/blob/main/cmd/api.go>`__), and of
       the Python SDK, which learns what changed in the API when it refreshes its pinned copy of
       the OpenAPI document and its contract tests fail.
   * - 6
     - 45
     - **Lecture 4: Chat APIs and streaming.** Smarter's
       :doc:`chat API </smarter-framework/smarter-api/chat>`, conversation state, and streaming
       responses. The OpenAI-compatible :doc:`Proxy </smarter-resources/smarter-proxy>`, and why
       compatibility with a popular API is a design strategy.
   * - 7
     - 45
     - **Lab 3: Write a client.** In a language of their choice, students write a small client
       that lists their LLMClients and sends a chat message to one. Produces Assignment 3.
   * - 8
     - 45
     - **Lecture 5: Evolving an API.** Versioning strategies (path, header, media type),
       deprecation, breaking and non-breaking changes, and Smarter's
       :doc:`ADR 023 on API versioning </adr/023-api-versioning>`.
   * - 9
     - 45
     - **Lab 4: Style guide review.** In groups, review part of Smarter's API against Google's or
       Zalando's guidelines, and list where it follows them and where it does not. Ungraded.
   * - 10
     - 45
     - **Lecture 6: Operating an API.** Rate limiting: DRF's throttling classes
       (:doc:`/smarter-framework/smarter-api/rate-limiting`), which Smarter does not configure,
       against what it uses instead: Budgets that limit spending and tokens, and middleware that
       blocks probing clients. Is that enough?
       :doc:`Logging </smarter-framework/smarter-api/logging>`, the journal of every request,
       monitoring, documentation, and the OWASP API Security Top 10.
   * - 11
     - 30
     - **Capstone kickoff.** Students choose a capstone and outline their design or client.

Smarter in the Source Code
--------------------------

.. include:: source-code.txt

Graded Assignments
------------------

Assignment 1: Resource Lifecycle by Hand
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students take one resource through its whole lifecycle with ``curl``, then with the CLI, and
compare the two.

**Turn in:** a Markdown file with every command and response, and a half-page comparison.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Complete lifecycle
     - 6
     - Apply, get, describe and delete, all successful.
     - Some steps missing or failing.
   * - Correct requests
     - 5
     - Correct methods, headers and bodies; no API key committed.
     - Errors in requests, or a real key in the file.
   * - Responses explained
     - 5
     - Status codes and bodies interpreted.
     - Pasted without comment.
   * - Comparison
     - 4
     - Explains what the CLI does for the user.
     - Superficial.

Assignment 2: Error Catalog
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students trigger at least five different errors and catalog them, then judge whether each error
gives a client what it needs to recover.

**Turn in:** a table of request, status code, body and assessment.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Variety
     - 5
     - Five or more distinct error classes.
     - Variations of one error.
   * - Accuracy
     - 5
     - Real requests and responses.
     - Paraphrased.
   * - Assessment
     - 6
     - Judges each error against what a client needs (code, message, field, retry).
     - No assessment.
   * - Improvement
     - 4
     - Proposes a better response for the weakest error.
     - None.

Assignment 3: A Small Client
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students write a client in the language of their choice that lists their LLMClients and chats with
one, reading the API key from an environment variable.

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
     - Lists LLMClients and completes a chat.
     - One of the two works.
   * - Error handling
     - 5
     - Handles bad keys, timeouts and server errors with clear messages.
     - Crashes on errors.
   * - Secrets
     - 4
     - Key from the environment, never in the repository.
     - Key in the code.
   * - Documentation
     - 5
     - Someone else could run it.
     - Missing setup steps.

Capstone Projects
-----------------

Students choose one. Capstones are due one week after the bootcamp.

Capstone A: A Client Library
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Design a client library that makes an API easy and safe to use, with
typed responses, errors and tests.

Students write a small client library for part of the Smarter API in a language of their choice,
covering authentication, ``apply``, ``get``, ``describe``, ``delete`` and chat, with typed
response objects, exceptions that map to the API's errors, retries for transient failures, and
tests that use recorded or mocked responses.

**What students turn in:**

- A Git repository with the library, tests and a ``README.md`` with examples.
- A short example program that uses it.
- A one-page design note on the library's interface.

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
     - Idiomatic for the language, consistent, hard to misuse.
     - A thin wrapper around raw HTTP calls.
   * - Errors and retries
     - 20
     - Errors mapped to exceptions; retries only for safe, transient failures.
     - Generic exceptions; retries for everything.
   * - Typed responses
     - 15
     - Responses parsed into typed objects.
     - Raw dictionaries.
   * - Tests
     - 20
     - Mocked or recorded responses, including errors.
     - Tests that need a live server, or none.
   * - Documentation
     - 20
     - Examples for every operation.
     - Sparse.

Capstone B: An API Change Proposal
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Design an improvement to a real API, and plan its release so that no
existing client breaks.

Students identify one weakness in Smarter's API (from their style guide review, for example
inconsistent naming, missing pagination or an unhelpful error) and write a design proposal as an
Architecture Decision Record, with the new OpenAPI description and a migration plan.

**What students turn in:**

- An ADR in the format of :doc:`/adr`, with context, decision, alternatives and consequences.
- The OpenAPI fragment for the new or changed endpoint.
- A migration plan: how old and new clients coexist, how deprecation is announced, and when the old
  behavior is removed.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Problem
     - 20
     - A real weakness, with evidence and the style guide rule it breaks.
     - A matter of taste.
   * - Design
     - 25
     - Consistent with the rest of the API and with the style guide.
     - Fixes one thing, breaks consistency elsewhere.
   * - Alternatives
     - 15
     - At least two alternatives, fairly compared.
     - None.
   * - Compatibility and migration
     - 25
     - No existing client breaks; clear deprecation timeline.
     - Breaks clients, or no plan.
   * - Writing
     - 15
     - Clear and concise, in ADR form.
     - Long or disorganized.

Recommended Texts
-----------------

- **Pre-reading:** Google's `API Design Guide <https://cloud.google.com/apis/design>`__, the
  sections on resource-oriented design and standard methods.
- **Reference:** Arnaud Lauret, *The Design of Web APIs* (Manning, 2019).
- **Smarter documentation:** :doc:`/smarter-framework/smarter-api`,
  :doc:`/smarter-framework/smarter-api/authentication`,
  :doc:`/smarter-framework/smarter-api/error-handling` and :doc:`/adr/023-api-versioning`.

Further Study
-------------

.. include:: further-study.txt
