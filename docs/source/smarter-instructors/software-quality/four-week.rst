Software Quality: Four-Week Online Course
=========================================

A four-week online course on software quality and quality assurance, taught on Smarter's complete
quality process, with twelve 30-minute recorded lectures and a 90-minute live session each week.
Week 1 covers unit testing, week 2 test doubles, integration and front end tests, week 3 static
checks and code review, and week 4 CI, releases and measuring quality. See :doc:`../course-formats`
for the format, the grading scale and the course policies, and :doc:`../software-quality` for an
overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Software developers and QA engineers who write Python or JavaScript.
   * - **Deployment**
     - Each student runs Smarter from source, with pre-commit hooks and a fork on GitHub. Week 1
       includes time for installation.
   * - **Workload**
     - 3 hours of instruction and 4 to 6 hours of assignments each week.
   * - **Cost**
     - Free on GitHub Actions for public forks, plus a few cents of model calls when running tests.

Learning Objectives
-------------------

By the end of the course, students can:

1. Explain the layers of a quality process and their costs and benefits.
2. Write meaningful unit and integration tests in Python, and component tests in React.
3. Use test doubles correctly, and keep tests isolated from real services.
4. Configure static analysis and pre-commit hooks, and review code effectively.
5. Build CI workflows, and automate releases from conventional commits.
6. Measure test quality with coverage and mutation testing, and delivery with the DORA metrics.

Technical Prerequisites
-----------------------

- **Required:** Python or JavaScript, enough to write a unit test.
- **Required:** Git and GitHub, including pull requests.
- **Required:** the command line and Docker basics.
- **Required by the end of week 1:** Smarter installed from source, with pre-commit hooks.
- **Helpful:** both Python and JavaScript, a unit testing framework, and YAML.

Schedule
--------

.. list-table::
   :header-rows: 1
   :widths: 10 18 72

   * - Week
     - Item
     - Content
   * - 1
     - Lecture 1
     - **What quality means.** Defects and their cost, the test pyramid, and the layers of
       Smarter's process.
   * - 1
     - Lecture 2
     - **Good unit tests.** Arrange, act, assert; naming; one behavior per test.
   * - 1
     - Lecture 3
     - **Testing Django.** The test runner, ``SmarterTestBase``, fixtures in ``setUpClass``, and
       cleanup without transaction rollback. :doc:`ADR 013 </adr/013-testing>`.
   * - 1
     - Live session 1
     - Installation triage, then a live coverage run and a first test in pairs. Start
       Assignment 1.
   * - 2
     - Lecture 4
     - **Test doubles.** Mocks, fakes, stubs and spies; where to patch; the in-memory
       infrastructure provider.
   * - 2
     - Lecture 5
     - **Integration tests.** API tests, database state, Celery tasks, and the ``infrastructure``
       test tag.
   * - 2
     - Lecture 6
     - **Front end tests.** Vitest, Testing Library, Storybook stories and MSW in the React
       workspace.
   * - 2
     - Live session 2
     - Review of Assignment 1. Debugging a flaky test, live. Start Assignment 2.
   * - 3
     - Lecture 7
     - **Static analysis.** black, isort, flake8, autoflake, pyupgrade, bandit, codespell,
       Prettier and ESLint; the secret detection hooks. :doc:`ADR 028 </adr/028-code-quality>`.
   * - 3
     - Lecture 8
     - **Code review.** What to look for, how to comment, review checklists, and reviewing code
       written by AI agents.
   * - 3
     - Lecture 9
     - **Documentation as quality.** Docstrings, :doc:`ADR 029 </adr/029-docstrings>`, and docs
       checked in CI.
   * - 3
     - Live session 3
     - Review of Assignment 2. A mock code review of a real pull request. Capstone proposals
       discussed. Start Assignment 3.
   * - 4
     - Lecture 10
     - **CI.** GitHub Actions, the ``test.yml`` workflow, caching and matrix builds.
       :doc:`/smarter-framework/developer-reference/devops/ci-cd`.
   * - 4
     - Lecture 11
     - **Releases.** Conventional commits, commitlint, semantic versioning and semantic-release.
       :doc:`/smarter-framework/guides/semantic-versioning`.
   * - 4
     - Lecture 12
     - **Measuring quality.** Coverage and its limits, mutation testing, flaky tests, and the
       DORA metrics.
   * - 4
     - Live session 4
     - Capstone presentations (about 6 minutes each, with 2 minutes of questions), and a course
       retrospective.

Assignments 1 to 3 are due before the next live session. Assignment 4 is due in the middle of week
4. The capstone proposal is due before Live session 3, and the capstone at the start of Live
session 4.

Graded Assignments
------------------

Assignment 1: Coverage Analysis and Unit Tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students analyze one app's coverage, then write tests for its riskiest gap.

**Turn in:** a one-page analysis, and a pull request against their fork.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Analysis
     - 6
     - Riskiest gaps, with reasons.
     - Percentages only.
   * - Tests
     - 8
     - Behavior and errors asserted.
     - No meaningful assertions.
   * - Conventions
     - 4
     - Fixtures, cleanup, naming.
     - Leaves data.
   * - Coverage gain
     - 2
     - Shown.
     - Not shown.

