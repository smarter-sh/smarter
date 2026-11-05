Semantic Versioning Guide
=========================

See `Conventional Commits <https://www.conventionalcommits.org/>`__

The `build <https://github.com/smarter-sh/smarter/tree/main/.github/workflows/build.yml>`__ Github Action
Workflow, which starts semantic-release after every merge into main, acts on the commit comment rules
that follow. A merge whose commits call for a release is then built, deployed by the
`deploy <https://github.com/smarter-sh/smarter/tree/main/.github/workflows/deploy.yml>`__ workflow, and
its documentation published.

As an open-source maintainer, squash feature branches onto master and
write a standardized commit message while doing so. The commit message
should be structured as follows:

   ``<type>``: This represents the type of change made in the commit.
   Common types include feat (for a new feature), fix (for a bug fix),
   chore (for routine tasks like updating dependencies), docs (for
   documentation changes), style (for code style changes), refactor (for
   refactoring existing code), test (for adding or updating tests), and
   perf (for performance improvements).

   ``[optional scope]``: This is an optional part that provides
   additional contextual information, like the part of the codebase the
   commit modifies.

   ``<description>``: This is a brief description of the changes the
   commit makes.

   ``[optional body]``: This is an optional part where you can provide a
   more detailed explanation of the changes.

   ``[optional footer(s)]``: This is also optional and is often used to
   reference issue tracker IDs.

Commit Message format
---------------------

- ``feat``: A new feature
- ``fix``: A bug fix
- ``docs``: Documentation only changes
- ``style``: Changes that do not affect the meaning of the code
  (white-space, formatting, missing semi-colons, etc)
- ``refactor``: A code change that neither fixes a bug nor adds a
  feature
- ``perf``: A code change that improves performance
- ``test``: Adding missing or correcting existing tests
- ``chore``: Changes to the build process or auxiliary tools and
  libraries such as documentation generation

Example

.. code:: console

   git commit -m "docs: add an example of a good commit message"

Breaking Changes
----------------

A ``!`` after the type or scope, or a ``BREAKING CHANGE:`` footer, makes the next release a major
one. Use it for any change that needs a manual step when an operator upgrades, such as a migration
that can't run unattended or a renamed setting, and for a breaking change to the REST api, a
manifest or the Smarter Chat contract. The footer says what an operator must do, and the release
notes repeat it. What a major version promises, and what counts as breaking, is decided in
:doc:`ADR-020 <../../adr/020-semantic-versioning>` and
:doc:`ADR-023 <../../adr/023-api-versioning>`.

.. code:: console

   git commit -m "feat(secret)!: rename SMARTER_SECRET_TTL to SMARTER_SECRET_CACHE_TTL" \
     -m "BREAKING CHANGE: set SMARTER_SECRET_CACHE_TTL in place of SMARTER_SECRET_TTL before upgrading."
