Python Programming with Agentic AI Master Class: Six-Week Online Course
=======================================================================

A six-week online master class for experienced Python developers who want an AI coding agent to
multiply their output on a large codebase without multiplying its mistakes. Over 18 hours,
students read how Smarter, a large Django codebase, shipped more feature releases in three weeks
with Claude Code than in its first three and a half years, and stayed converged: the series
model of convergence and divergence, measuring a codebase, hand-built subsystems, one way to do
each thing, types and contracts, tests, linters, a runnable environment, what the agent actually
reads, ``CLAUDE.md`` and Agent Skills, docstrings and commit bodies, the antipattern of a second
way, detecting and fixing it, irreversible steps, honest review, and keeping the agent's sources
from decaying. Each topic is a one-hour module: a 30-minute recorded lecture, and a lab done in
the week's live session in the student's own project. Week 1 covers convergence, week 2 the
foundation, week 3 feedback, week 4 guidance, week 5 the antipattern, and week 6 the human in
the loop. The online format suits this course well: between live sessions, the agent does real
work in the student's project, and the next week measures it. See
:doc:`/smarter-instructors/example-courses/micro-courses/course-formats` for the grading scale
and the course policies, and :doc:`../python-agentic-ai` for an overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Experienced Python developers, technical leads and architects who are responsible for a
       large codebase, and who use, or are about to use, an AI coding agent on it.
   * - **Format**
     - Each week, three 30-minute recorded lectures (1 hour 30) and one 90-minute live session for
       the week's three labs: 3 hours of instruction a week, 18 in all.
   * - **Deployment**
     - On each student's computer, working before the first live session: Claude Code, the
       student's project with its tests running, and Smarter from source under Docker Compose,
       for reading, counting and comparing.
   * - **Models**
     - Claude Code, with the model of the student's plan. Other coding agents can do most labs,
       but the Module 10 lab reads Claude Code's transcripts. Smarter's own test suite sends
       live prompts to an LLM provider.
   * - **Workload**
     - 3 hours of instruction and 3 to 5 hours of assignments each week, and 15 to 20 hours for
       the capstone, in week 6 and the two weeks after.
   * - **Cost**
     - Free software, plus a Claude plan that includes Claude Code, or API credit, for about two
       months: from about $40 to about $400 per student, depending on the plan and how hard the
       capstone pushes the agent; check current prices when announcing the course. Running
       Smarter's tests needs an OpenAI API key with a few dollars of credit, which can be capped
       with a project budget in the OpenAI dashboard.

Learning Objectives
-------------------

By the end of the course, students can:

1. Explain why an AI coding agent makes a codebase converge or diverge, in terms of telescoping
   and geometric series, and identify what sets the ratio in a given codebase.
2. Measure a large Python codebase's convergence from its Git history, tests, coverage, linters
   and the agent's own transcripts, with Python scripts, and report what the figures do not
   show.
3. Separate a codebase's subsystems from its applications, and design by hand the foundation
   that cancels an agent's errors: ownership, response contracts, errors, secrets, settings and
   types.
4. Build the feedback loop that an agent runs alone: tests that define correct, pre-commit
   hooks, and an environment started and tested with one command.
5. Write the guidance that an agent actually reads, ``CLAUDE.md``, Agent Skills, docstrings and
   commit bodies, and keep it from decaying.
6. Find a second way to do something, eliminate every copy in one change, write its rule where
   the agent reads first, and guard it with a test.
7. Keep a human on irreversible steps, review agent-written code, and measure an agent's
   productivity honestly.

Technical Prerequisites
-----------------------

- **Required:** professional Python experience: packages and imports, classes and decorators,
  type hints, virtual environments, and a test framework such as ``unittest`` or ``pytest``.
- **Required:** *the student's project*: a Python codebase of at least about 20,000 lines, in Git
  with at least a year of history, whose tests run on the student's computer, and on which the
  student is allowed to use a coding agent. Check the employer's or the project's policy before
  the course. A student without one uses a fork of Smarter, or a large open-source Python
  project approved by the instructor.
- **Required:** Git and GitHub: branches, ``git log``, ``git blame``, tags and pull requests;
  working in a terminal with common Linux commands.
- **Required by the first live session:** Claude Code installed and signed in, and a first
  session run against the student's project.
- **Required by the end of week 1:** Docker Desktop or Docker Engine with Compose, at least 16
  GB of memory, and Smarter running from source as described in
  :doc:`/smarter-framework/guides/developer-setup`, with one of its Django apps' tests run in
  the container.
