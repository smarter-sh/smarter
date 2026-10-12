Open Source Participation: Four-Week Online Course
==================================================

A four-week online course on participating in open source, using Smarter, with twelve 30-minute
recorded lectures and a 90-minute live session each week. Week 1 covers how projects work and
their licenses, week 2 the first contributions, week 3 a substantial contribution and review, and
week 4 community, security and sustainability. The four weeks give time for a contribution to go
through real review. See :doc:`../course-formats` for the format, the grading scale and the course
policies, and :doc:`../open-source` for an overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Anyone who can use Git, often as a capstone to another course.
   * - **Deployment**
     - A GitHub account and a fork for each student. Students making code contributions run
       Smarter from source, installed in week 2.
   * - **Workload**
     - 3 hours of instruction and 4 to 6 hours of assignments each week.
   * - **Cost**
     - Free.

.. note::

   Contact the maintainers in `GitHub Discussions <https://github.com/smarter-sh/smarter/discussions>`__
   at least two weeks before the course, so that they can prepare issues and plan reviews. Grade
   the contribution and the process, not whether it was merged.

Learning Objectives
-------------------

By the end of the course, students can:

1. Explain how open source projects are organized, governed and funded.
2. Explain and compare the major licenses, and how they apply to real scenarios.
3. Make documentation and code contributions that follow a project's conventions.
4. Give and respond to code review, and take part in a project's discussions.
5. Report security issues responsibly, and assess a project's health.
6. Plan a sustained contribution, and present open source work in a portfolio.

Technical Prerequisites
-----------------------

- **Required:** Git, including rebasing and resolving merge conflicts.
- **Required:** a GitHub account, and forks, issues and pull requests.
- **Required:** the command line and a text editor.
- **Required:** Markdown and reStructuredText; Python or JavaScript for code contributions.
- **Required by week 2 (for code contributions):** Docker, and Smarter installed from source.

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
     - **How open source works.** Motivations, roles, and a tour of Smarter on GitHub.
   * - 1
     - Lecture 2
     - **Governance and funding.** Benevolent dictators, foundations, companies, sponsorship, and
       maintainer burnout.
   * - 1
     - Lecture 3
     - **Licenses.** Copyright, permissive and copyleft, the AGPL, compatibility and contributor
       agreements.
   * - 1
     - Live session 1
     - A license scenarios quiz, then a tour of Smarter's issues and pull requests. Start
       Assignment 1.
   * - 2
     - Lecture 4
     - **Reading the rules.** :doc:`/smarter-framework/guides/contributing`,
       :doc:`/smarter-framework/guides/code-of-conduct`,
       :doc:`/smarter-framework/guides/developer-guidelines` and ``SECURITY.md``.
   * - 2
     - Lecture 5
     - **The pull request workflow.** Forks, branches, conventional commits, hooks, CI, and
       :doc:`/smarter-framework/guides/semantic-versioning`.
   * - 2
     - Lecture 6
     - **Documentation contributions.** Finding gaps, reStructuredText, and testing on readers.
   * - 2
     - Live session 2
     - Review of Assignment 1. Students open their first documentation pull requests together.
       Start Assignment 2.
   * - 3
     - Lecture 7
     - **Choosing a substantial issue.** Reading an issue, estimating it, and asking first.
   * - 3
     - Lecture 8
     - **Code contributions.** Following the patterns, tests, docs, and a pull request that is easy
       to review.
   * - 3
     - Lecture 9
     - **Code review.** Reviewing and being reviewed, disagreement, and patience.
   * - 3
     - Live session 3
     - Review of Assignment 2. Students present their chosen issue and approach. Capstone
       proposals discussed. Start Assignment 3.
   * - 4
     - Lecture 10
     - **Security in open source.** Coordinated disclosure, CVEs, supply chain security and the
       OpenSSF Scorecard.
   * - 4
     - Lecture 11
     - **Project health.** CHAOSS metrics, bus factor, and choosing projects to depend on.
   * - 4
     - Lecture 12
     - **Sustaining contribution.** Triage, helping in discussions, becoming a maintainer, and open
       source in a portfolio.
   * - 4
     - Live session 4
     - Capstone presentations (about 6 minutes each, with 2 minutes of questions), and a course
       retrospective.

Assignments 1 to 3 are due before the next live session. Assignment 4 is due in the middle of week
4. The capstone proposal is due before Live session 3, and the capstone at the start of Live
session 4.

Graded Assignments
------------------

Assignment 1: Licenses and Governance
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students compare four licenses on six scenarios, and describe the governance and funding of
Smarter and of one well-known project of their choice.

