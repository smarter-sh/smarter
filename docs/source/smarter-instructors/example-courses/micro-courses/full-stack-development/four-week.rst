Full Stack Development: Four-Week Online Course
===============================================

A four-week online course on full stack development with Django and React, taught on Smarter's web
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
one definition. There are twelve 30-minute recorded lectures and a 90-minute live session each week.
Week 1 covers architecture and hosting, week 2 the API and authentication, week 3 contracts and
testing, and week 4 shipping. The course ends with a new console page, delivered end to end. See
:doc:`../course-formats` for the format, the grading scale and the course policies, and
:doc:`../full-stack-development` for an overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Developers who know some Python and some JavaScript.
   * - **Deployment**
     - Each student runs Smarter from source. Week 1 includes time for installation.
   * - **Workload**
     - 3 hours of instruction and 4 to 6 hours of assignments each week.
   * - **Cost**
     - Free, apart from small model charges.

Learning Objectives
-------------------

By the end of the course, students can:

1. Compare full stack architectures, and choose one for a project.
2. Explain and debug how Django serves React apps, including builds and static files.
3. Connect React to a Django REST API securely, with sessions, CSRF and account scoping.
4. Define typed contracts between back end and front end, and test both sides.
5. Deliver a complete page, from Django URL to React component, following an application's
   patterns.
6. Explain how full stack changes are built, tested and released in CI.

Technical Prerequisites
-----------------------

- **Required:** Python (classes, decorators, type hints) and JavaScript (modules, promises,
  ``async``/``await``).
- **Required:** basic Django and basic React.
- **Required:** Git and GitHub, the command line, Docker basics, HTTP and JSON.
- **Required by the end of week 1:** Smarter installed from source.
- **Helpful:** TypeScript, the browser's network panel, and GitHub Actions.

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
     - **Architectures.** Server-rendered, single-page and hybrid applications, and their
       trade-offs.
   * - 1
     - Lecture 2
     - **Installing Smarter from source.** The containers, the ``Makefile``, and getting changes
       into them.
   * - 1
     - Lecture 3
     - **Hosting React in Django.** View, template, template tag, root element and data
       attributes.
   * - 1
     - Live session 1
     - Installation triage. Live trace of a list page from URL to component. Start Assignment 1.
   * - 2
     - Lecture 4
     - **Builds and static files.** The Vite manifest, ``collectstatic``, ``make react-build``, and
       failure modes.
   * - 2
     - Lecture 5
     - **Authentication across the stack.** Sessions, CSRF, cookies and ``SameSite``, API keys,
       and CORS for embedded apps, limited to each LLMClient's ``allowedOrigins``.
   * - 2
     - Lecture 6
     - **The list page API contract.** List, clone, rename and delete; ``fetchDjangoUrl`` and
       ``SessionContext``.
   * - 2
     - Live session 2
     - Review of Assignment 1. Pairs diagnose deliberately broken pages. Start Assignment 2.
   * - 3
     - Lecture 7
     - **Typed contracts.** Pydantic models, JSON Schema and generated TypeScript types
       (:doc:`/smarter-framework/smarter-chat/api-contract`).
   * - 3
     - Lecture 8
     - **Testing the back end.** Django API tests, scoping tests, fixtures, and the shared
       ``ResourceViewsTestMixin`` that tests every list page's views.
   * - 3
     - Lecture 9
     - **Testing the front end.** Vitest, Testing Library and MSW, and keeping mocks honest.
   * - 3
     - Live session 3
     - Review of Assignment 2. Live addition of a field from model to pixel. Capstone proposals
       discussed. Start Assignment 3.
   * - 4
     - Lecture 10
     - **Adding a page.** The sidebar link, the Django view and template, and a new React package
       in the workspace.
   * - 4
     - Lecture 11
     - **CI and release.** The ``python`` and ``react`` jobs in ``.github/workflows/test.yml``,
       builds, and semantic releases.
   * - 4
     - Lecture 12
     - **Performance and caching.** Query counts behind a page, browser caching of built assets,
       and perceived performance.
   * - 4
     - Live session 4
     - Capstone demonstrations (about 6 minutes each, with 2 minutes of review questions), and a
       course retrospective.

Assignments 1 to 3 are due before the next live session. Assignment 4 is due in the middle of week
4. The capstone proposal is due before Live session 3, and the capstone at the start of Live
session 4.

Smarter in the Source Code
--------------------------

.. include:: source-code.txt

Graded Assignments
------------------

Assignment 1: Page Trace
~~~~~~~~~~~~~~~~~~~~~~~~

Students document how two list pages reach the screen, and identify exactly what differs between
them on the server and in the client.

**Turn in:** diagrams and a Markdown explanation in their fork, with network evidence.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Server side
     - 6
     - URL, view, template, tag and static files, with file names.
     - Incomplete.
   * - Client side
     - 6
     - Entry point, components and API calls.
     - Components only.
   * - Differences
     - 4
     - Precise.
     - Superficial.
   * - Evidence
     - 4
     - Network panel and logs.
     - Inferred.

