Front End Development: Two-Week Online Course
=============================================

A two-week online course on front end development with React, TypeScript, Vite and Bootstrap, taught
on the pages of Smarter's web console. The console is an npm workspace of `twenty-four React apps
<https://github.com/smarter-sh/smarter/tree/main/smarter/react/packages>`__, one per page, with
shared code in ``@smarter/common``, built on React 19, TypeScript and Vite, and styled with the Keen
Bootstrap theme. Storybook, Vitest, Testing Library, Mock Service Worker, ESLint and Prettier are
already set up, with about 150 test files and every story run as a test. Each app is hosted by a
Django template, and the chat interface, `@smarter.sh/ui-chat
<https://github.com/smarter-sh/smarter/tree/main/smarter/react/packages/smarter.sh-chat>`__, is published to npm with TypeScript types generated
from the server's Pydantic contract. There are six 30-minute recorded lectures and a 90-minute live
session each week. Week 1 covers React and components in isolation, and week 2 covers styling,
testing and integration. See :doc:`../course-formats` for the format, the grading scale and the
course policies, and :doc:`../frontend-development` for an overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Developers who know JavaScript and want to learn React and professional front end tooling.
   * - **Deployment**
     - Each student has a clone of the repository with ``make react-install`` done. A running
       Smarter is needed in week 2; students may install it from source, or the instructor can
       provide a shared one with a deployed LLMClient.
   * - **Workload**
     - 3 hours of instruction and 4 to 6 hours of assignments each week.
   * - **Cost**
     - Free, apart from small model charges for the chat exercise.

Learning Objectives
-------------------

By the end of the course, students can:

1. Build typed React components with props, state, effects and hooks.
2. Navigate an npm workspace of React apps that share a common package.
3. Develop components in isolation with Storybook and mocked APIs.
4. Style responsive, accessible pages with Bootstrap.
5. Test React components with Vitest and Testing Library, and integrate a third-party component.

Technical Prerequisites
-----------------------

- **Required:** JavaScript: functions, objects, arrays, destructuring, modules, promises and
  ``async``/``await``.
- **Required:** HTML and CSS basics, and the browser's developer tools.
- **Required:** Git and GitHub: clone, branch, commit, push and pull requests.
- **Required:** Node.js 24 or later and npm, and the command line.
- **Required before Live session 1:** the repository cloned, ``make react-install`` run, and
  Storybook opening with ``make react-storybook``.
- **Helpful:** TypeScript basics, JSON and REST APIs, and Docker (for running Smarter in week 2).

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
     - **React in one picture.** Components, JSX, props, state, effects, hooks and TypeScript props.
   * - 1
     - Lecture 2 (30 min)
     - **The web console's workspace.** One React app per page in ``smarter/react/packages/``,
       shared code in ``smarter-common``, and a tour of a list page.
   * - 1
     - Lecture 3 (30 min)
     - **Components in isolation.** Storybook stories, args and controls, and Mock Service Worker.
   * - 1
     - Live session 1 (90 min)
     - Live walkthrough of ``smarter-guardrail-list`` in Storybook and the code. Pairs write a
       story together. Start Assignment 1.
   * - 2
     - Lecture 4 (30 min)
     - **Styling and accessibility.** The Bootstrap grid, utilities and components, responsive
       layout, semantic HTML, labels, keyboard use and contrast.
   * - 2
     - Lecture 5 (30 min)
     - **Testing React.** Vitest, Testing Library, queries by role and label, user events.
   * - 2
     - Lecture 6 (30 min)
     - **Build and integration.** Vite builds, the build manifest, how Django serves each app
       (:doc:`/smarter-framework/developer-reference/react-integration`), and embedding a chat
       with `@smarter.sh/ui-chat <https://www.npmjs.com/package/@smarter.sh/ui-chat>`__.
   * - 2
     - Live session 2 (90 min)
     - Capstone demonstrations (about 5 minutes each, with 2 minutes of code review questions).

Assignment 1 is due at the end of week 1, Assignment 2 in the middle of week 2, and Assignment 3
and the capstone at the start of Live session 2.

Smarter in the Source Code
--------------------------

.. include:: source-code.txt

Graded Assignments
------------------

Assignment 1: Anatomy of a List Page and Missing Stories
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students draw the component tree of ``smarter-guardrail-list`` with its API calls, then add at
least three stories for states that have none, with MSW handlers.

