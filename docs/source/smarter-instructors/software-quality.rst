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

**Course plans.** Three complete, ready-to-teach plans, each with a schedule, graded assignments
and rubrics, two capstone projects, recommended texts, further study and technical prerequisites.
See :doc:`course-formats` for what the formats have in common.

.. toctree::
   :maxdepth: 1

   Classroom bootcamp: 8 hours <software-quality/bootcamp>
   Two-week online course: 6 hours <software-quality/two-week>
   Four-week online course: 12 hours <software-quality/four-week>

See the :doc:`Smarter Instructor Guide </smarter-instructor>` to install Smarter and set up
a class.
