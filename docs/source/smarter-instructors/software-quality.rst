Software Quality and Quality Assurance
======================================

**Why Smarter.** Quality is usually taught in fragments: a unit testing chapter here, a linter
there, a CI tutorial on a project with three tests. Students rarely see a complete quality process
that already works on a large codebase, or learn what each layer catches and what slips through.
Smarter has one, and every layer is in the repository:

- **Tests at scale.** More than **seven thousand** unit tests across Python and React, built on
  time-test code infrastructure like `SmarterTestBase <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/lib/unittest/base_classes.py>`__
  and shared mixins that test every resource's broker, API and views the same way.
- **Test doubles that protect production.** The development containers hold live cloud
  credentials, so an `in-memory provider
  <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/infrastructure/providers/memory.py>`__
  replaces every DNS, certificate, Kubernetes and email call in tests, and a
  `custom test runner <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/lib/unittest/runner.py>`__
  skips the tests that need real infrastructure unless they are asked for.
- **Coverage with a target.** At least 90% for each Django app, 95% where that takes moderate
  effort, measured with ``make coverage`` and reported to Codecov under separate
  `Python and React flags <https://github.com/smarter-sh/smarter/blob/main/codecov.yml>`__.
- **Checks before every commit.** The
  `pre-commit hooks <https://github.com/smarter-sh/smarter/blob/main/.pre-commit-config.yaml>`__,
  black, isort, flake8, autoflake, pyupgrade, pydocstringformatter, bandit, codespell, Prettier
  and ESLint, secret detection and commitlint, are the project's one lint standard
  (:doc:`ADR 028 </adr/028-code-quality>`).
- **CI and releases.** A `test workflow
  <https://github.com/smarter-sh/smarter/blob/main/.github/workflows/test.yml>`__ that rebuilds the
  developer environment step by step, with caches and no cloud credentials, separate workflows
  for builds, chart releases and deployments, and
  `semantic-release <https://github.com/smarter-sh/smarter/blob/main/release.config.js>`__ that
  turns conventional commits into versions and changelogs.
- **Quality when agents write the code.** Most new code is written by coding agents, against a
  definition of done in `CLAUDE.md <https://github.com/smarter-sh/smarter/blob/main/CLAUDE.md>`__
  and the `testing skills <https://github.com/smarter-sh/smarter/blob/main/skills/smarter-python-testing/SKILL.md>`__,
  so students can study how a quality process holds up when the author is a model.

Students see a complete quality process that already works, rather than assembling one from
fragments, and can measure where it is strong and where it is not.

**What the course covers.** What quality means: defects and their cost, the test pyramid and
shifting left; writing good unit tests; testing Django, with fixtures and cleanup without
transaction rollback; test doubles, and where to patch; integration tests, Celery tasks and tagged
tests; front end tests with Vitest, Testing Library, Storybook and MSW; static analysis and the
pre-commit hooks; code review, including code written by AI agents; documentation as quality; CI
with GitHub Actions, caching and matrix builds; conventional commits and automated releases; and
measuring quality with coverage, mutation testing, flaky test detection and the DORA metrics.

**Look at.**

- `.pre-commit-config.yaml <https://github.com/smarter-sh/smarter/blob/main/.pre-commit-config.yaml>`__
  and `.github/workflows/ <https://github.com/smarter-sh/smarter/tree/main/.github/workflows>`__.
- Any app's ``tests/`` folder, such as
  `guardrail/tests/ <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/guardrail/tests>`__,
  and `smarter/smarter/lib/unittest/ <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/lib/unittest>`__.
- `codecov.yml <https://github.com/smarter-sh/smarter/blob/main/codecov.yml>`__ and the
  ``coverage`` target in the `Makefile <https://github.com/smarter-sh/smarter/blob/main/Makefile>`__.

Each course plan lists every file that it uses under *Smarter in the Source Code*.

**Read.** :doc:`/smarter-framework/developer-reference/devops/test`,
:doc:`/smarter-framework/developer-reference/devops/ci-cd`,
:doc:`/smarter-framework/guides/semantic-versioning`,
:doc:`ADR 013 on testing </adr/013-testing>`, :doc:`ADR 028 on code quality </adr/028-code-quality>`.

**Exercises.**

- Run ``make coverage`` for one Django app, find its least covered module, and raise its
  coverage with meaningful tests.
- Introduce a deliberate bug, and see which tests, hooks and CI jobs catch it, and which do not.
- Fork the repository, add a ``push`` or ``pull_request`` trigger to ``test.yml``, which upstream
  starts by hand, and get it passing on the fork. Use it as an autograder for later assignments.
- Review a pull request written by a coding agent, and decide whether each of its tests checks
  behavior or only executes lines.

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
