Front End Development with React, Vite.js and Bootstrap
=======================================================

**Why Smarter.** Front end courses usually build one app from scratch, so students never see what
a team's codebase looks like once it has grown, or how its quality is kept up. Smarter's web
console is a real, maintained front end, organized so that a student can work on one page without
having to understand all of them:

- **One small React app per page.** An npm workspace of
  `twenty-four packages <https://github.com/smarter-sh/smarter/tree/main/smarter/react/packages>`__,
  built on React 19, TypeScript and Vite: a list page for each resource, the dashboard, a manifest
  editor, a terminal emulator, the chat, and the shared
  `@smarter/common <https://github.com/smarter-sh/smarter/tree/main/smarter/react/packages/smarter-common/src>`__,
  with its sortable headers, tabbed list views and ``fetchDjangoUrl``, which sends the session
  cookie and the CSRF token. The ``smarter-*-list`` apps are near-identical, so the
  `guardrail list <https://github.com/smarter-sh/smarter/tree/main/smarter/react/packages/smarter-guardrail-list/src>`__
  explains them all.
- **Quality tools already set up.** One shared `Storybook
  <https://github.com/smarter-sh/smarter/tree/main/smarter/react/storybook>`__ configuration with
  Mock Service Worker, about 150 Vitest and Testing Library test files with every story rendered as
  a test, and one `ESLint configuration
  <https://github.com/smarter-sh/smarter/blob/main/smarter/react/eslint.config.js>`__ with
  accessibility rules and no warnings allowed. ``make react-test`` and ``make react-lint`` run the
  same checks as the CI workflow's ``react`` job.
- **A real integration with a backend.** Each app is hosted by a Django template that passes the
  session and the API's URL as data attributes, and a `template tag
  <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/lib/django/templatetags/smarter_react_templatetag_manager.py>`__
  that reads Vite's build manifest. See :doc:`full-stack-development`.
- **A published component.** The chat interface,
  `smarter.sh-chat <https://github.com/smarter-sh/smarter/tree/main/smarter/react/packages/smarter.sh-chat>`__, is built on the chatscope UI kit,
  renders Markdown with math and Mermaid diagrams, shows a prompt's progress through Server-Sent
  Events, applies an LLMClient's :doc:`styles </smarter-resources/llmclient/styles>` as CSS custom
  properties, and is published to npm as
  `@smarter.sh/ui-chat <https://www.npmjs.com/package/@smarter.sh/ui-chat>`__, with TypeScript
  types `generated <https://github.com/smarter-sh/smarter/blob/main/smarter/react/packages/smarter.sh-chat/src/contract.gen.ts>`__
  from the server's Pydantic contract.

The console is styled with the Keen Bootstrap theme, by an explicit decision
(:doc:`ADR 026 </adr/026-keen>`), so students also learn to work within a design system rather than
around it.

**What the course covers.** React in one picture: components, JSX, props, state, effects and the
rules of hooks; TypeScript for props, state, events and API responses; the web console's
workspace; components in isolation with Storybook, args, controls and Mock Service Worker; styling
with Bootstrap, and responsive layout; accessibility, from semantic HTML to WCAG 2.2; server data,
session authentication and CSRF; context and custom hooks; testing with Vitest and Testing
Library; Vite, the build manifest and bundle size; Django integration; and the chat interface,
from Server-Sent Events to embedding it in a page of one's own.

**Look at.**

- `smarter/react/packages/ <https://github.com/smarter-sh/smarter/tree/main/smarter/react/packages>`__:
  the ``smarter-*-list`` apps, ``smarter-common`` and ``smarter-dashboard``.
- `smarter/react/packages/smarter.sh-chat/ <https://github.com/smarter-sh/smarter/tree/main/smarter/react/packages/smarter.sh-chat>`__, the chat interface.
- `smarter/react/README.md <https://github.com/smarter-sh/smarter/blob/main/smarter/react/README.md>`__
  and the `smarter-react-testing
  <https://github.com/smarter-sh/smarter/blob/main/skills/smarter-react-testing/SKILL.md>`__ skill,
  for the workspace's conventions.

Each course plan lists every file that it uses under *Smarter in the Source Code*.

**Read.** :doc:`/smarter-framework/smarter-chat/development`,
:doc:`/smarter-framework/smarter-chat/embedding`,
:doc:`/smarter-framework/developer-reference/react-integration`, :doc:`ADR 019 on React
</adr/019-react>`, `Getting Started with @smarter.sh/ui-chat
<https://blog.smarter.sh/2026/08/08/getting-started-smarter-ui-chat/>`__, `Django-React Integration
<https://blog.smarter.sh/2026/05/29/react-integration/>`__.

**Exercises.**

- Run ``make react-storybook APP=smarter-guardrail-list`` and study a list page's components in
  isolation, then write a new story for a state that has none, such as an empty list or an error.
- Add a column, a filter or a sort to a list page, with a Vitest test, and get ``make react-test``
  and ``make react-lint`` passing.
- Embed a deployed LLMClient in a page of their own with the
  `@smarter.sh/ui-chat <https://www.npmjs.com/package/@smarter.sh/ui-chat>`__ npm package, and
  brand it from the LLMClient's manifest.

**Course plans.** Three complete, ready-to-teach plans, each with a schedule, graded assignments
and rubrics, two capstone projects, recommended texts, further study and technical prerequisites.
See :doc:`course-formats` for what the formats have in common.

.. toctree::
   :maxdepth: 1

   Classroom bootcamp: 8 hours <frontend-development/bootcamp>
   Two-week online course: 6 hours <frontend-development/two-week>
   Four-week online course: 12 hours <frontend-development/four-week>

See the :doc:`Smarter Instructor Guide </smarter-instructor>` to install Smarter and set up
a class.
