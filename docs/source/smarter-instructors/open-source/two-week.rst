Open Source Participation: Two-Week Online Course
=================================================

A two-week online course on participating in open source, using Smarter, with six 30-minute
recorded lectures and a 90-minute live session each week. Week 1 covers how projects work and the
first contribution, and week 2 covers code contributions, review and community. See
:doc:`../course-formats` for the format, the grading scale and the course policies, and
:doc:`../open-source` for an overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Anyone who can use Git, often as a capstone to another course.
   * - **Deployment**
     - A GitHub account and a fork for each student. Students making code contributions run
       Smarter from source.
   * - **Workload**
     - 3 hours of instruction and 4 to 6 hours of assignments each week.
   * - **Cost**
     - Free.

.. note::

   Contact the maintainers in `GitHub Discussions <https://github.com/smarter-sh/smarter/discussions>`__
   at least two weeks before the course. Grade the contribution and the process, not whether it was
   merged, because volunteer reviews follow the project's schedule.

Learning Objectives
-------------------

By the end of the course, students can:

1. Explain how open source projects are organized and governed.
2. Explain what the major licenses allow and require.
3. Find suitable issues and agree an approach with maintainers.
4. Make documentation and code contributions that follow a project's conventions.
5. Give and respond to code review professionally.

Technical Prerequisites
-----------------------

- **Required:** Git, including rebasing and resolving merge conflicts.
- **Required:** a GitHub account, and forks, issues and pull requests.
- **Required:** the command line and a text editor.
- **Required:** Markdown and reStructuredText; Python or JavaScript for code contributions.
- **Helpful:** Docker.

Schedule
--------

.. list-table::
   :header-rows: 1
   :widths: 10 18 72

   * - Week
     - Item
     - Content
   * - 1
     - Lecture 1 (30 min)
     - **How open source works.** Motivations, roles, governance and economics; a tour of Smarter
       on GitHub.
   * - 1
     - Lecture 2 (30 min)
     - **Licenses.** Permissive and copyleft licenses, the AGPL, and compatibility.
   * - 1
     - Lecture 3 (30 min)
     - **The first contribution.** Reading the rules (:doc:`/smarter-framework/guides/contributing`),
       finding documentation problems, and the pull request workflow.
   * - 1
     - Live session 1 (90 min)
     - Live walkthrough of a documentation pull request, from fork to review. Students start
       their own. Start Assignment 1.
   * - 2
     - Lecture 4 (30 min)
     - **Code contributions.** Choosing an issue, asking first, conventional commits, tests,
       hooks and CI.
   * - 2
     - Lecture 5 (30 min)
     - **Code review.** Reviewing and being reviewed, and the pace of volunteer projects.
   * - 2
     - Lecture 6 (30 min)
     - **Community.** Security reports, triage, discussions, the code of conduct, and becoming a
       maintainer.
   * - 2
     - Live session 2 (90 min)
     - Capstone presentations (about 5 minutes each, with 2 minutes of questions).

Assignment 1 is due at the end of week 1, Assignment 2 in the middle of week 2, and Assignment 3
and the capstone at the start of Live session 2.

Graded Assignments
------------------

Assignment 1: Rules and Licenses
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students answer ten questions about how to contribute to Smarter, with citations, and compare four
licenses on five scenarios.

**Turn in:** the answers and the license table.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Contribution rules
     - 8
     - All correct and cited.
     - Several wrong.
   * - License analysis
     - 8
     - All scenarios correct, with reasons.
     - Several wrong.
   * - AGPL network clause
     - 4
     - Explained correctly.
     - Vague.

Assignment 2: A Documentation Pull Request
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students open a documentation pull request that fixes a genuine problem.

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
     - Genuine problem fixed.
     - Trivial.
   * - Conventions
     - 6
     - Conventional commit; hooks pass.
     - Fails.
   * - Description
     - 5
     - Clear.
     - Empty.
   * - Scope
     - 2
     - Focused.
     - Mixed.

Assignment 3: Peer Review
~~~~~~~~~~~~~~~~~~~~~~~~~

Students review two classmates' pull requests in GitHub, then respond to the reviews of their own.

**Turn in:** links to the reviews given and the responses.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Review quality
     - 8
     - Specific, actionable and kind.
     - "Looks good" or harsh.
   * - Coverage
     - 4
     - Correctness, clarity and conventions.
     - One aspect.
   * - Responses
     - 6
     - Thoughtful, with changes made.
     - Ignored.
   * - Tone
     - 2
     - Professional.
     - Unprofessional.

Capstone Projects
-----------------

Students choose one, and present it in Live session 2.

Capstone A: A Code Contribution
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** See a real code contribution through an open source project's process.

Students choose a ``good first issue`` (or one agreed with the maintainers), discuss the approach
in the issue, implement it with tests, and open a pull request upstream.

**What students turn in:**

- Links to the issue discussion and pull request.
- A process log and a short reflection.
- A five-minute presentation.

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
     - Agreed before coding.
     - No discussion.
   * - Code quality
     - 25
     - Patterns, tests and hooks.
     - Failing checks.
   * - Pull request
     - 15
     - Clear and focused.
     - Unclear.
   * - Review response
     - 20
     - Professional, with changes.
     - Ignored.
   * - Reflection and presentation
     - 15
     - Thoughtful.
     - Generic.

Capstone B: A Documentation Contribution
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Make a substantial documentation contribution that helps real users.

Students agree a documentation need with the maintainers, write it, test it on a reader, and open a
pull request upstream.

**What students turn in:**

- Links to the discussion and pull request.
- Reader test notes and a process log.
- A five-minute presentation.

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
     - Scope agreed.
     - Unannounced.
   * - Value
     - 25
     - Real gap; reader tested.
     - Marginal.
   * - Accuracy and markup
     - 20
     - Verified and valid.
     - Errors.
   * - Review response
     - 20
     - Professional.
     - Ignored.
   * - Reflection and presentation
     - 15
     - Thoughtful.
     - Generic.

Recommended Texts
-----------------

- **Required:** Karl Fogel, *Producing Open Source Software* (2nd edition, O'Reilly, 2017; free
  online). Week 1: chapters 1 and 2. Week 2: chapters on communications and licensing.
- **Required:** GitHub's `Open Source Guides <https://opensource.guide/>`__, in week 1.
- **Reference:** VM (Vicky) Brasseur, *Forge Your Future with Open Source* (Pragmatic Bookshelf,
  2018).
- **Smarter documentation:** :doc:`/smarter-framework/guides/contributing`,
  :doc:`/smarter-framework/guides/code-of-conduct`,
  :doc:`/smarter-framework/guides/developer-guidelines` and
  :doc:`/smarter-framework/guides/semantic-versioning`.

Further Study
-------------

.. include:: further-study.txt
