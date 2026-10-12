API Design and Integration
==========================

**Why Smarter.** Smarter's :doc:`REST API </smarter-framework/smarter-api>` is versioned,
documented with Swagger, authenticated with API keys, rate limited, and returns errors in one
consistent format. Several clients are built on it: the web console, the Go command-line
interface, a Python SDK and an npm package. Students can study one API from both sides.

**Look at.** ``smarter/smarter/apps/api/``, and the
`smarter-cli <https://github.com/smarter-sh/smarter-cli>`__ repository.

**Read.** :doc:`/smarter-framework/smarter-api`, :doc:`/smarter-framework/smarter-api/authentication`,
:doc:`/smarter-framework/smarter-api/error-handling`, :doc:`/adr/023-api-versioning`.

**Exercises.**

- Call the API with ``curl`` and an API key to apply, describe and delete a resource, then do the
  same with the CLI, and compare.
- Write a small client in a language of their choice that lists a user's LLMClients and chats
  with one.
- Review the API against a published style guide, and propose one improvement with a migration
  plan that does not break existing clients.

See the :doc:`Smarter Instructor Guide </smarter-instructor>` to install Smarter and set up
a class.
