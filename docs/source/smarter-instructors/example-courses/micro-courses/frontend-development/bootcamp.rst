Front End Development: Classroom Bootcamp
=========================================

An eight-hour classroom bootcamp on front end development with React, TypeScript, Vite and
Bootstrap, taught on the pages of Smarter's web console. The console is an npm workspace of
`twenty-four React apps <https://github.com/smarter-sh/smarter/tree/main/smarter/react/packages>`__,
one per page, with shared code in ``@smarter/common``, built on React 19, TypeScript and Vite, and
styled with the Keen Bootstrap theme. Storybook, Vitest, Testing Library, Mock Service Worker,
ESLint and Prettier are already set up, with about 150 test files and every story run as a test.
Each app is hosted by a Django template, and the chat interface, `@smarter.sh/ui-chat
<https://github.com/smarter-sh/smarter-chat>`__, is published to npm with TypeScript types generated
from the server's Pydantic contract. Students study components in Storybook, add a feature to a list
page with a test, and embed a chat in a page of their own. See :doc:`../course-formats` for the
standard bootcamp day, the grading scale and the course policies, and :doc:`../frontend-development`
for an overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Developers who know JavaScript and want to learn React and professional front end tooling.
   * - **Deployment**
     - Each student has a clone of the repository with ``make react-install`` done, so that
       Storybook and the tests run. A running Smarter (from source) is needed only for Lab 4 and
       the chat embedding capstone; the instructor can provide a shared one with a deployed
       LLMClient.
   * - **Cost**
     - Free, apart from small model charges for the chat exercise.

Learning Objectives
-------------------

By the end of the bootcamp, students can:

1. Explain components, props, state, effects and hooks, and read a typed React component.
2. Navigate an npm workspace of small React apps that share a common package.
3. Develop and review components in isolation with Storybook, using mocked APIs.
4. Add a feature to a React page, with a Vitest and Testing Library test.
5. Embed a chat component from an npm package in a web page.

Technical Prerequisites
-----------------------

- **Required:** JavaScript: functions and arrow functions, objects and arrays, destructuring,
  modules (``import`` and ``export``), promises and ``async``/``await``.
- **Required:** HTML and CSS basics, and using the browser's developer tools.
- **Required:** Git: clone, branch, commit and push, and a GitHub account.
- **Required:** Node.js 24 or later and npm installed, and the command line.
- **Required:** the repository cloned and ``make react-install`` run before the bootcamp, with
  ``make react-storybook`` opening Storybook in the browser.
- **Helpful:** TypeScript basics, JSON, and REST APIs.

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
     - **Lecture 1: React in one picture.** Components, JSX, props, state, effects and hooks, and
       TypeScript types for props. How the web console is built: one small React app per page in
       ``smarter/react/packages/``, with shared code in ``smarter-common``.
   * - 2
     - 45
     - **Lab 1: Read a list page.** Take the ``smarter-guardrail-list`` app apart: its entry point,
       components, the API calls it makes, and what it shares with ``smarter-secret-list``.
       Produces Assignment 1.
   * - 3
     - 45
     - **Lecture 2: Components in isolation.** Storybook stories, args and controls, and Mock
       Service Worker for faking APIs. Why every state, including loading, empty and error, needs
       a story.
   * - 4
     - 45
     - **Lab 2: Write stories.** Find a component state with no story, such as an empty list, a
       very long name or a server error, and write stories for it with MSW mocks. Produces
       Assignment 2.
   * - 5
     - 45
     - **Lecture 3: Styling with Bootstrap.** The grid, utilities and components, responsive
       layout, and when to write your own CSS. Accessibility basics: semantic HTML, labels,
       keyboard use and contrast.
   * - 6
     - 45
     - **Lecture 4: Testing React.** Vitest, Testing Library, querying by role and label, user
       events, and testing behavior rather than implementation.
   * - 7
     - 45
     - **Lab 3: Add a feature.** Add a column, a filter or a sort to a list page, with a test, and
       get ``make react-test`` and ``make react-lint`` passing. Produces Assignment 3.
   * - 8
     - 45
     - **Lecture 5: Build and integration.** Vite, its dev server and production build, the build
       manifest, and how Django serves each app on a page of the console
       (:doc:`/smarter-framework/developer-reference/react-integration`).
   * - 9
     - 45
     - **Lab 4: Embed a chat.** Create a plain Vite app and embed a deployed LLMClient with the
       `@smarter.sh/ui-chat <https://www.npmjs.com/package/@smarter.sh/ui-chat>`__ package.
       Ungraded.
   * - 10
     - 45
     - **Lecture 6: Quality and performance.** ESLint and Prettier, bundle size, rendering
       performance, and a tour of the ``smarter-chat`` package: the chatscope UI kit,
       Markdown with math and diagrams, Server-Sent Events for a prompt's progress, branding from
       ``spec.config.styles``, and accessibility.
   * - 11
     - 30
     - **Capstone kickoff.** Students choose a capstone, create a branch, and sketch their
       component tree.

Smarter in the Source Code
--------------------------

