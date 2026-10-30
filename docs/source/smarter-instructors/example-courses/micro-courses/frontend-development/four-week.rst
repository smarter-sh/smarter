Front End Development: Four-Week Online Course
==============================================

A four-week online course on front end development with React, TypeScript, Vite and Bootstrap,
taught on the pages of Smarter's web console. The console is an npm workspace of `twenty-four React
apps <https://github.com/smarter-sh/smarter/tree/main/smarter/react/packages>`__, one per page, with
shared code in ``@smarter/common``, built on React 19, TypeScript and Vite, and styled with the Keen
Bootstrap theme. Storybook, Vitest, Testing Library, Mock Service Worker, ESLint and Prettier are
already set up, with about 150 test files and every story run as a test. Each app is hosted by a
Django template, and the chat interface, `@smarter.sh/ui-chat
<https://github.com/smarter-sh/smarter/tree/main/smarter/react/packages/smarter.sh-chat>`__, is published to npm with TypeScript types generated
from the server's Pydantic contract. There are twelve 30-minute recorded lectures and a 90-minute
live session each week. Week 1 covers React and TypeScript, week 2 components and styling, week 3
data and testing, and week 4 build, integration and the chat interface. See :doc:`../course-formats`
for the format, the grading scale and the course policies, and :doc:`../frontend-development` for an
overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Developers who know JavaScript and want to learn React and professional front end tooling.
   * - **Deployment**
     - Each student has a clone of the repository with ``make react-install`` done, and installs
       Smarter from source by week 3, when pages are tested against the real API.
   * - **Workload**
     - 3 hours of instruction and 4 to 6 hours of assignments each week.
   * - **Cost**
     - Free, apart from small model charges for the chat exercises.

Learning Objectives
-------------------

By the end of the course, students can:

1. Build typed React components with props, state, effects, context and custom hooks.
2. Navigate an npm workspace of React apps that share a common package.
3. Develop components in isolation with Storybook and mocked APIs.
4. Style responsive, accessible pages with Bootstrap, and audit them for accessibility.
5. Fetch and update server data, handling loading, errors and authentication.
6. Test React with Vitest and Testing Library, and build and integrate apps with Vite.

Technical Prerequisites
-----------------------

- **Required:** JavaScript: functions, objects, arrays, destructuring, modules, promises and
  ``async``/``await``.
- **Required:** HTML and CSS basics, and the browser's developer tools.
- **Required:** Git and GitHub: clone, branch, commit, push and pull requests.
- **Required:** Node.js 24 or later and npm, and the command line.
- **Required by week 3:** Docker, and Smarter installed from source, following the
  :doc:`Developer Setup Guide </smarter-framework/guides/developer-setup>`.
