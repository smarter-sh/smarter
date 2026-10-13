Full Stack Development: Two-Week Online Course
==============================================

A two-week online course on full stack development with Django and React, taught on Smarter's web
console, where Django hosts each React app and React calls back into Django. Every list page in the
console is built the same way: a `Django view
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/guardrail/views/listview/view.py>`__
and `template
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/templates/react/guardrail-list.html>`__
render a root element with the session's details as data attributes, a template tag reads Vite's
build manifest, and the React app calls back into `session-authenticated views
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/guardrail/views/listview/api.py>`__
to list, clone, rename and delete. The chat goes further, with a `Pydantic contract
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/prompt/contract/models.py>`__
that is exported as a JSON Schema and turned into TypeScript types, so both sides of the stack share
one definition. There are six 30-minute recorded lectures and a 90-minute live session each week.
Week 1 covers how Django hosts React, and week 2 covers the API, contracts and testing. See
:doc:`../course-formats` for the format, the grading scale and the course policies, and
:doc:`../full-stack-development` for an overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Developers who know some Python and some JavaScript.
   * - **Deployment**
     - Each student runs Smarter from source, installed before Live session 1, with
       ``make react-install`` done.
   * - **Workload**
     - 3 hours of instruction and 4 to 6 hours of assignments each week.
   * - **Cost**
     - Free, apart from small model charges.

Learning Objectives
-------------------

By the end of the course, students can:

1. Compare full stack architectures, and explain the one that Smarter uses.
2. Explain and debug how Django serves a React app.
3. Connect React to a Django REST API with session authentication and CSRF.
4. Deliver a feature from database to screen, tested on both sides.
5. Use a typed contract to keep a front end and a back end in agreement.

Technical Prerequisites
-----------------------

- **Required:** Python (classes, decorators, type hints) and JavaScript (modules, promises,
  ``async``/``await``).
- **Required:** basic Django and basic React, or the :doc:`backend <../backend-development>` and
  :doc:`front end <../frontend-development>` courses.
- **Required:** Git and GitHub, the command line, Docker basics, HTTP and JSON.
- **Required before Live session 1:** Smarter installed from source (see the
  :doc:`Developer Setup Guide </smarter-framework/guides/developer-setup>`).
- **Helpful:** TypeScript, and the browser's network panel.

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
     - **Architectures.** Server-rendered pages, single-page apps, and Django pages that host
       small React apps.
   * - 1
     - Lecture 2 (30 min)
     - **Hosting React in Django.** View, template, template tag, root element and data
       attributes (:doc:`/smarter-framework/developer-reference/react-integration`).
   * - 1
     - Lecture 3 (30 min)
     - **Builds and static files.** The Vite manifest, ``collectstatic``, ``make react-build``, and
       the classic failure modes.
   * - 1
     - Live session 1 (90 min)
     - Live trace of a list page from URL to component. Pairs diagnose a deliberately broken page.
       Start Assignment 1.
   * - 2
     - Lecture 4 (30 min)
     - **Talking to the API.** Sessions, CSRF, ``fetchDjangoUrl``, ``SessionContext``, and the list
       page API contract.
   * - 2
     - Lecture 5 (30 min)
     - **Typed contracts.** Pydantic models, JSON Schema and generated TypeScript types
       (:doc:`/smarter-framework/smarter-chat/api-contract`).
   * - 2
     - Lecture 6 (30 min)
     - **Testing both sides.** Django API tests, Vitest and MSW, and keeping mocks honest.
   * - 2
     - Live session 2 (90 min)
     - Capstone demonstrations (about 5 minutes each, with 2 minutes of review questions).

Assignment 1 is due at the end of week 1, Assignment 2 in the middle of week 2, and Assignment 3
and the capstone at the start of Live session 2.

Smarter in the Source Code
--------------------------

.. include:: source-code.txt

Graded Assignments
------------------

Assignment 1: Page Trace and Diagnosis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students document how a list page reaches the screen, and write up the broken page they fixed in
Live session 1.