.. include:: source-code.txt

Graded Assignments
------------------

Assignment 1: Anatomy of a List Page
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students draw the component tree of ``smarter-guardrail-list``, list the API calls it makes with
their purpose, and identify which code is shared with other list pages and where it lives.

**Turn in:** a Markdown file with a diagram, in their fork.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Component tree
     - 6
     - Complete, with props and state noted at each level.
     - Components missing, or no props or state.
   * - API calls
     - 5
     - Every call, with method, path and purpose.
     - Some calls missing.
   * - Shared code
     - 5
     - Correctly identifies what comes from ``smarter-common``.
     - Not identified.
   * - Clarity
     - 4
     - A newcomer could use it.
     - Hard to follow.

Assignment 2: Missing Stories
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students add at least three stories for component states that have none, with MSW handlers where
an API is involved.

**Turn in:** a pull request against their fork, with screenshots of the stories.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Useful states
     - 6
     - States that matter to users: empty, error, loading, long content.
     - Trivial variations of the default story.
   * - Mocks
     - 5
     - MSW handlers that match the real API's shape.
     - Mocks with made-up shapes.
   * - Conventions
     - 5
     - Follow the existing stories' structure; lint passes.
     - Inconsistent, or lint fails.
   * - Pull request
     - 4
     - Screenshots and a clear description.
     - No description.

Assignment 3: A List Page Feature
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students add a column, a filter or a sort to a list page, with a Vitest test.

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
     - The feature works in Storybook and in the console.
     - Works only in some states.
   * - Test
     - 6
     - Tests behavior through roles and user events.
     - Tests implementation details, or no test.
   * - Accessibility
     - 4
     - Labeled controls, keyboard usable.
     - Unlabeled, mouse only.
   * - Quality
     - 4
     - Typed, linted, formatted, matches the surrounding code.
     - Lint fails, or ``any`` types.

Capstone Projects
-----------------

Students choose one. Capstones are due one week after the bootcamp.

Capstone A: A Polished List Page Feature
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Deliver a user-facing front end feature with stories, tests and attention to
accessibility, as a professional pull request.

Students extend Assignment 3 into a complete feature, for example search with highlighted matches
and a clear "no results" state, sortable columns that remember the user's choice, or a bulk
selection with a confirmation dialog.

**What students turn in:**

- A pull request with the code, stories for every state, and tests.
- Passing ``make react-test`` and ``make react-lint``.
- A short screen recording of the feature, including keyboard use.

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
     - Works in every state, including empty and error.
     - Works on the happy path only.
   * - Tests and stories
     - 25
     - Every state has a story; behavior tested by role.
     - Few stories or tests.
   * - Accessibility
     - 15
     - Keyboard usable, labeled, sufficient contrast, announced changes.
     - Mouse only, or unlabeled.
   * - Code quality
     - 20
     - Typed, small components, consistent with the workspace.
     - Large components, ``any`` types.
   * - Pull request
     - 15
     - Clear description and recording.
     - No description.

Capstone B: An Embedded Assistant on a Web Page
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Integrate a third-party React component into an application of your own,
and design a responsive, accessible page around it.

Students build a small website with Vite and React for a fictional business or club, with a home
page and an "Ask us" page that embeds a deployed LLMClient using ``@smarter.sh/ui-chat``, styled to
match the site.

**What students turn in:**

- A Git repository with the site, a ``README.md`` with setup instructions, and at least three
  component tests.
- A deployed preview (for example on GitHub Pages) or a screen recording.
- A half-page note on the integration: configuration, styling, and anything that was hard.

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
     - Chat works; the site's origin is in ``allowedOrigins``; the note explains the choice of a
       public LLMClient with a budget, or a dedicated, revocable API key.
     - Works, but uses a personal API key in the page without discussing the risk.
   * - Design
     - 20
     - Responsive, consistent styling that matches the chat.
     - Breaks on a phone, or clashes.
   * - Accessibility
     - 15
     - Semantic HTML, labels, keyboard navigation.
     - Divs everywhere, mouse only.
   * - Tests
     - 20
     - Three or more meaningful tests.
     - Fewer, or trivial.
   * - Documentation
     - 20
     - Someone else could run it from the ``README.md``.
     - Missing setup steps.

Recommended Texts
-----------------

- **Pre-reading:** the *Describing the UI* and *Adding Interactivity* chapters of
  `react.dev/learn <https://react.dev/learn>`__.
- **Reference:** Alex Banks and Eve Porcello, *Learning React* (2nd edition, O'Reilly, 2020).
- **Reference:** Marijn Haverbeke, *Eloquent JavaScript* (4th edition, No Starch Press, 2024; free
  at `eloquentjavascript.net <https://eloquentjavascript.net/>`__), for students whose JavaScript
  needs a refresher.
- **Smarter documentation:** :doc:`/smarter-framework/smarter-chat/development`,
  :doc:`/smarter-framework/smarter-chat/embedding` and
  :doc:`/smarter-framework/developer-reference/react-integration`.

Further Study
-------------

.. include:: further-study.txt
