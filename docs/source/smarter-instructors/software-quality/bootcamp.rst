Software Quality: Classroom Bootcamp
====================================

An eight-hour classroom bootcamp on software quality and quality assurance, taught on a complete
quality process that already works: Smarter's thousands of unit tests, per-app coverage targets,
pre-commit hooks for formatting, linting, spelling and security, conventional commits, automated
semantic releases, and GitHub Actions. Students measure, extend and test that process. See
:doc:`../course-formats` for the standard bootcamp day, the grading scale and the course policies,
and :doc:`../software-quality` for an overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Software developers and QA engineers who write Python or JavaScript.
   * - **Deployment**
     - Each student runs Smarter from source, installed **before** the bootcamp, with the Python
       virtual environment and pre-commit hooks set up (``make init``), and a fork on GitHub.
   * - **Cost**
     - Free on GitHub Actions for public forks. Running the test suite makes some live model
       calls, which cost a few cents.

Learning Objectives
-------------------

By the end of the bootcamp, students can:

1. Explain the layers of a quality process: formatting, linting, static analysis, unit and
   integration tests, coverage, code review, CI and release automation.
2. Run a Django app's tests and coverage in a container, and read the results.
3. Write meaningful unit tests that raise coverage and catch real bugs.
4. Explain what each pre-commit hook does, and what it cannot catch.
5. Explain conventional commits and semantic versioning, and how they drive automated releases.

Technical Prerequisites
-----------------------

- **Required:** Python (functions, classes, exceptions) or JavaScript, enough to write a unit test.
- **Required:** Git: branch, commit, push and pull requests, and a GitHub account.
- **Required:** the command line, and Docker basics.
- **Required:** Smarter installed from source and running, and ``pre-commit run --all-files``
  completed once, before the bootcamp.
- **Helpful:** a unit testing framework (``unittest``, ``pytest``, Jest or Vitest), and YAML for
  reading workflows.

Schedule
--------

.. list-table::
   :header-rows: 1
   :widths: 8 8 84

   * - Block
     - Min
     - Content
   * - 1
     - 45
     - **Lecture 1: What quality means.** Defects and their cost, the test pyramid, shifting left,
       and the layers of Smarter's process: ``.pre-commit-config.yaml``, the test suite,
       ``.github/workflows/`` and :doc:`ADR 028 on code quality </adr/028-code-quality>`.
   * - 2
     - 45
     - **Lab 1: Measure.** Run one Django app's tests and ``make coverage`` in the ``smarter-app``
       container, read the coverage report, and find the least covered module. Produces
       Assignment 1.
   * - 3
     - 45
     - **Lecture 2: Writing good unit tests.** Arrange, act, assert; one behavior per test;
       fixtures created once per class; cleaning up without transaction rollback; and
       ``SmarterTestBase``. :doc:`ADR 013 on testing </adr/013-testing>`.
   * - 4
     - 45
     - **Lab 2: Raise coverage.** Write tests for the least covered module found in Lab 1, aiming
       at behavior rather than lines. Produces Assignment 2.
   * - 5
     - 45
     - **Lecture 3: Test doubles.** Mocks, fakes and stubs; patching external services; Smarter's
       in-memory infrastructure provider; and why tests must never touch real cloud resources.
   * - 6
     - 45
     - **Lecture 4: Automated checks before the commit.** black, isort, flake8, autoflake,
       pyupgrade, bandit, codespell, Prettier and ESLint, and the secret detection hooks. What
       each catches, and what none of them catch.
   * - 7
     - 45
     - **Lab 3: Bug hunt.** Introduce a deliberate bug (wrong comparison, missing ``await``,
       swallowed exception, hard-coded key), and record which hooks, tests and CI jobs catch it.
       Produces Assignment 3.
   * - 8
     - 45
     - **Lecture 5: CI and releases.** The ``test.yml`` workflow, conventional commits and
       commitlint, semantic versioning, and automated releases with semantic-release.
       :doc:`/smarter-framework/developer-reference/devops/ci-cd` and
       :doc:`/smarter-framework/guides/semantic-versioning`.
   * - 9
     - 45
     - **Lab 4: CI on your fork.** Enable GitHub Actions on your fork and get the test workflow
       running. Ungraded.
   * - 10
     - 45
     - **Lecture 6: Beyond the tests.** Code review, mutation testing, flaky tests, testing code
       written by AI agents, and the delivery metrics from the DORA research.
   * - 11
     - 30
     - **Capstone kickoff.** Students choose a capstone and a target module or workflow.

Graded Assignments
------------------

Assignment 1: Coverage Report
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students run one Django app's tests and coverage, and report the results: test count, duration,
coverage by module, and the three riskiest gaps.

