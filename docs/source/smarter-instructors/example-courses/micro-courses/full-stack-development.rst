Full Stack Development with Django and React
============================================

**Why Smarter.** Full stack courses tend to teach the back end and the front end as two separate
projects, joined at the end by a fetch call. In Smarter, Django hosts each React app, and the
seams between them are where students learn the most:

- **A hybrid architecture used by many real applications.** Each page of the web console is a
  Django page that hosts one small React app. A `view
  <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/guardrail/views/listview/view.py>`__
  and a `template
  <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/templates/react/guardrail-list.html>`__
  render a root element that carries the session's cookie names, the cookie domain and the API's
  URL as data attributes, and a `template tag
  <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/guardrail/templatetags/react_guardrail_list.py>`__
  reads Vite's build manifest, validated by `Pydantic models
  <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/lib/django/templatetags/smarter_react_contract.py>`__,
  to insert the app's hashed assets.
- **One contract for every list page.** React mounts on the root element, and calls back into
  `session-authenticated views
  <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/guardrail/views/listview/api.py>`__
  with ``fetchDjangoUrl``, which sends the CSRF token, to list, clone, rename and delete. Every
  resource's list page follows the same pattern, written down in the
  `smarter-django-react <https://github.com/smarter-sh/smarter/blob/main/skills/smarter-django-react/SKILL.md>`__
  skill, and tested by one shared `test mixin
  <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/lib/unittest/resource_views.py>`__.
- **Types that cross the stack.** The chat API's requests and responses are
  `Pydantic models <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/prompt/contract/models.py>`__,
  exported as a `JSON Schema
  <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/prompt/contract/chat-contract.schema.json>`__
  and turned into the `TypeScript types
  <https://github.com/smarter-sh/smarter/blob/main/smarter/react/packages/smarter.sh-chat/src/contract.gen.ts>`__ of the
  `smarter.sh-chat <https://github.com/smarter-sh/smarter/tree/main/smarter/react/packages/smarter.sh-chat>`__ component, so the two sides cannot
  drift apart without a failing test.
- **Real failure modes.** A missing build manifest renders an empty page with no console error,
  and ``make build`` without ``make react-build`` reuses stale static files. Students learn to
  diagnose the problems that this architecture actually has.

Students can follow a feature from database column to pixel, in a clear, complete example of a
pattern that they will meet again in their own work.

**What the course covers.** Server-rendered, single-page and hybrid architectures and their
trade-offs; installing Smarter from source; hosting React in Django: view, template, template tag,
root element and data attributes; builds and static files, the Vite manifest and
``collectstatic``; authentication across the stack: sessions, CSRF, cookies, ``SameSite``, API keys
and CORS for embedded apps; the list page API contract; typed contracts from Pydantic to
TypeScript; testing the back end and the front end, and keeping mocks honest; adding a new page
end to end; CI and releases; and performance and caching.

**Look at.**

- The guardrail list page, end to end:
  `apps/guardrail/views/listview/ <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/guardrail/views/listview>`__,
  `templates/react/guardrail-list.html <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/templates/react/guardrail-list.html>`__
  and `smarter/react/packages/smarter-guardrail-list/ <https://github.com/smarter-sh/smarter/tree/main/smarter/react/packages/smarter-guardrail-list>`__.
- `smarter/react/packages/smarter-common/ <https://github.com/smarter-sh/smarter/tree/main/smarter/react/packages/smarter-common>`__,
  for ``fetchDjangoUrl`` and ``SessionContext``.
- `smarter/smarter/apps/prompt/contract/ <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/prompt/contract>`__,
  the chat API's contract.

Each course plan lists every file that it uses, step by step, under *Smarter in the Source Code*.

**Read.** :doc:`/smarter-framework/developer-reference/react-integration`,
:doc:`/smarter-framework/smarter-chat/web-console-hosting`,
:doc:`/smarter-framework/smarter-chat/api-contract`, `Django-React Integration
<https://blog.smarter.sh/2026/05/29/react-integration/>`__, `Smarter's List Views: One Design for
Queries, Caching, Pagination and Refresh
<https://blog.smarter.sh/2026/08/15/smarter-list-views/>`__.

**Exercises.**

- Follow one list page from the Django URL, view and template, through the Vite build manifest, to
  the React component and the API it calls.
- Add a new list page for a resource, end to end, with Django and React tests.
- Study how the chat API contract is published as a JSON Schema from Pydantic models, and how
  the React side's types are generated from it. Discuss what this prevents.
- Break a page on purpose (a missing manifest, a wrong data attribute, a stale build), and write
  down how each failure looks to a user and to a developer.

**Course plans.** Three complete, ready-to-teach plans, each with a schedule, graded assignments
and rubrics, two capstone projects, recommended texts, further study and technical prerequisites.
See :doc:`course-formats` for what the formats have in common.

.. toctree::
   :maxdepth: 1

   Classroom bootcamp: 8 hours <full-stack-development/bootcamp>
   Two-week online course: 6 hours <full-stack-development/two-week>
   Four-week online course: 12 hours <full-stack-development/four-week>

See the :doc:`Smarter Instructor Guide </smarter-instructor>` to install Smarter and set up
a class.
