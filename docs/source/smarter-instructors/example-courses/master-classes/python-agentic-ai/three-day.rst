Python Programming with Agentic AI Master Class: Three-Day Classroom Course
===========================================================================

A three-day classroom master class for experienced Python developers who want an AI coding
agent to multiply their output on a large codebase without multiplying its mistakes. Over 18
hours, students read how Smarter, a large Django codebase, shipped more feature releases in
three weeks with Claude Code than in its first three and a half years, and stayed converged:
the series model of convergence and divergence, measuring a codebase, hand-built subsystems,
one way to do each thing, types and contracts, tests, linters, a runnable environment, what
the agent actually reads, ``CLAUDE.md`` and Agent Skills, docstrings and commit bodies, the
antipattern of a second way, detecting and fixing it, irreversible steps, honest review, and
keeping the agent's sources from decaying. Each topic is a one-hour module, a 30-minute lecture
and a 30-minute lab in the student's own project. Day 1 covers convergence and the foundation,
day 2 feedback and guidance, and day 3 the antipattern and the human in the loop. See
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
     - Three days of six hours of instruction, each day six one-hour modules. Breaks and lunch are
       not counted.
   * - **Deployment**
     - On each student's laptop, working before day 1: Claude Code, the student's project with
       its tests running, and Smarter from source under Docker Compose, for reading, counting
       and comparing.
   * - **Models**
     - Claude Code, with the model of the student's plan. Other coding agents can do most labs,
       but the Module 10 lab reads Claude Code's transcripts. Smarter's own test suite sends
       live prompts to an LLM provider.
   * - **Workload**
     - About 2 hours each evening for the day's assignment, and 15 to 20 hours for the capstone
       in the two weeks after the course.
   * - **Cost**
     - Free software, plus a Claude plan that includes Claude Code, or API credit, for the
       course and the capstone: from about $20 to about $200 per student, depending on the plan
       and how hard the capstone pushes the agent; check current prices when announcing the
       course. Running Smarter's tests needs an OpenAI API key with a few dollars of credit, which
       can be capped with a project budget in the OpenAI dashboard.

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
  with at least a year of history, whose tests run on the student's laptop, and on which the
  student is allowed to use a coding agent. Check the employer's or the project's policy before
  the course. A student without one uses a fork of Smarter, or a large open-source Python
  project approved by the instructor.
- **Required:** Git and GitHub: branches, ``git log``, ``git blame``, tags and pull requests;
  working in a terminal with common Linux commands.
- **Required before day 1:** Claude Code installed and signed in, and a first session run
  against the student's project. Send students the instructions at least a week ahead, and ask
  for a screenshot of the session.
- **Required before day 1:** Docker Desktop or Docker Engine with Compose, at least 16 GB of
  memory, and Smarter running from source as described in
  :doc:`/smarter-framework/guides/developer-setup`, with one of its Django apps' tests run in
  the container.
- **Helpful:** Django, Docker and Pydantic, which Smarter's code uses throughout, and the sum of
  a geometric series, from any calculus text. Students new to coding agents can take
  :doc:`/smarter-instructors/example-courses/micro-courses/agentic-development` first.
- **Not needed:** machine learning, or experience with LLM APIs.

Schedule
--------

Each module is described under `The Modules`_.

.. list-table::
   :header-rows: 1
   :widths: 10 30 30 30

   * - Day
     - Morning (3 hours)
     - Afternoon (3 hours)
     - Evening
   * - 1
     - Modules 1 to 3: eighteen days in October; telescoping and geometric series; measuring a
       codebase.
     - Modules 4 to 6: subsystems by hand; one way to do each thing; types and contracts.
     - Assignment 1, due at the start of day 2.
   * - 2
     - Modules 7 to 9: tests define correct; linters cancel mechanically; a runnable
       environment.
     - Modules 10 to 12: what the agent reads; ``CLAUDE.md`` and Skills; docstrings, ADRs and
       commit bodies.
     - Assignment 2, due at the start of day 3.
   * - 3
     - Modules 13 to 15: a second way to do things; detecting divergence; the four-step fix.
     - Modules 16 to 18: irreversible steps; prompts, review and honest numbers; keeping the
       sources convergent.
     - Assignment 3, due two days after the course. Capstone choice.

Each day opens with 10 minutes of questions on the previous evening's assignment, taken from the
first lecture's time. The capstone is due two weeks after the course, because a convergence
campaign needs time for the agent to do real work.

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
     - 45% (3 × 15%)
   * - Participation (labs and questions)
     - 10%
   * - Capstone project
     - 45%

The grading scale, the rubric levels and the course policies are those of
:doc:`/smarter-instructors/example-courses/micro-courses/course-formats`.

Graded Assignments
------------------

Each assignment builds on the day's labs in the student's project, and is submitted as a pull
request against the student's project or a fork of it. A student whose project's code cannot
leave their employer submits the convergence kit's output and the written parts instead, with
names changed.

Assignment 1: A Convergence Baseline
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students finish ``convergence.py`` and commit the student's project's baseline: commits, lines
and releases by author over time, tests and coverage per package, and commit bodies. A two-page
foundation map names each subsystem's canonical module, the subsystems that are missing, and
each canonical helper beside the primitive it wraps, and estimates the project's ratio with
evidence from three recent changes.

**Turn in:** the pull request with the script and its output, and the foundation map.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Measurement
     - 7
     - Reproducible from a clean clone, counted at tags, with what each figure does not show.
     - Today's counts only, or figures pasted from the agent's summary.
   * - Foundation map
     - 7
     - Every subsystem and its canonical module, the missing ones named, helpers paired with
       primitives.
     - A list of folders.
   * - Ratio
     - 4
     - Argued from three real changes, each with the example it copied and the feedback that
       checked it.
     - A guess.
   * - Verification
     - 2
     - Each figure spot-checked by hand.
     - Took the script's word for it.

Assignment 2: Feedback and Guidance
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students give the student's project one command that runs its tests from a clean clone, a
pre-commit configuration run on the whole tree, a ``CLAUDE.md`` of no more than about 150 lines,
and a first skill that points to the narrower ones, with at least one skill written from a
mistake the agent made in the labs. They finish ``reads.py`` and report what the agent read in
their own sessions before and after the guidance existed.

**Turn in:** the pull request, and the ``reads.py`` table with a paragraph on what changed.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Feedback loop
     - 6
     - The agent runs tests and hooks alone, from one command each, on a clean clone.
     - Tests that need the student's help to run.
   * - CLAUDE.md
     - 4
     - Short, universal rules only, each with its reason, pointing to the first skill.
     - Everything in one long file.
   * - Skills
     - 5
     - A skill written from a real mistake, with the trap, the rule and its reason.
     - Generic advice the model already knows.
   * - Evidence
     - 5
     - Transcripts show the skill loaded and the tests run; limits of the classification stated.
     - Assumed the agent read it.

Assignment 3: Eliminate a Second Way
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

Students choose one at the end of day 3, and submit it two weeks after the course.

.. include:: capstones.txt

Recommended Texts
-----------------

- **Pre-reading:** the three parts of *Converge or Diverge* on blog.smarter.sh, listed under
  Further Study, before day 1, and :doc:`/smarter-framework/developer-reference/agentic-development`.
- **Required:** Michael C. Feathers, *Working Effectively with Legacy Code* (Prentice Hall,
  2004), on getting a large codebase under test, which is where every convergence campaign
  starts.
- **Reference:** Adam Tornhill, *Your Code as a Crime Scene*, 2nd edition (Pragmatic Bookshelf,
  2024), on mining Git history for the patterns that a single diff hides.
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
