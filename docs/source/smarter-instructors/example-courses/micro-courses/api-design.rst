API Design and Integration
==========================

**Why Smarter.** Students usually learn APIs from one side only: they call someone else's, or
they build a toy one that nobody calls. Smarter lets them study one real API from both sides, the
server and the clients that depend on it, all in public repositories.

On the server side, Smarter's :doc:`REST API </smarter-framework/smarter-api>` is a large,
consistent design that is worth taking apart:

- **One API for every resource.** Sixteen commands under `/api/v1/cli/
  <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/api/v1/cli/urls.py>`__, such
  as ``apply``, ``describe``, ``delete``, ``deploy`` and ``logs``, work on every kind of resource,
  because the request body is a YAML manifest and a `broker
  <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/api/v1/cli/brokers.py>`__
  for each kind turns it into database rows. Beside them are resource-style DRF
  endpoints, such as ``/api/v1/guardrails/<id>/events/``, and the session-authenticated endpoints
  that the web console's list pages call, so three API styles can be compared in one codebase.
- **Versioned, and evolving in public.** The version is in the path and in every manifest
  (:doc:`ADR 023 </adr/023-api-versioning>`), and when a command was renamed, the old path was
  kept as a permanent redirect because the VS Code extension still calls it.
- **Authenticated and consistent.** API keys built on Django REST Knox, of which only a `hash is
  stored <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/lib/drf/models.py>`__; one
  `base view
  <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/api/v1/cli/views/base.py>`__
  that maps every exception to a status code and one JSON error format; and a :doc:`journal
  </smarter-platform/smarter-journal>` of every request and response.
- **Self-describing.** A typed OpenAPI 3.1 contract generated from its Pydantic models, a JSON Schema and an example
  manifest for every kind, served by the API itself, and a chat API whose `Pydantic contract
  <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/prompt/contract/models.py>`__
  is exported as a JSON Schema and tested to be current.
- **Compatible by design.** A :doc:`Proxy </smarter-resources/smarter-proxy>` passes requests
  through to OpenAI's, Anthropic's or Google's own API, so callers keep the provider's SDK and
  change only the base URL and the key.

On the client side, the API has real consumers: the Go
`smarter-cli <https://github.com/smarter-sh/smarter-cli>`__, with one subcommand per API command
and packages for macOS, Linux and Windows; the React web console; the
`@smarter.sh/ui-chat <https://github.com/smarter-sh/smarter/tree/main/smarter/react/packages/smarter.sh-chat>`__ npm package, whose TypeScript
types are generated from the chat contract; the
`smarter-vscode-yaml <https://github.com/smarter-sh/smarter-vscode-yaml>`__ editor extension; and a
typed `Python SDK <https://github.com/smarter-sh/smarter-python>`__, which keeps a copy of the
platform's OpenAPI document and contracts, pinned to a platform release, and tests every request
it sends against them. Its `ADR 022
<https://github.com/smarter-sh/smarter-python/blob/main/docs/source/adr/022-pinned-openapi.rst>`__ explains
why: the CLI once shipped two broken commands, for routes the platform had renamed, with every
unit test passing.

Smarter also has honest gaps to review. It does not configure DRF throttling, relying on budgets
and on middleware that blocks probing clients, and it returns 403 rather than 401 for a bad API
key. Students can judge both against a published style guide and the OWASP API Security Top 10.

**What the course covers.** What makes an API good: resources, methods, idempotence, status codes
and consistency; authentication, API keys and sessions; errors, and problem details (RFC 9457);
writing a client, with configuration, retries, timeouts, backoff and typed responses; chat and
streaming APIs, and compatibility with a popular API as a strategy; how the server is built with
Django REST Framework, brokers and Pydantic contracts; describing an API with OpenAPI; versioning,
deprecation and breaking changes; securing an API against the OWASP API Security Top 10; and
operating an API, with rate limits, logging, monitoring and service level objectives.

**Look at.**

- `smarter/smarter/apps/api/
  <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/api>`__, the API's URLs,
  views and brokers.
- `smarter/smarter/lib/drf/
  <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/lib/drf>`__, API keys and
  authentication.
- The `smarter-cli <https://github.com/smarter-sh/smarter-cli>`__ and
  `smarter-python <https://github.com/smarter-sh/smarter-python>`__ repositories.

Each course plan lists every file that it uses, on the server and in the clients, under *Smarter
in the Source Code*.

**Read.** :doc:`/smarter-framework/smarter-api`,
:doc:`/smarter-framework/smarter-api/authentication`,
:doc:`/smarter-framework/smarter-api/error-handling`, :doc:`/smarter-framework/smarter-api/chat`,
:doc:`/smarter-framework/smarter-chat/api-contract`, :doc:`/adr/023-api-versioning`, `Smarter's
OpenAPI Contract: One Extensibility Model for Python, Go, React and VS Code
<https://blog.smarter.sh/2026/09/05/smarter-openapi-contract/>`__, `Getting Started With
smarter-api, the Smarter Python SDK
<https://blog.smarter.sh/2026/06/06/getting-started-smarter-api/>`__.

**Exercises.**

- Call the API with ``curl`` and an API key to apply, describe and delete a resource, then do the
  same with the CLI, and compare.
- Trigger five different errors, and record each status code and body. Which would a client
  author want changed?
- Write a small client in a language of their choice that lists a user's LLMClients and chats
  with one.
- Review the API against a published style guide, and propose one improvement with a migration
  plan that does not break existing clients, such as the CLI and the VS Code extension.

**Course plans.** Three complete, ready-to-teach plans, each with a schedule, graded assignments
and rubrics, two capstone projects, recommended texts, further study and technical prerequisites.
See :doc:`course-formats` for what the formats have in common.

.. toctree::
   :maxdepth: 1

   Classroom bootcamp: 8 hours <api-design/bootcamp>
   Two-week online course: 6 hours <api-design/two-week>
   Four-week online course: 12 hours <api-design/four-week>

See the :doc:`Smarter Instructor Guide </smarter-instructor>` to install Smarter and set up
a class.
