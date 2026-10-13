Full Stack Development: Classroom Bootcamp
==========================================

An eight-hour classroom bootcamp on full stack development with Django and React, taught on
Smarter's web console, where Django hosts each React app and React calls back into Django's REST
API. Every list page in the console is built the same way: a `Django view
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/guardrail/views/listview/view.py>`__
and `template
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/templates/react/guardrail-list.html>`__
render a root element with the session's details as data attributes, a template tag reads Vite's
build manifest, and the React app calls back into `session-authenticated views
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/guardrail/views/listview/api.py>`__
to list, clone, rename and delete. The chat goes further, with a `Pydantic contract
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/prompt/contract/models.py>`__
that is exported as a JSON Schema and turned into TypeScript types, so both sides of the stack share
one definition. Students follow a feature from database column to pixel, and add one of their own.
See :doc:`../course-formats` for the standard bootcamp day, the grading scale and the course
policies, and :doc:`../full-stack-development` for an overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Developers who know some Python and some JavaScript, and want to connect a back end to a
       front end in a real application.
   * - **Deployment**
     - Each student runs Smarter from source, installed and working **before** the bootcamp, with
       ``make react-install`` done.
   * - **Cost**
     - Free, apart from small model charges.

Learning Objectives
-------------------

By the end of the bootcamp, students can:

1. Explain how Django serves a React app: view, template, root element, build manifest and static
   files.
2. Trace a feature from a Django model, through a REST endpoint, to a React component.
3. Explain session authentication and CSRF between a React front end and a Django back end.
4. Add a field that travels from the database to the screen, with tests on both sides.
5. Explain how a typed contract, published as a JSON Schema from Pydantic models, keeps a front
   end and a back end in agreement.

Technical Prerequisites
-----------------------

- **Required:** Python (classes, decorators, type hints) and JavaScript (modules, promises,
  ``async``/``await``).
- **Required:** basic Django (models, views, URLs) or completion of the
  :doc:`backend course <../backend-development>`, and basic React (components, props, state) or
  the :doc:`front end course <../frontend-development>`.
- **Required:** Git, the command line, Docker basics, HTTP and JSON.
- **Required:** Smarter installed from source and running before the bootcamp (see the
  :doc:`Developer Setup Guide </smarter-framework/guides/developer-setup>`), with a screenshot of
  ``docker ps`` sent beforehand.
- **Helpful:** TypeScript, and the browser's network panel.

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
     - **Lecture 1: Architectures for full stack apps.** Server-rendered pages, single-page apps,
       and the hybrid that Smarter uses: Django pages that each host a small React app. Trade-offs
       of each.
   * - 2
     - 45
     - **Lab 1: Follow a page.** Follow one list page from its Django URL, view and template,
       through the Vite build manifest, to the React component and the API it calls, using the
       browser's network panel. Produces Assignment 1.
   * - 3
     - 45
     - **Lecture 2: Hosting React in Django.** The view, template and template tag that render the
       root element and its data attributes, the Vite manifest, ``collectstatic``, and what goes
       wrong when the manifest is missing: an empty page, no console error, and a template tag
       that has cached the absence.
       :doc:`/smarter-framework/developer-reference/react-integration`.
   * - 4
     - 45
     - **Lab 2: Break it and fix it.** The instructor gives each pair a broken page (a missing
       manifest, a wrong data attribute, a stale build). Diagnose and fix it. Produces
       Assignment 2.
   * - 5
     - 45
     - **Lecture 3: Talking to the API.** Session authentication, CSRF tokens, ``fetchDjangoUrl``
       and ``SessionContext`` in ``smarter-common``, and the list, clone, rename and delete API
       contract that every list page uses.
   * - 6
     - 45
     - **Lecture 4: Typed contracts.** How the chat API contract is defined as Pydantic models,
       published as a JSON Schema, and turned into TypeScript types
       (:doc:`/smarter-framework/smarter-chat/api-contract`). What this prevents.
   * - 7
     - 45
     - **Lab 3: Database to pixel.** Add a field that already exists on a model to a list page:
       serializer, API response, TypeScript type, column, story and test. Produces Assignment 3.
   * - 8
     - 45
     - **Lecture 5: Testing both sides.** Django tests for the API, Vitest and MSW for the
       component, and keeping mocks honest.
   * - 9
     - 45
     - **Lab 4: Rebuild and verify.** Run ``make react-build``, restart the app, and verify the new
       column in the real console. Ungraded.
   * - 10
     - 45
     - **Lecture 6: Shipping it.** Builds in CI, static files in production, caching, and how a
       front end change reaches users.
   * - 11
     - 30
     - **Capstone kickoff.** Students choose a capstone, branch, and list every file they expect to
       change.

