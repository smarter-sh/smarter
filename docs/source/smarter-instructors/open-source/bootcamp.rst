Open Source Participation: Classroom Bootcamp
=============================================

An eight-hour classroom bootcamp on participating in open source, using Smarter, which is developed
in public with issues, discussions, pull requests, code review, conventional commits and automated
releases. Students learn how a project works, make a first documentation contribution during the
day, and leave with a code or documentation contribution under way. See :doc:`../course-formats`
for the standard bootcamp day, the grading scale and the course policies, and
:doc:`../open-source` for an overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Anyone who can use Git: developers, technical writers, designers and students, often as a
       capstone to another course.
   * - **Deployment**
     - Each student has a GitHub account and a fork of the repository. Students making code
       contributions run Smarter from source.
   * - **Cost**
     - Free.

.. note::

   Contact the maintainers in `GitHub Discussions <https://github.com/smarter-sh/smarter/discussions>`__
   at least two weeks before the bootcamp, so that they can label suitable issues and plan for the
   reviews. Students' pull requests are reviewed by volunteers, on the project's schedule, not the
   course's, so grade the quality of the contribution and the process, not whether it was merged.

Learning Objectives
-------------------

By the end of the bootcamp, students can:

1. Explain how an open source project is organized: maintainers, contributors, governance, and the
   documents that set the rules.
2. Explain what the major licenses (AGPL, GPL, Apache and MIT) allow and require.
3. Choose a suitable issue, and discuss an approach with maintainers before writing code.
4. Make a contribution that follows a project's conventions: branch, conventional commits, tests,
   documentation and a clear pull request.
5. Respond to code review professionally.

Technical Prerequisites
-----------------------

- **Required:** Git: clone, branch, commit, rebase, push, and resolving a simple merge conflict.
- **Required:** a GitHub account, and the GitHub workflow of forks, issues and pull requests.
- **Required:** the command line, and a text editor.
- **Required:** reading Markdown and reStructuredText; for code contributions, Python or
  JavaScript.
- **Helpful:** Docker (for running Smarter), and familiarity with the project from another course.

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
     - **Lecture 1: How open source works.** Why people and companies contribute, maintainers and
       contributors, governance, and the economics of open source. A tour of Smarter's issues,
       discussions, pull requests and releases.
   * - 2
     - 45
     - **Lab 1: Read the rules.** Read Smarter's :doc:`contributing guide </smarter-framework/guides/contributing>`,
       :doc:`code of conduct </smarter-framework/guides/code-of-conduct>`,
       :doc:`developer guidelines </smarter-framework/guides/developer-guidelines>` and
       ``SECURITY.md``, and answer questions about how to contribute. Produces Assignment 1.
   * - 3
     - 45
     - **Lecture 2: Licenses.** Copyright, permissive and copyleft licenses, the AGPL and network
       use, contributor agreements, and license compatibility.
   * - 4
     - 45
     - **Lab 2: Compare licenses.** Compare the AGPL-3.0, GPL-3.0, Apache-2.0 and MIT licenses on
       five scenarios (for example "a company runs a modified version as a web service"). Produces
       Assignment 2.
   * - 5
     - 45
     - **Lecture 3: The contribution workflow.** Finding an issue, asking first, forking and
       branching, conventional commits, pre-commit hooks, tests, and writing a pull request.
       :doc:`/smarter-framework/guides/semantic-versioning`.
   * - 6
     - 45
     - **Lecture 4: Documentation contributions.** Why documentation is the easiest first
       contribution and one of the most valued; finding unclear pages; reStructuredText basics.
   * - 7
     - 45
     - **Lab 3: A first contribution.** Find and fix a documentation problem (a typo, a broken
       command, a missing example), and open a pull request. Produces Assignment 3.
   * - 8
     - 45
     - **Lecture 5: Code review.** What reviewers look for, how to respond to comments, how to
       review others' work kindly, and how long reviews take in volunteer projects.
   * - 9
     - 45
     - **Lab 4: Review each other.** Students review two classmates' pull requests from Lab 3,
       with comments in GitHub. Ungraded.
   * - 10
     - 45
     - **Lecture 6: Beyond the first pull request.** Security reports, triaging issues, helping
       in discussions, becoming a maintainer, and open source on a résumé.
   * - 11
     - 30
     - **Capstone kickoff.** Students choose an issue and post their proposed approach in it.