- **Helpful:** Django, Docker and Pydantic, which Smarter's code uses throughout, and the sum of
  a geometric series, from any calculus text. Students new to coding agents can take
  :doc:`/smarter-instructors/example-courses/micro-courses/agentic-development` first.
- **Not needed:** machine learning, or experience with LLM APIs.

Schedule
--------

Students watch the week's three lectures before its live session. Each module is described under
`The Modules`_.

.. list-table::
   :header-rows: 1
   :widths: 10 45 45

   * - Week
     - Lectures
     - Assignment
   * - 1
     - Modules 1 to 3: eighteen days in October; telescoping and geometric series; measuring a
       codebase.
     - Assignment 1: A Convergence Baseline.
   * - 2
     - Modules 4 to 6: subsystems by hand; one way to do each thing; types and contracts.
     - Assignment 2: The Foundation, Mapped and Contracted.
   * - 3
     - Modules 7 to 9: tests define correct; linters cancel mechanically; a runnable
       environment.
     - Assignment 3: A Feedback Loop the Agent Runs Alone.
   * - 4
     - Modules 10 to 12: what the agent reads; ``CLAUDE.md`` and Skills; docstrings, ADRs and
       commit bodies.
     - Assignment 4: Guidance the Agent Reads.
   * - 5
     - Modules 13 to 15: a second way to do things; detecting divergence; the four-step fix.
     - Assignment 5: Eliminate a Second Way. Capstone choice.
   * - 6
     - Modules 16 to 18: irreversible steps; prompts, review and honest numbers; keeping the
       sources convergent.
     - Capstone, due two weeks after the last live session.

Live Sessions
~~~~~~~~~~~~~

This course's live sessions differ from the standard session in
:doc:`/smarter-instructors/example-courses/micro-courses/course-formats`, because they hold the
labs:

- **15 minutes:** questions on the week's lectures, and what the convergence kit showed in the
  students' projects since the last session.
- **75 minutes:** the week's three labs, 25 minutes each. The instructor demonstrates the start
  of each lab in a clone of Smarter, then students work in pairs in breakout rooms, each pair
  taking turns on one student's project.

Students finish any lab that runs over on their own, before starting the week's assignment.
Assignments are due before the next live session.

The Modules
-----------

.. include:: modules.txt

The Modules in the Source Code
------------------------------

.. include:: source-code.txt

Grading
-------

.. list-table::
   :header-rows: 1
   :widths: 60 40

   * - Component
     - Weight
   * - Graded assignments
     - 50% (5 × 10%)
   * - Participation (live sessions and labs)
     - 10%
   * - Capstone project
     - 40%

The grading scale, the rubric levels and the course policies are those of
:doc:`/smarter-instructors/example-courses/micro-courses/course-formats`.

Graded Assignments
------------------

Each assignment builds on the week's labs in the student's project, and is submitted as a pull
request against the student's project or a fork of it. A student whose project's code cannot
leave their employer submits the convergence kit's output and the written parts instead, with
names changed.

Assignment 1: A Convergence Baseline
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students finish ``convergence.py`` and commit the student's project's baseline: commits, lines
and releases by author over time, tests and coverage per package, and commit bodies. A paragraph
reproduces one of Smarter's figures from Module 1 with the same script, and another estimates the
student's project's ratio with evidence from three recent changes.

**Turn in:** the pull request with the script and its output, and the two paragraphs.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Measurement
     - 8
     - Reproducible from a clean clone, counted at tags, with what each figure does not show.
     - Today's counts only.
   * - Smarter's figure
     - 4
     - Reproduced, with any difference from the lecture explained.
     - Copied from the lecture.
   * - Ratio
     - 6
     - Argued from three real changes, each with the example it copied and the feedback that
       checked it.
     - A guess.
   * - Verification
     - 2
     - Each figure spot-checked by hand.
     - Took the script's word for it.

Assignment 2: The Foundation, Mapped and Contracted
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students write a two-page foundation map of the student's project, with each subsystem's
canonical module, the missing subsystems, and each canonical helper beside the primitive it
wraps. They then annotate one subsystem boundary, give it a Pydantic model, and test it from the
outside, and show whether the contract held when the agent changed the code behind it.

**Turn in:** the foundation map, and the pull request with the contract test.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Foundation map
     - 8
     - Every subsystem and its canonical module, the missing ones named, helpers paired with
       primitives.
     - A list of folders.
   * - Types and model
     - 5
     - Annotated, no unexplained ``Any``, the boundary a Pydantic model.
     - Dictionaries in and out.
   * - Contract test
     - 7
     - Calls the boundary as a client would, and caught, or would have caught, the agent's
       change.
     - Tests the internals.