**Turn in:** the coverage summary and a one-page analysis.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Ran correctly
     - 5
     - Tests run in the container; results reported accurately.
     - Run on the host, or results misread.
   * - Gap analysis
     - 8
     - Identifies the riskiest untested code, not just the lowest percentage.
     - Lists percentages only.
   * - Reasoning
     - 5
     - Explains why each gap matters.
     - No reasons.
   * - Clarity
     - 2
     - Clear.
     - Unclear.

Assignment 2: Meaningful Tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students raise the coverage of one module with tests that check behavior, including error paths.

**Turn in:** a pull request against their fork, with coverage before and after.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Behavior tested
     - 7
     - Each test asserts an outcome that would fail if the behavior broke.
     - Tests execute code without meaningful assertions.
   * - Error paths
     - 4
     - Invalid input and failures tested.
     - Happy path only.
   * - Conventions
     - 5
     - Fixtures in ``setUpClass``, cleanup, external calls mocked.
     - Leaves data behind, or calls real services.
   * - Coverage gain
     - 4
     - Clear gain, shown before and after.
     - Little gain, or not shown.

Assignment 3: Bug Hunt Report
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students introduce four deliberate defects of different kinds, one at a time, and record which
layer of the process catches each.

**Turn in:** a table of defect, layer that caught it (or none), and evidence; and a half-page
conclusion.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Defect variety
     - 5
     - Four different kinds (style, logic, security, secret).
     - Similar defects.
   * - Evidence
     - 6
     - Hook output or failing tests for each.
     - Claims without evidence.
   * - Analysis
     - 6
     - Explains why each layer caught it or missed it.
     - Reports results only.
   * - Improvement
     - 3
     - Proposes a check that would catch a missed defect.
     - None.

Capstone Projects
-----------------

Students choose one. Capstones are due one week after the bootcamp, as a pull request against
their fork.

Capstone A: Bring a Module to 95%
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Raise the test coverage of real production code with tests that would catch
real regressions, following the project's testing conventions.

Students pick a module below 90% coverage and bring it to at least 95%, with tests of behavior,
errors and edge cases. They show that the tests are meaningful by introducing three bugs that the
new tests catch.

**What students turn in:**

- A pull request with the tests, and coverage before and after.
- A table of three deliberate bugs and the tests that catch them.
- A short note on any code that was hard to test, and why.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Coverage
     - 20
     - 95% or more.
     - Below 90%.
   * - Meaningful assertions
     - 30
     - Three deliberate bugs caught; assertions on outcomes.
     - Tests pass even with bugs present.
   * - Conventions
     - 20
     - Fixtures, cleanup, mocks and naming as in the project.
     - Inconsistent, or touches real services.
   * - Edge cases
     - 15
     - Errors, empty and boundary inputs.
     - Happy path.
   * - Note
     - 15
     - Insightful about testability.
     - Missing.

Capstone B: A Quality Gate for Your Own Project
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Build a complete quality process for a project of your own, modeled on a
working one.

Students take a small project of their own and add the quality process that Smarter uses:
pre-commit hooks for formatting, linting, spelling, security and secrets; tests with a coverage
threshold; a GitHub Actions workflow; commitlint; and automated semantic releases.

**What students turn in:**

- A public repository with the configuration, tests and workflows.
- A passing CI run, a failing one (caught by a hook or test), and an automated release.
- A one-page comparison with Smarter's setup.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Pre-commit
     - 20
     - Format, lint, spelling, security and secret hooks.
     - Formatting only.
   * - Tests and coverage
     - 20
     - Meaningful tests; CI fails below the threshold.
     - No threshold.
   * - CI
     - 20
     - Runs hooks and tests on every push and pull request.
     - Manual only.
   * - Commits and releases
     - 20
     - Commitlint and an automated release, demonstrated.
     - Not demonstrated.
   * - Comparison
     - 20
     - Thoughtful about what to adopt and what to skip.
     - Missing.

Recommended Texts
-----------------

- **Pre-reading:** Ham Vocke, `The Practical Test Pyramid
  <https://martinfowler.com/articles/practical-test-pyramid.html>`__ (martinfowler.com, 2018).
- **Reference:** Vladimir Khorikov, *Unit Testing: Principles, Practices, and Patterns* (Manning,
  2020).
- **Smarter documentation:** :doc:`/smarter-framework/developer-reference/devops/test`,
  :doc:`/smarter-framework/developer-reference/devops/ci-cd`,
  :doc:`/smarter-framework/guides/semantic-versioning`, :doc:`/adr/013-testing` and
  :doc:`/adr/028-code-quality`.

Further Study
-------------

.. include:: further-study.txt
