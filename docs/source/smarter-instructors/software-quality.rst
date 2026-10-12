Software Quality and Quality Assurance
======================================

**Why Smarter.** Smarter has thousands of unit tests, a coverage target of 90% for each Django app,
pre-commit hooks for formatting, linting, spelling and security, conventional commits checked by
commitlint, automated semantic releases, and GitHub Actions for tests, builds and deployments.
Students see a complete quality process that already works, rather than assembling one from
fragments.

**Look at.** ``.pre-commit-config.yaml``, ``.github/workflows/``, and any app's ``tests/`` folder.

**Read.** :doc:`/smarter-framework/developer-reference/devops/test`,
:doc:`/smarter-framework/developer-reference/devops/ci-cd`,
:doc:`/smarter-framework/guides/semantic-versioning`,
:doc:`ADR 013 on testing </adr/013-testing>`, :doc:`ADR 028 on code quality </adr/028-code-quality>`.

**Exercises.**

- Run ``make coverage`` for one Django app, find its least covered module, and raise its
  coverage with meaningful tests.
- Introduce a deliberate bug, and see which tests, hooks and CI jobs catch it, and which do not.
- Fork the repository, and get the ``test.yml`` workflow passing on the fork. Use it as an
  autograder for later assignments.

See the :doc:`Smarter Instructor Guide </smarter-instructor>` to install Smarter and set up
a class.