- **Helpful:** TypeScript basics, JSON and REST APIs.

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
     - **React in one picture.** Components, JSX, props and rendering.
   * - 1
     - Lecture 2
     - **State and effects.** ``useState``, ``useEffect``, lifting state, and the rules of hooks.
   * - 1
     - Lecture 3
     - **TypeScript for React.** Typing props, state, events and API responses, and avoiding
       ``any``.
   * - 1
     - Live session 1
     - Tour of ``smarter/react/packages/`` and ``smarter-common``. Pairs build a small component
       together. Start Assignment 1.
   * - 2
     - Lecture 4
     - **Components in isolation.** Storybook, args, controls and Mock Service Worker.
   * - 2
     - Lecture 5
     - **Styling with Bootstrap.** Grid, utilities, components, theming and responsive layout.
   * - 2
     - Lecture 6
     - **Accessibility.** Semantic HTML, ARIA where needed, labels, focus, keyboard use, contrast,
       and WCAG 2.2.
   * - 2
     - Live session 2
     - Review of Assignment 1. Accessibility audit of a console page, live. Start Assignment 2.
   * - 3
     - Lecture 7
     - **Server data.** Fetching, loading and error states, session authentication and CSRF, and
       ``fetchDjangoUrl`` in ``smarter-common``.
   * - 3
     - Lecture 8
     - **Context and custom hooks.** Sharing state and logic, and the console's ``SessionContext``.
   * - 3
     - Lecture 9
     - **Testing React.** Vitest, Testing Library, user events, MSW in tests, and what not to test.
   * - 3
     - Live session 3
     - Review of Assignment 2. Debugging a failing test, live. Capstone proposals discussed. Start
       Assignment 3.
   * - 4
     - Lecture 10
     - **Vite and the build.** Dev server, production build, the build manifest, and bundle size.
   * - 4
     - Lecture 11
     - **Django integration.** How Django hosts each app, from template to root element to React
       (:doc:`/smarter-framework/developer-reference/react-integration`).
   * - 4
     - Lecture 12
     - **The chat interface.** A tour of ``smarter.sh-chat``: Server-Sent Events for a prompt's
       progress, Markdown with math and diagrams, branding from ``spec.config.styles``, the API
       contract and its generated types, and embedding with `@smarter.sh/ui-chat
       <https://www.npmjs.com/package/@smarter.sh/ui-chat>`__. Pre-reading: "The second line: the
       reply is untrusted HTML" in the case study `Guardrails: Can You Trust the Model?
       <https://smarter.sh/case-studies/guardrails>`__, on how the chat renders a model's reply
       safely, and "Lab 3: allowedOrigins" in the case study `One Platform, Many Tenants
       <https://smarter.sh/case-studies/multi-tenancy>`__, on letting a page embed a chatbot.
   * - 4
     - Live session 4
     - Capstone demonstrations (about 6 minutes each, with 2 minutes of code review questions),
       and a course retrospective.

Assignments 1 to 3 are due before the next live session. Assignment 4 is due in the middle of week
4. The capstone proposal is due before Live session 3, and the capstone at the start of Live
session 4.

Smarter in the Source Code
--------------------------

.. include:: source-code.txt

Graded Assignments
------------------

Assignment 1: Anatomy of a List Page
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students draw the component tree of ``smarter-guardrail-list``, list its API calls, compare it with
``smarter-secret-list``, and propose one piece of duplicated code that could move to
``smarter-common``.

**Turn in:** a Markdown file with diagrams, in their fork.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Component tree
     - 6
     - Complete, with props and state.
     - Incomplete.
   * - API calls
     - 4
     - Every call, with purpose.
     - Some missing.
   * - Comparison
     - 5
     - Similarities and differences identified precisely.
     - Superficial.
   * - Refactoring proposal
     - 5
     - A sound, specific proposal with its risks.
     - Vague ("make it shared").

Assignment 2: An Accessible, Storied Component
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students build a new presentational component with Bootstrap, with stories for every variant, and
audit it for accessibility.

**Turn in:** a pull request against their fork with screenshots at two widths and audit results.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Component design
     - 5
     - Typed, reusable, sensible defaults.
     - Hard-coded.
   * - Responsive
     - 4
     - Works at phone and desktop widths.
     - Breaks at one.
   * - Accessibility
     - 7
     - No violations; keyboard and screen reader tested.
     - Violations unaddressed.
   * - Stories
     - 4
     - Every variant.
     - One story.

Assignment 3: A Data-Driven Feature with Tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students add a filter, a sort or a new column to a list page that uses data from the API, with
loading and error states, Vitest tests with MSW, and stories.

**Turn in:** a pull request against their fork, with ``make react-test`` and ``make react-lint``
passing, and a screenshot against a running Smarter.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Works against the API
     - 5
     - Works in the real console, not only in Storybook.
     - Storybook only.
   * - States
     - 5
     - Loading, empty and error handled.
     - Happy path only.
   * - Tests
     - 6
     - Behavior tested with MSW.
     - Implementation tested.
   * - Quality
     - 4
     - Typed, linted, consistent.
     - Lint fails.

Assignment 4: Build and Bundle Report
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students build one console app for production, inspect its bundle, identify its three largest
dependencies, and try one change that reduces its size or load time, measuring before and after.