Assignment 3: A Feedback Loop the Agent Runs Alone
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students give the student's project one command that runs its tests from a clean clone and one
that starts it, and a pre-commit configuration run on the whole tree. They have the agent raise
one package's coverage by at least ten points, recording each bug it finds as an expected
failure, and check every one themselves.

**Turn in:** the pull request, and a list of the bugs found, each marked confirmed or not.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - One command
     - 5
     - The agent runs the tests and starts the project alone, on a clean clone.
     - Needs the student's help.
   * - Pre-commit
     - 4
     - Hooks run on the whole tree, findings fixed or deliberately configured.
     - Hooks installed but never run.
   * - Coverage
     - 5
     - Ten points or more, tests that assert behavior.
     - Lines executed, nothing asserted.
   * - Bugs found
     - 6
     - Each recorded as an expected failure and checked by hand.
     - Took the agent's word for it.

Assignment 4: Guidance the Agent Reads
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students write a ``CLAUDE.md`` of no more than about 150 lines for the student's project, and a
first skill that points to the narrower ones, with at least one skill written from a mistake the
agent made. They finish ``reads.py``, and report what the agent read in their own sessions before
and after the guidance existed, and the share of commits with real bodies since week 1.

**Turn in:** the pull request, and the ``reads.py`` table with a paragraph on what changed.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - CLAUDE.md
     - 5
     - Short, universal rules only, each with its reason, pointing to the first skill.
     - Everything in one long file.
   * - Skills
     - 6
     - A skill written from a real mistake, with the trap, the rule and its reason.
     - Generic advice the model already knows.
   * - Evidence
     - 6
     - Transcripts show the skill loaded; limits of the classification stated.
     - Assumed the agent read it.
   * - Commit bodies
     - 3
     - Bodies that say what was wrong, what changed and how it was tested.
     - Subject lines only.

Assignment 5: Eliminate a Second Way
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students finish ``ways.py``, find the student's project's worst second way, and fix it in four
steps: the pattern named, every copy fixed in one change by the agent and reviewed by the
student, the rule written with its reasons and exceptions in a skill, and a guard test built
with ``ast`` that fails on a new copy.

**Turn in:** the pull request, with ``ways.py``'s output before and after, and a commit body
that explains what was wrong, what changed and how it was tested.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Detection
     - 4
     - Both ways counted at every tag, with the growth shown and the copies' shared
       fingerprints.
     - One grep today.
   * - One change
     - 6
     - Every copy fixed, legitimate exceptions kept and named, the tests passing.
     - Some copies left for later.
   * - Rule
     - 4
     - Written where the agent reads first, with reasons and exceptions.
     - A rule without reasons.
   * - Guard
     - 6
     - A test that fails on a planted copy and passes on the exceptions.
     - No guard, or one that was never seen to fail.

Capstone Projects
-----------------

Students choose one in week 5, work on it in week 6, and submit it two weeks after the last live
session.

.. include:: capstones.txt

Recommended Texts
-----------------

- **Pre-reading:** the three parts of *Converge or Diverge* on blog.smarter.sh, listed under
  Further Study, and :doc:`/smarter-framework/developer-reference/agentic-development`, before
  week 1.
- **Required:** Michael C. Feathers, *Working Effectively with Legacy Code* (Prentice Hall,
  2004): getting code under test in week 3, and breaking dependencies in week 5.
- **Reference:** Adam Tornhill, *Your Code as a Crime Scene*, 2nd edition (Pragmatic Bookshelf,
  2024), on mining Git history for the patterns that a single diff hides, for weeks 1 and 5.
- **Reference:** Martin Fowler, *Refactoring: Improving the Design of Existing Code*, 2nd edition
  (Addison-Wesley, 2018), for the one change that fixes every copy.
- **Reference:** Titus Winters, Tom Manshreck and Hyrum Wright, *Software Engineering at Google*
  (O'Reilly, 2020), on large-scale changes, code review and static analysis.
- **Reference:** Harry Percival and Bob Gregory, *Architecture Patterns with Python* (O'Reilly,
  2020), and Luciano Ramalho, *Fluent Python*, 2nd edition (O'Reilly, 2022), for subsystems,
  decorators and protocols in Python.
- **Reference:** Gilbert Strang and Edwin Herman, *Calculus Volume 2* (OpenStax, 2016), free
  online, the chapter on sequences and series.
- **In the repository:** `CLAUDE.md <https://github.com/smarter-sh/smarter/blob/main/CLAUDE.md>`__,
  `skills/ <https://github.com/smarter-sh/smarter/tree/main/skills>`__, :doc:`/adr` and
  :doc:`/smarter-framework/developer-reference/devops/test`.

Further Study
-------------

.. include:: further-study.txt