**Turn in:** a Markdown file with the diagram, and a pull request against their fork with the
stories.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Component tree
     - 6
     - Complete, with props, state, API calls and shared code identified.
     - Incomplete.
   * - Stories
     - 6
     - Useful states (empty, error, loading, long content).
     - Trivial variations.
   * - Mocks
     - 4
     - Match the real API's shape.
     - Made-up shapes.
   * - Conventions
     - 4
     - Follow existing stories; lint passes.
     - Inconsistent.

Assignment 2: A Responsive, Accessible Component
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students build a new presentational component for the console, such as a resource summary card
with a status badge, tags and actions, using Bootstrap, with stories for each variant and an
accessibility check.

**Turn in:** a pull request against their fork, with screenshots at phone and desktop widths and
the results of Storybook's accessibility panel or an equivalent check.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Component design
     - 5
     - Typed props, sensible defaults, reusable.
     - Hard-coded content.
   * - Responsive layout
     - 5
     - Works at phone and desktop widths.
     - Breaks at one width.
   * - Accessibility
     - 6
     - No violations; keyboard and screen reader friendly.
     - Violations left unaddressed.
   * - Stories
     - 4
     - Every variant has a story.
     - One story.

Assignment 3: A List Page Feature with Tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students add a column, a filter or a sort to a list page, with Vitest tests.

**Turn in:** a pull request against their fork, with ``make react-test`` and ``make react-lint``
passing.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Works
     - 6
     - In every state, in Storybook and the console.
     - Some states only.
   * - Tests
     - 6
     - Behavior tested by role and user events.
     - Implementation tested, or no tests.
   * - Accessibility
     - 4
     - Labeled, keyboard usable.
     - Mouse only.
   * - Quality
     - 4
     - Typed, linted, consistent.
     - Lint fails.

Capstone Projects
-----------------

Students choose one, and demonstrate it in Live session 2.

Capstone A: A Polished List Page Feature
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Deliver a user-facing feature with stories, tests and accessibility, as a
professional pull request.

Students build a complete feature on a list page, such as search with highlighted matches and a
"no results" state, sortable columns that remember the user's choice, or bulk selection with a
confirmation dialog.

**What students turn in:**

- A pull request with code, stories for every state, and tests, with tests and lint passing.
- A screen recording, including keyboard use.
- A five-minute demonstration in Live session 2.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Functionality
     - 25
     - Every state, including empty and error.
     - Happy path only.
   * - Tests and stories
     - 25
     - Every state has a story; behavior tested.
     - Few.
   * - Accessibility
     - 15
     - Keyboard, labels, contrast, announced changes.
     - Mouse only.
   * - Code quality
     - 20
     - Typed, small components, consistent.
     - Large components, ``any`` types.
   * - Demonstration
     - 15
     - Clear and on time.
     - Overruns.

Capstone B: An Embedded Assistant on a Web Page
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Integrate a third-party React component into an application of your own,
and design a responsive, accessible page around it.

Students build a small Vite and React website for a fictional business or club, with at least
three pages and an "Ask us" page that embeds a deployed LLMClient with ``@smarter.sh/ui-chat``,
styled to match.

**What students turn in:**

- A Git repository with the site, tests and a ``README.md``.
- A deployed preview or a screen recording.
- A five-minute demonstration in Live session 2.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Integration
     - 25
     - Chat works, with ``allowedOrigins`` set and the authentication choice explained.
     - Works, with a personal API key in the page.
   * - Design
     - 20
     - Responsive and consistent.
     - Breaks on a phone.
   * - Accessibility
     - 15
     - Semantic HTML, labels, keyboard navigation.
     - Mouse only.
   * - Tests
     - 20
     - Meaningful component tests.
     - Trivial or none.
   * - Documentation and demonstration
     - 20
     - Runnable from the ``README.md``; clear demonstration.
     - Missing setup steps.

Recommended Texts
-----------------

- **Required:** the `react.dev/learn <https://react.dev/learn>`__ chapters, in week 1.
- **Required:** Alex Banks and Eve Porcello, *Learning React* (2nd edition, O'Reilly, 2020). Week
  1: chapters 4 to 8 on components, hooks and data. Week 2: chapter 10 on testing.
- **Reference:** Marijn Haverbeke, *Eloquent JavaScript* (4th edition, No Starch Press, 2024; free
  online).
- **Smarter documentation:** :doc:`/smarter-framework/smarter-chat/development`,
  :doc:`/smarter-framework/smarter-chat/embedding` and
  :doc:`/smarter-framework/developer-reference/react-integration`.

Further Study
-------------

.. include:: further-study.txt