Assignment 2: Diagnosis and Authentication Report
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students write up the broken page they fixed, and explain, with evidence from the network panel,
how one API request from the console is authenticated and protected against CSRF.

**Turn in:** a two-page report.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Diagnosis
     - 6
     - Correct cause, with the evidence trail.
     - Symptom only.
   * - Authentication
     - 6
     - Cookies, headers and the server-side checks explained correctly.
     - Partly correct.
   * - CSRF
     - 5
     - Explains the attack and the defense.
     - Names CSRF without explaining it.
   * - Clarity
     - 3
     - Well organized.
     - Hard to follow.

Assignment 3: Database to Pixel, Both Sides Tested
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students expose an existing field on a list page and add a server-side filter for it, with Django
and Vitest tests.

**Turn in:** a pull request against their fork.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - End to end
     - 6
     - Every layer, including the filter.
     - A layer missing.
   * - Scoping and validation
     - 4
     - Filter validated and scoped to the account.
     - Unvalidated.
   * - Tests
     - 6
     - Both sides, including invalid input.
     - One side.
   * - Quality
     - 4
     - All hooks pass; verified in the console.
     - Hooks fail.

Assignment 4: A Typed Contract
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students define one list endpoint's response as a Pydantic model, publish its JSON Schema, generate
TypeScript types and use them, with a freshness test.

**Turn in:** a pull request against their fork, with a demonstration that a server rename is
caught.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Model
     - 5
     - Exact, no ``Any``.
     - Loose.
   * - Generated types used
     - 5
     - Component uses the generated types.
     - Unused.
   * - Freshness test
     - 5
     - Fails when stale.
     - Missing.
   * - Demonstration
     - 5
     - Breaking change caught.
     - Not shown.

Capstone Projects
-----------------

Students choose one, propose it before Live session 3, and demonstrate it in Live session 4.

Capstone A: A New List Page, End to End
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Add a complete page to a full stack application by following its
established patterns, on both sides, with tests.

Students add a list page to the web console for a resource that does not have one, or rebuild an
existing one from scratch on a branch, following the pattern in
:doc:`/smarter-framework/developer-reference/react-integration`: the Django view, template and
template tag, the sidebar link, a new React package, and the list, clone, rename and delete API.

**What students turn in:**

- A pull request with the Django and React changes, Django tests, Vitest tests and stories.
- The page working in the console after ``make react-build``, shown in a recording.
- A six-minute demonstration in Live session 4.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Follows the pattern
     - 25
     - Indistinguishable in structure from the existing list pages.
     - Invents its own approach.
   * - Back end
     - 20
     - All four operations, scoped and validated.
     - Some operations missing.
   * - Front end
     - 20
     - All states, accessible, consistent with the console.
     - Happy path only.
   * - Tests
     - 20
     - Both sides, including errors and other accounts.
     - Partial.
   * - Demonstration
     - 15
     - Clear and on time.
     - Overruns.

Capstone B: A Feature Across the Stack with a Typed Contract
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Design an API and its front end together, protected by a typed contract and
tests on both sides.

Students design a new feature that needs a new endpoint, for example a details drawer that shows a
resource's manifest, its recent journal entries and its cost this month. The endpoint returns a
Pydantic response model whose JSON Schema generates the TypeScript types used by the drawer.

**What students turn in:**

- A pull request with the endpoint, Pydantic model, schema, generated types, React components,
  tests and stories.
- A one-page API design note.
- A six-minute demonstration in Live session 4.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - API design
     - 20
     - Consistent with the existing API; efficient; scoped.
     - Inconsistent or slow.
   * - Contract
     - 20
     - Generated types used; freshness test.
     - Hand-written types.
   * - Front end
     - 20
     - All states, accessible.
     - Happy path only.
   * - Tests
     - 25
     - Both sides, including errors and scoping.
     - Partial.
   * - Design note and demonstration
     - 15
     - Clear trade-offs, on time.
     - Missing note.

Recommended Texts
-----------------

- **Required:** William S. Vincent, *Django for APIs* (latest edition, self-published), in week 2.
- **Required:** Alex Banks and Eve Porcello, *Learning React* (2nd edition, O'Reilly, 2020),
  chapters 8 and 10, in week 3.
- **Required:** :doc:`/smarter-framework/developer-reference/react-integration`,
  :doc:`/smarter-framework/smarter-chat/web-console-hosting` and
  :doc:`/smarter-framework/smarter-chat/api-contract`.
- **Reference:** David Thomas and Andrew Hunt, *The Pragmatic Programmer* (20th anniversary
  edition, Addison-Wesley, 2019).
- **Smarter documentation:** :doc:`/smarter-framework/developer-reference/devops/ci-cd` and
  :doc:`ADR 019 on React </adr/019-react>`.

Further Study
-------------

.. include:: further-study.txt
