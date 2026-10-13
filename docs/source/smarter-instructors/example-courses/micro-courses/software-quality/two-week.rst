Software Quality: Two-Week Online Course
========================================

A two-week online course on software quality and quality assurance, taught on Smarter's complete
quality process. The process is all in the repository: more than five thousand Python unit tests and
about 150 React test files, `SmarterTestBase
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/lib/unittest/base_classes.py>`__
and shared test mixins, an in-memory cloud provider for test doubles, a `test runner
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/lib/unittest/runner.py>`__ that
skips tests needing real infrastructure, `pre-commit hooks
<https://github.com/smarter-sh/smarter/blob/main/.pre-commit-config.yaml>`__ as the lint standard,
Codecov flags for each suite, commitlint, semantic-release, and a `test workflow
<https://github.com/smarter-sh/smarter/blob/main/.github/workflows/test.yml>`__ that reproduces the
developer setup in CI. There are six 30-minute recorded lectures and a 90-minute live session each
week. Week 1 covers testing and coverage, and week 2 covers automated checks, CI and releases. See
:doc:`../course-formats` for the format, the grading scale and the course policies, and
:doc:`../software-quality` for an overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Software developers and QA engineers who write Python or JavaScript.
   * - **Deployment**
     - Each student runs Smarter from source, installed before Live session 1, with pre-commit
       hooks set up and a fork on GitHub.
   * - **Workload**
     - 3 hours of instruction and 4 to 6 hours of assignments each week.
   * - **Cost**
     - Free on GitHub Actions for public forks, plus a few cents of model calls when running tests.

Learning Objectives
-------------------

By the end of the course, students can:

1. Explain the layers of a quality process, and what each catches.
2. Run tests and coverage, and identify the riskiest untested code.
3. Write meaningful unit tests with fixtures and test doubles.
4. Configure and explain pre-commit hooks and CI workflows.
5. Explain conventional commits, semantic versioning and automated releases.

Technical Prerequisites
-----------------------

- **Required:** Python or JavaScript, enough to write a unit test.
- **Required:** Git and GitHub, including pull requests.
- **Required:** the command line and Docker basics.
- **Required before Live session 1:** Smarter installed from source, and
  ``pre-commit run --all-files`` completed once.
- **Helpful:** a unit testing framework, and YAML.

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
     - Lecture 1 (30 min)
     - **What quality means.** Defects and their cost, the test pyramid, and the layers of
       Smarter's process. :doc:`ADR 028 </adr/028-code-quality>`.
   * - 1
     - Lecture 2 (30 min)
     - **Good unit tests.** Arrange, act, assert; fixtures; cleanup; ``SmarterTestBase``;
       :doc:`ADR 013 </adr/013-testing>`.
   * - 1
     - Lecture 3 (30 min)
     - **Test doubles.** Mocks, fakes and stubs, patching external services, and the in-memory
       infrastructure provider.
   * - 1
     - Live session 1 (90 min)
     - Live coverage run on one app, then pairs write a first test together. Start Assignment 1.
   * - 2
     - Lecture 4 (30 min)
     - **Automated checks.** Every hook in ``.pre-commit-config.yaml``: what it catches and what
       it cannot.
   * - 2
     - Lecture 5 (30 min)
     - **CI.** The workflows in ``.github/workflows/``, and
       :doc:`/smarter-framework/developer-reference/devops/ci-cd`.
   * - 2
     - Lecture 6 (30 min)
     - **Commits and releases.** Conventional commits, commitlint, semantic versioning and
       semantic-release (:doc:`/smarter-framework/guides/semantic-versioning`).
   * - 2
     - Live session 2 (90 min)
     - Capstone presentations (about 5 minutes each, with 2 minutes of questions).

Assignment 1 is due at the end of week 1, Assignment 2 in the middle of week 2, and Assignment 3
and the capstone at the start of Live session 2.

Smarter in the Source Code
--------------------------

.. include:: source-code.txt

Graded Assignments
------------------

Assignment 1: Coverage Analysis and First Tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students run one app's coverage, identify the three riskiest gaps, and write tests for one of them.