Assignment 2: Isolation and Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students write an integration test for an API endpoint and a unit test for code that calls an
external service, proving that neither makes a network call, and a component test in the React
workspace.

**Turn in:** a pull request against their fork, with a half-page note on how isolation was proven.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Integration test
     - 6
     - Exercises URL, view and database; asserts the response and state.
     - Asserts the status code only.
   * - Isolation
     - 6
     - Network calls blocked and proven absent.
     - Assumed.
   * - React test
     - 5
     - Behavior through roles and events, with MSW.
     - Implementation details.
   * - Note
     - 3
     - Clear.
     - Missing.

Assignment 3: Code Review
~~~~~~~~~~~~~~~~~~~~~~~~~

Students review a merged pull request from the Smarter repository (assigned by the instructor), as
if it were still open: correctness, tests, design, security and documentation.

**Turn in:** review comments as they would be posted, and a one-page summary with a verdict.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Depth
     - 7
     - Finds substantive issues or confirms correctness with reasons.
     - Style nits only.
   * - Tests
     - 5
     - Judges whether tests cover the change.
     - Ignores tests.
   * - Tone
     - 4
     - Specific, kind and actionable.
     - Vague or harsh.
   * - Verdict
     - 4
     - Clear and justified.
     - Missing.

Assignment 4: Mutation Testing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students run a mutation testing tool (such as ``mutmut``) on one well-covered module, analyze the
surviving mutants, and add tests that kill at least three.

**Turn in:** the tool's report before and after, and a pull request with the new tests.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Ran correctly
     - 4
     - Scoped to one module; report explained.
     - Not explained.
   * - Analysis
     - 6
     - Survivors classified as real gaps or equivalent mutants.
     - Not classified.
   * - New tests
     - 6
     - Three or more mutants killed.
     - Fewer.
   * - Insight
     - 4
     - Compares mutation score with coverage.
     - None.

Capstone Projects
-----------------

Students choose one, propose it before Live session 3, and present it in Live session 4.

Capstone A: A Quality Improvement for Smarter
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Make a measurable improvement to a real project's quality process, and
justify it.

Students choose one improvement and implement it on their fork: raising an app from below 90% to
95% coverage with mutation-tested tests; adding a check to CI (for example a docs link check, or a
dependency audit); finding and fixing a flaky test; or speeding up the test workflow with caching.

**What students turn in:**

- A pull request against their fork.
- Before-and-after measurements (coverage, mutation score, run time or failure rate).
- A two-page report, and a six-minute presentation.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Value
     - 20
     - Addresses a real weakness.
     - Cosmetic.
   * - Implementation
     - 25
     - Correct and consistent with the project.
     - Inconsistent.
   * - Measurement
     - 25
     - Repeatable before and after.
     - Unmeasured.
   * - Report
     - 15
     - Explains trade-offs.
     - Lists changes.
   * - Presentation
     - 15
     - Clear and on time.
     - Overruns.

Capstone B: A Quality Process for Your Own Project
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Design and build a complete quality process for a project of your own, and
measure its effect.

Students add to a project of their own: pre-commit hooks, unit and integration tests with a
coverage threshold, mutation testing on a core module, CI on pull requests with required checks,
commitlint, automated semantic releases, and a pull request template with a review checklist.

**What students turn in:**

- A public repository with the configuration, tests and workflows.
- Evidence: passing and failing runs, a mutation report, a release, and a reviewed pull request.
- A two-page comparison with Smarter's process, and a six-minute presentation.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Static checks
     - 15
     - Format, lint, security, secrets.
     - Formatting only.
   * - Tests
     - 25
     - Unit and integration, threshold, mutation testing.
     - Unit only.
   * - CI and review
     - 20
     - Required checks and a review checklist.
     - CI only.
   * - Releases
     - 15
     - Automated from commits.
     - Manual.
   * - Comparison and presentation
     - 25
     - Thoughtful; clear.
     - Superficial.

Recommended Texts
-----------------

- **Required:** Vladimir Khorikov, *Unit Testing: Principles, Practices, and Patterns* (Manning,
  2020), in weeks 1 and 2.
- **Required:** Titus Winters, Tom Manshreck and Hyrum Wright, *Software Engineering at Google*
  (O'Reilly, 2020; free online), the chapters on code review, testing and continuous integration,
  in weeks 3 and 4.
- **Required:** Nicole Forsgren, Jez Humble and Gene Kim, *Accelerate* (IT Revolution, 2018), part
  1, in week 4.
- **Reference:** Brian Okken, *Python Testing with pytest* (2nd edition, Pragmatic Bookshelf,
  2022).
- **Smarter documentation:** :doc:`/smarter-framework/developer-reference/devops/test`,
  :doc:`/smarter-framework/developer-reference/devops/ci-cd`,
  :doc:`/smarter-framework/guides/semantic-versioning`, :doc:`/adr/013-testing`,
  :doc:`/adr/014-ci-cd` and :doc:`/adr/028-code-quality`.

Further Study
-------------

.. include:: further-study.txt