**Turn in:** a one-page report with the measurements, and the change as a pull request (or an
explanation of why it was not worth making).

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Measurement
     - 6
     - Bundle sizes and load time measured with real tools.
     - Guessed.
   * - Analysis
     - 5
     - Explains what each large dependency is for.
     - Lists sizes only.
   * - Change
     - 5
     - Measured effect, with trade-offs.
     - Unmeasured.
   * - Judgment
     - 4
     - Weighs the gain against complexity.
     - Optimizes regardless of cost.

Capstone Projects
-----------------

Students choose one, propose it before Live session 3, and demonstrate it in Live session 4.

Capstone A: A New Console Page
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Build a complete React page in an existing application, following its
patterns, from component design to tests to integration.

Students build a new page for the web console, for example a read-only "account overview" with
counts of each resource kind and recent activity, using existing API endpoints. The React app is a
new package in the workspace that follows the list pages' structure. Integrating it with Django is
optional, and is the subject of the :doc:`full stack <../full-stack-development>` course.

**What students turn in:**

- A pull request with the new package, components, stories for every state, tests and a
  ``README.md``.
- Passing ``make react-test`` and ``make react-lint``.
- A screen recording, and a six-minute demonstration in Live session 4.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Follows the patterns
     - 20
     - Structure, configuration and shared code match the existing packages.
     - Invents its own setup.
   * - Functionality
     - 20
     - Correct data, all states handled.
     - Happy path only.
   * - Tests and stories
     - 25
     - Every state storied and tested.
     - Few.
   * - Accessibility and design
     - 20
     - Responsive, accessible, consistent with the console.
     - Inconsistent or inaccessible.
   * - Demonstration
     - 15
     - Clear and on time.
     - Overruns.

Capstone B: A Branded Assistant Website
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Build a complete, accessible React site around a third-party component,
with tests and deployment.

Students build a website with Vite, React and Bootstrap for a fictional business or club, with
routing, at least four pages, a contact form with validation, and an assistant page that embeds a
deployed LLMClient with ``@smarter.sh/ui-chat``, styled to match, and deploy it. "Lab 3:
allowedOrigins" in the multi-tenancy case study shows how to let the site's origin call the
chatbot.

**What students turn in:**

- A Git repository with the site, tests, and a ``README.md``.
- A deployed site (for example on GitHub Pages or Netlify).
- An accessibility audit and a Lighthouse report.
- A six-minute demonstration in Live session 4.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Integration
     - 20
     - Chat works; origins and authentication handled as the embedding guide describes.
     - Personal API key in the page.
   * - Site quality
     - 20
     - Routing, form validation and responsive design.
     - Broken links or layouts.
   * - Accessibility and performance
     - 20
     - Audit passes; Lighthouse scores of 90 or more.
     - Violations or poor scores unaddressed.
   * - Tests
     - 20
     - Meaningful tests of pages and the form.
     - Trivial.
   * - Deployment and demonstration
     - 20
     - Live site; clear demonstration.
     - Not deployed.

Recommended Texts
-----------------

- **Required:** the `react.dev/learn <https://react.dev/learn>`__ chapters, in weeks 1 and 3.
- **Required:** Alex Banks and Eve Porcello, *Learning React* (2nd edition, O'Reilly, 2020), in
  weeks 1 to 3.
- **Required:** the W3C's `WCAG 2.2 quick reference <https://www.w3.org/WAI/WCAG22/quickref/>`__,
  in week 2.
- **Reference:** Marijn Haverbeke, *Eloquent JavaScript* (4th edition, No Starch Press, 2024; free
  online), and Adam Wathan and Steve Schoger, *Refactoring UI* (self-published, 2018), for visual
  design.
- **Smarter documentation:** :doc:`/smarter-framework/smarter-chat/development`,
  :doc:`/smarter-framework/smarter-chat/embedding`,
  :doc:`/smarter-framework/smarter-chat/api-contract` and
  :doc:`/smarter-framework/developer-reference/react-integration`.

Further Study
-------------

.. include:: further-study.txt