**Turn in:** a one-page analysis, and a pull request against their fork with the tests.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Gap analysis
     - 6
     - Riskiest code, with reasons.
     - Percentages only.
   * - Tests
     - 8
     - Behavior and error paths asserted.
     - Execute code without asserting outcomes.
   * - Conventions
     - 4
     - Fixtures, cleanup, mocks.
     - Leaves data, or real calls.
   * - Coverage gain
     - 2
     - Shown.
     - Not shown.

Assignment 2: Mocks and Fakes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students write tests for code that calls an external service (an LLM provider, DNS, or HTTP), once
with ``unittest.mock`` and once with a fake, and compare the two approaches.

**Turn in:** a pull request against their fork and a half-page comparison.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - No real calls
     - 6
     - Provably isolated from the network.
     - A real call slips through.
   * - Mock test
     - 4
     - Patches at the right place; asserts the call and the outcome.
     - Patches the wrong name.
   * - Fake test
     - 4
     - Uses or extends a fake correctly.
     - Not attempted.
   * - Comparison
     - 6
     - Weighs brittleness and realism.
     - Superficial.

Assignment 3: Bug Hunt Report
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students introduce five deliberate defects of different kinds, one at a time, and record which
layer catches each, including CI on their fork.

**Turn in:** a table with evidence, and a half-page conclusion.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Variety
     - 5
     - Five kinds.
     - Similar.
   * - Evidence
     - 6
     - Hook output, failing tests, CI runs.
     - Claims.
   * - Analysis
     - 6
     - Why each was caught or missed.
     - Results only.
   * - Improvement
     - 3
     - A new check proposed.
     - None.

Capstone Projects
-----------------

Students choose one, and present it in Live session 2.

Capstone A: Bring a Module to 95%
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Raise real production code's coverage with tests that catch real
regressions.

Students bring a module below 90% to at least 95%, and prove the tests are meaningful by showing
three deliberate bugs that they catch.

**What students turn in:**

- A pull request with tests and coverage before and after.
- A table of bugs and the tests that catch them.
- A five-minute presentation.

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
     - Deliberate bugs caught.
     - Tests pass with bugs.
   * - Conventions
     - 20
     - Project conventions followed.
     - Inconsistent.
   * - Edge cases
     - 15
     - Errors and boundaries.
     - Happy path.
   * - Presentation
     - 15
     - Clear and on time.
     - Overruns.

Capstone B: A Quality Gate for Your Own Project
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Build a complete quality process for a project of your own, modeled on a
working one.

Students add pre-commit hooks, tests with a coverage threshold, a CI workflow, commitlint and
automated semantic releases to a project of their own.

**What students turn in:**

- A public repository with the configuration, tests and workflows.
- A passing run, a failing run and an automated release.
- A five-minute presentation.

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
     - Format, lint, spelling, security, secrets.
     - Formatting only.
   * - Tests and threshold
     - 20
     - Enforced in CI.
     - No threshold.
   * - CI
     - 20
     - Every push and pull request.
     - Manual.
   * - Commits and releases
     - 20
     - Demonstrated.
     - Not demonstrated.
   * - Presentation
     - 20
     - Clear, with comparison to Smarter.
     - Unclear.

Recommended Texts
-----------------

- **Required:** Vladimir Khorikov, *Unit Testing: Principles, Practices, and Patterns* (Manning,
  2020). Week 1: parts 1 and 2. Week 2: part 4 (anti-patterns).
- **Required:** the `Conventional Commits <https://www.conventionalcommits.org/>`__ and
  `Semantic Versioning <https://semver.org/>`__ specifications, in week 2.
- **Reference:** Harry Percival, *Test-Driven Development with Python* (O'Reilly; free online at
  `obeythetestinggoat.com <https://www.obeythetestinggoat.com/>`__).
- **Smarter documentation:** :doc:`/smarter-framework/developer-reference/devops/test`,
  :doc:`/smarter-framework/developer-reference/devops/ci-cd`,
  :doc:`/smarter-framework/guides/semantic-versioning`, :doc:`/adr/013-testing` and
  :doc:`/adr/028-code-quality`.

Further Study
-------------

.. include:: further-study.txt