Graded Assignments
------------------

Assignment 1: How to Contribute
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students answer ten questions about how to contribute to Smarter (for example: where to ask a
question, how to report a vulnerability, what a commit message must look like, what must pass
before review), citing the document that answers each.

**Turn in:** the answers with citations.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Correct answers
     - 12
     - All ten correct.
     - Several wrong.
   * - Citations
     - 6
     - Each answer cites the right document and section.
     - Missing citations.
   * - Clarity
     - 2
     - Concise.
     - Rambling.

Assignment 2: License Comparison
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students compare four licenses on five scenarios, and explain the AGPL's network clause.

**Turn in:** a table and a one-page explanation.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Scenario analysis
     - 10
     - All twenty cells correct, with reasons.
     - Several wrong.
   * - AGPL explanation
     - 6
     - Explains the network clause and why Smarter chose it.
     - Vague.
   * - Clarity
     - 4
     - Clear.
     - Confusing.

Assignment 3: A First Pull Request
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students open a documentation pull request to Smarter (or to their fork, if the maintainers prefer
that for a large class).

**Turn in:** a link to the pull request.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Real improvement
     - 7
     - Fixes a genuine problem.
     - Trivial or unnecessary change.
   * - Conventions
     - 6
     - Conventional commit, branch, hooks pass.
     - Commit message or hooks fail.
   * - Pull request description
     - 5
     - Explains the problem and the change.
     - Empty.
   * - Scope
     - 2
     - Small and focused.
     - Unrelated changes mixed in.

Capstone Projects
-----------------

Students choose one. Capstones are due one week after the bootcamp. Grade the contribution and the
process, not whether the maintainers have merged it by the deadline.

Capstone A: A Code Contribution
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** See a real code contribution through an open source project's process, from
issue to review.

Students choose an issue labelled ``good first issue`` (or another agreed with the maintainers),
discuss the approach in the issue, implement it with tests, and open a pull request upstream.

**What students turn in:**

- Links to the issue discussion and the pull request.
- A one-page log of the process: the discussion, the decisions, the review comments and the
  responses.
- A short reflection on what they learned about the project and about collaboration.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Process
     - 25
     - Approach agreed in the issue before coding.
     - Pull request opened without discussion.
   * - Code quality
     - 25
     - Follows the project's patterns; tests and hooks pass.
     - Inconsistent, failing checks.
   * - Pull request
     - 15
     - Clear description, small focused commits.
     - Unclear.
   * - Review response
     - 20
     - Responds promptly and professionally, with changes.
     - Ignores or argues with review.
   * - Reflection
     - 15
     - Specific and thoughtful.
     - Generic.

Capstone B: A Documentation Contribution
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Make a substantial documentation contribution that helps real users, through
an open source project's process.

Students choose a documentation need (ask in GitHub Discussions), such as a missing tutorial, an
outdated guide or an undocumented feature, agree the scope with the maintainers, write it, test it
on a reader, and open a pull request upstream.

**What students turn in:**

- Links to the discussion and the pull request.
- Notes from the reader test.
- A one-page log of the process and review.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Process
     - 20
     - Scope agreed with maintainers.
     - Unannounced.
   * - Value to users
     - 25
     - Fills a real gap; tested on a reader.
     - Marginal; untested.
   * - Accuracy and markup
     - 20
     - Verified; valid markup; links work.
     - Errors.
   * - Review response
     - 20
     - Professional, with changes.
     - Ignored.
   * - Reflection
     - 15
     - Thoughtful.
     - Generic.

Recommended Texts
-----------------

- **Pre-reading:** GitHub's `How to Contribute to Open Source <https://opensource.guide/how-to-contribute/>`__.
- **Reference:** Karl Fogel, *Producing Open Source Software* (2nd edition, O'Reilly, 2017; free
  at `producingoss.com <https://producingoss.com/>`__).
- **Smarter documentation:** :doc:`/smarter-framework/guides/contributing`,
  :doc:`/smarter-framework/guides/code-of-conduct`,
  :doc:`/smarter-framework/guides/developer-guidelines` and
  :doc:`/smarter-framework/guides/semantic-versioning`.

Further Study
-------------

.. include:: further-study.txt