Smarter in the Source Code
--------------------------

.. include:: source-code.txt

Graded Assignments
------------------

Assignment 1: Page Trace
~~~~~~~~~~~~~~~~~~~~~~~~

Students document how one list page reaches the screen, from URL to React component, and every API
request it makes.

**Turn in:** a diagram and a Markdown explanation in their fork, with network panel screenshots.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Server side
     - 6
     - URL, view, template, template tag and static files, with file names.
     - Steps missing.
   * - Client side
     - 6
     - Entry point, components and API calls.
     - Components only.
   * - Evidence
     - 4
     - Network panel confirms each request.
     - Inferred.
   * - Clarity
     - 4
     - A newcomer could follow it.
     - Hard to follow.

Assignment 2: Diagnosis Report
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pairs diagnose and fix the broken page they are given, and write up the symptom, the cause, how
they found it, and how to prevent it.

**Turn in:** a one-page report and the fix.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Fixed
     - 6
     - The page works.
     - Partly working.
   * - Root cause
     - 6
     - Correct and specific.
     - Symptom fixed, cause unclear.
   * - Method
     - 4
     - Describes the evidence that led to the cause.
     - "We tried things until it worked".
   * - Prevention
     - 4
     - A realistic check that would catch it.
     - None.

Assignment 3: Database to Pixel
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students expose an existing model field on a list page, end to end, with a Django test and a
Vitest test.

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
     - Serializer, API, type, component and story all updated.
     - A layer missing.
   * - Tests
     - 6
     - Both sides tested; mocks match the real response.
     - One side only.
   * - Verified
     - 3
     - Shown working in the real console after a rebuild.
     - Storybook only.
   * - Quality
     - 4
     - Pre-commit, ESLint and Prettier pass.
     - Hooks fail.

Capstone Projects
-----------------

Students choose one. Capstones are due one week after the bootcamp, as a pull request against
their fork.

Capstone A: A Full Stack Feature on a List Page
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Deliver a feature that needs coordinated back end and front end changes,
tested on both sides.

Students add a server-side feature with a front end to a list page, for example filtering by tag
(a query parameter on the API, a filter control on the page), or a "duplicate with new name"
action with validation errors shown in the dialog.

**What students turn in:**

- A pull request with Django and React changes, Django tests, Vitest tests and stories.
- A screen recording in the real console.
- A half-page design note on the API change.

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
     - Correct, efficient, scoped to the user's account, consistent errors.
     - Works, but unscoped or inconsistent.
   * - Front end
     - 20
     - All states handled; accessible controls.
     - Happy path only.
   * - Contract
     - 15
     - Front and back agree; types and mocks match the real API.
     - Mocks drift from the API.
   * - Tests
     - 25
     - Both sides, including errors.
     - One side only.
   * - Pull request
     - 15
     - Clear description, recording and design note.
     - No description.

Capstone B: A Typed Contract for a List Page
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Apply the typed-contract pattern from the chat API to another part of the
application, and show the class of bugs it prevents.

Students define one list page's API response as a Pydantic model, publish its JSON Schema, generate
TypeScript types from it, use them in the React app, and add a test that fails when the committed
schema is out of date.

**What students turn in:**

- A pull request with the Pydantic model, schema, generated types, React changes and tests.
- A demonstration that renaming a field on the server breaks the build or a test.
- A one-page note comparing this with hand-written types.

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
     - Matches the real response exactly, no ``Any``.
     - Loose types.
   * - Schema and types
     - 20
     - Generated, not hand-edited, and used by the component.
     - Generated but unused.
   * - Freshness test
     - 20
     - Fails when the schema is stale.
     - No test.
   * - Demonstration
     - 20
     - A server change is caught before it reaches users.
     - Not demonstrated.
   * - Note
     - 20
     - Weighs the benefits against the extra build step.
     - One-sided.

Recommended Texts
-----------------

- **Pre-reading:** :doc:`/smarter-framework/developer-reference/react-integration`, and the Vite
  `backend integration guide <https://vite.dev/guide/backend-integration>`__.
- **Reference:** William S. Vincent, *Django for APIs* (latest edition, self-published), and Alex
  Banks and Eve Porcello, *Learning React* (2nd edition, O'Reilly, 2020).
- **Smarter documentation:** :doc:`/smarter-framework/smarter-chat/web-console-hosting` and
  :doc:`/smarter-framework/smarter-chat/api-contract`.

Further Study
-------------

.. include:: further-study.txt