**Turn in:** a diagram and explanation, and a half-page diagnosis report, in their fork.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Trace
     - 8
     - Server and client sides complete, with file names and network evidence.
     - Steps missing.
   * - Diagnosis
     - 6
     - Correct root cause, with the evidence that led to it.
     - Symptom only.
   * - Prevention
     - 3
     - A realistic check that would catch it.
     - None.
   * - Clarity
     - 3
     - Easy to follow.
     - Hard to follow.

Assignment 2: Database to Pixel
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students expose an existing model field on a list page, end to end, with tests on both sides.

**Turn in:** a pull request against their fork.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - End to end
     - 7
     - Every layer updated.
     - A layer missing.
   * - Tests
     - 6
     - Both sides; mocks match the real response.
     - One side only.
   * - Verified
     - 3
     - Working in the real console.
     - Storybook only.
   * - Quality
     - 4
     - All hooks pass.
     - Hooks fail.

Assignment 3: An API Change with Its Front End
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students add an optional query parameter to a list endpoint (for example, filter by tag or by
date), and a control on the page that uses it.

**Turn in:** a pull request against their fork.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - API change
     - 6
     - Backward compatible, validated, scoped to the account.
     - Breaks existing calls, or unvalidated.
   * - Front end
     - 5
     - Accessible control; loading and empty states.
     - Happy path only.
   * - Tests
     - 6
     - Both sides, including invalid input.
     - Partial.
   * - Pull request
     - 3
     - Clear description.
     - None.

Capstone Projects
-----------------

Students choose one, and demonstrate it in Live session 2.

Capstone A: A Full Stack Feature
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Deliver a feature that needs coordinated back end and front end changes,
with tests on both sides.

Students add a feature such as a "duplicate with new name" action with server-side validation and
errors shown in a dialog, or a details drawer that loads a resource's manifest when a row is
clicked.

**What students turn in:**

- A pull request with Django and React changes, tests and stories.
- A screen recording, and a five-minute demonstration.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Back end
     - 25
     - Correct, scoped, consistent errors.
     - Unscoped or inconsistent.
   * - Front end
     - 20
     - All states; accessible.
     - Happy path only.
   * - Contract
     - 15
     - Types and mocks match the API.
     - Drift.
   * - Tests
     - 25
     - Both sides, including errors.
     - One side.
   * - Demonstration
     - 15
     - Clear and on time.
     - Overruns.

Capstone B: A Typed Contract for a List Page
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Apply the typed-contract pattern to another part of the application, and
demonstrate the bugs it prevents.

Students define one list page's API response as a Pydantic model, publish its JSON Schema, generate
TypeScript types, use them in the React app, and add a schema freshness test.

**What students turn in:**

- A pull request with the model, schema, generated types, React changes and tests.
- A demonstration that a server-side rename is caught.
- A five-minute demonstration in Live session 2.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Pydantic model
     - 20
     - Exact, no ``Any``.
     - Loose.
   * - Schema and types
     - 20
     - Generated and used.
     - Unused.
   * - Freshness test
     - 20
     - Fails when stale.
     - Missing.
   * - Demonstration of value
     - 25
     - A breaking change caught before users see it.
     - Not shown.
   * - Presentation
     - 15
     - Clear trade-offs, on time.
     - One-sided.

Recommended Texts
-----------------

- **Required:** :doc:`/smarter-framework/developer-reference/react-integration` and
  :doc:`/smarter-framework/smarter-chat/api-contract`, in weeks 1 and 2.
- **Required:** William S. Vincent, *Django for APIs* (latest edition, self-published), the
  chapters on permissions, authentication and CORS, in week 2.
- **Reference:** Alex Banks and Eve Porcello, *Learning React* (2nd edition, O'Reilly, 2020).
- **Smarter documentation:** :doc:`/smarter-framework/smarter-chat/web-console-hosting`.

Further Study
-------------

.. include:: further-study.txt