**Turn in:** a license table and a two-page comparison.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - License analysis
     - 8
     - All scenarios correct, with reasons.
     - Several wrong.
   * - Governance comparison
     - 8
     - Accurate, with sources.
     - Unsourced or wrong.
   * - Insight
     - 4
     - Relates governance to the project's health.
     - Description only.

Assignment 2: A Documentation Pull Request
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students open a documentation pull request that fixes a genuine problem, and review one
classmate's.

**Turn in:** links to their pull request and their review.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Real improvement
     - 6
     - Genuine.
     - Trivial.
   * - Conventions
     - 5
     - Commit, hooks, description.
     - Fails.
   * - Review given
     - 6
     - Specific, actionable, kind.
     - "Looks good".
   * - Response to review
     - 3
     - Changes made.
     - Ignored.

Assignment 3: Issue Proposal
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students choose a substantial issue, post a proposed approach in it, and respond to the
maintainers' feedback.

**Turn in:** a link to the issue comment, and a one-page plan with the files they expect to change
and the tests they will write.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Issue choice
     - 4
     - Appropriate in size and agreed.
     - Too large or unclaimed.
   * - Proposal
     - 6
     - Clear approach, with questions where unsure.
     - "I'll fix it".
   * - Plan
     - 6
     - Specific files and tests, following the patterns.
     - Vague.
   * - Communication
     - 4
     - Responds to feedback.
     - Ignored.

Assignment 4: Project Health Assessment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students assess the health of Smarter and of one dependency it uses, with CHAOSS metrics and the
OpenSSF Scorecard, and recommend one improvement for each.

**Turn in:** a two-page assessment with data.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Data
     - 7
     - Real metrics from the repositories and Scorecard.
     - Impressions.
   * - Interpretation
     - 6
     - Careful about what the metrics mean.
     - Overclaims.
   * - Recommendations
     - 5
     - Specific and realistic.
     - Generic.
   * - Clarity
     - 2
     - Clear.
     - Unclear.

Capstone Projects
-----------------

Students choose one, propose it before Live session 3, and present it in Live session 4.

Capstone A: A Substantial Code Contribution
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** See a substantial code contribution through an open source project's
process, including iterations of review.

Students implement the issue from Assignment 3, with tests and documentation, open a pull request
upstream, and work through review.

**What students turn in:**

- Links to the issue and the pull request, with its review history.
- A process log: decisions, review comments and responses.
- A two-page reflection, and a six-minute presentation.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Code quality
     - 25
     - Follows the patterns; tests, docs, hooks and CI pass.
     - Inconsistent or failing.
   * - Process
     - 20
     - Agreed approach followed.
     - Diverged without discussion.
   * - Review iterations
     - 25
     - Responds to every comment, with changes.
     - Ignores review.
   * - Pull request
     - 10
     - Clear, focused, easy to review.
     - Sprawling.
   * - Reflection and presentation
     - 20
     - Thoughtful.
     - Generic.

Capstone B: A Contribution Program
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Contribute to a project in several ways over four weeks, and build a body of
public work.

Students make at least four contributions of different kinds over the course: a documentation pull
request, a code or test pull request, an issue triage or a good bug report, and an answer in GitHub
Discussions, and present them as a portfolio.

**What students turn in:**

- Links to each contribution.
- A portfolio page (for example, a ``README.md`` on their GitHub profile) describing the work.
- A two-page reflection, and a six-minute presentation.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Breadth
     - 20
     - Four kinds of contribution.
     - One kind.
   * - Quality
     - 30
     - Each contribution is useful and follows the project's conventions.
     - Low-value contributions.
   * - Communication
     - 20
     - Professional in every interaction.
     - Abrupt.
   * - Portfolio
     - 15
     - Clear and honest.
     - Missing.
   * - Reflection and presentation
     - 15
     - Thoughtful.
     - Generic.

Recommended Texts
-----------------

- **Required:** Karl Fogel, *Producing Open Source Software* (2nd edition, O'Reilly, 2017; free
  online), across weeks 1 to 4.
- **Required:** Nadia Eghbal, *Working in Public: The Making and Maintenance of Open Source
  Software* (Stripe Press, 2020), in weeks 1 and 4.
- **Required:** VM (Vicky) Brasseur, *Forge Your Future with Open Source* (Pragmatic Bookshelf,
  2018), in weeks 2 and 3.
- **Reference:** Eric S. Raymond, *The Cathedral and the Bazaar* (O'Reilly, 1999; free online), for
  history.
- **Smarter documentation:** :doc:`/smarter-framework/guides/contributing`,
  :doc:`/smarter-framework/guides/code-of-conduct`,
  :doc:`/smarter-framework/guides/developer-guidelines`,
  :doc:`/smarter-framework/guides/semantic-versioning` and :doc:`/contributors`.

Further Study
-------------

.. include:: further-study.txt
