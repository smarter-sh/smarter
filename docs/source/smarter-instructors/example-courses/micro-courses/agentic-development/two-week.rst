Agentic Software Development: Two-Week Online Course
====================================================

A two-week online course on developing software with coding agents such as `Claude Code
<https://claude.com/claude-code>`__, taught on a real production code base. Smarter is a code base
shaped for agents: nearly all of its new code is now designed, written and tested by agents working
from `CLAUDE.md <https://github.com/smarter-sh/smarter/blob/main/CLAUDE.md>`__ and the eighteen
`Agent Skills <https://github.com/smarter-sh/smarter/tree/main/skills>`__ in ``skills/``, and its
git history shows it: since late September 2026, most commits have been authored by Claude. Its
:doc:`ImageSearchPlugin </smarter-resources/plugin/plugin/image-search>` was built by Claude Code in
a live class demonstration, from the request to a `merged pull request
<https://github.com/smarter-sh/smarter/pull/775>`__ with tests and documentation. There are six
30-minute recorded lectures and a 90-minute live session each week. Week 1 covers how agents work
and how to delegate and review, and week 2 covers instructions, safety and responsibility. See
:doc:`../course-formats` for the format, the grading scale and the course policies, and
:doc:`../agentic-development` for an overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Software developers who write Python or JavaScript.
   * - **Deployment**
     - Each student runs Smarter from source, with a fork on GitHub and a coding agent installed,
       before Live session 1.
   * - **Workload**
     - 3 hours of instruction and 4 to 6 hours of assignments each week.
   * - **Cost**
     - A coding agent subscription or API usage for each student, plus small model charges from
       Smarter's tests.

Learning Objectives
-------------------

By the end of the course, students can:

1. Explain how coding agents work, and what makes a code base agent-friendly.
2. Delegate broad, bounded tasks with clear acceptance criteria.
3. Review agent-written code and tests critically, and verify them independently.
4. Write instructions and skills that improve an agent's results, and measure the effect.
5. Work safely with agents, and take responsibility for what they produce.

Technical Prerequisites
-----------------------

- **Required:** Python or JavaScript, well enough to review a pull request.
- **Required:** Git and GitHub, including code review.
- **Required:** the command line, and Docker basics.
- **Required before Live session 1:** Smarter installed from source, and a coding agent working in
  the repository.
- **Required:** basic generative AI concepts: prompts, context windows and tool calls.
- **Helpful:** automated testing, and Markdown.

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
     - **What a coding agent is.** A model in a loop with tools, context and permissions.
   * - 1
     - Lecture 2 (30 min)
     - **How you ask.** Outcomes, evidence, acceptance criteria and the pattern-first workflow.
       :doc:`/smarter-framework/developer-reference/agentic-development`.
   * - 1
     - Lecture 3 (30 min)
     - **Reviewing agent code.** Weakened tests, swallowed errors, invented APIs, and verifying
       independently.
   * - 1
     - Live session 1 (90 min)
     - The instructor delegates a task live and reviews the result with the class. Pairs then
       delegate one of their own. Start Assignment 1.
   * - 2
     - Lecture 4 (30 min)
     - **Instructions and skills.** ``CLAUDE.md``, Agent Skills, and how Smarter's skills grew
       from repeated mistakes, such as the caching rules added by `commit eeb7a7a19
       <https://github.com/smarter-sh/smarter/commit/eeb7a7a19bccd08c0b341feecf3ca444875a1f48>`__.
       The same format as a product feature: the
       :doc:`SkillPlugin </smarter-resources/plugin/plugin/skill>`.
   * - 2
     - Lecture 5 (30 min)
     - **Safety.** Permissions, sandboxes, live credentials (and why Smarter's
       ``smarter-infrastructure-safety`` skill fakes every cloud call in tests), secrets and prompt
       injection through files.
   * - 2
     - Lecture 6 (30 min)
     - **Responsibility.** Authorship, attribution, licenses, and the changing developer role.
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

Assignment 1: Delegation and Review
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students delegate a broad, bounded change to the agent, and review the resulting pull request as a
colleague's.

**Turn in:** the request, the pull request against their fork, and a review of at least five
comments with test and hook results.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Request
     - 4
     - Outcome and acceptance criteria.
     - Steps or vague.
   * - Review
     - 8
     - Substantive.
     - "Looks good".
   * - Verification
     - 5
     - Run by the student.
     - Agent's word.
   * - Honesty
     - 3
     - Problems reported.
     - Omitted.

Assignment 2: The Bug Hunt
~~~~~~~~~~~~~~~~~~~~~~~~~~

The instructor provides three agent-written pull requests, each with a planted problem (a weakened
assertion, a swallowed exception, an invented function). Students find and explain each problem,
and write the test that would have caught it.

**Turn in:** a short report for each pull request, and the tests.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Problems found
     - 8
     - All three.
     - One.
   * - Explanation
     - 6
     - Why it is wrong and what it would cause.
     - Named only.
   * - Tests
     - 6
     - Fail on the planted problem, pass when fixed.
     - Missing or ineffective.

Assignment 3: With and Without Skills
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students compare the agent's work on the same task with and without the skills.

**Turn in:** both diffs and a one-page comparison.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Fair comparison
     - 5
     - Same task and model, fresh context.
     - Uncontrolled.
   * - Criteria
     - 6
     - Correctness, patterns, tests and time.
     - One.
   * - Analysis
     - 6
     - Linked to skill content.
     - Describes only.
   * - Conclusion
     - 3
     - Honest.
     - Assumed.

Capstone Projects
-----------------

Students choose one, and present it in Live session 2.

Capstone A: A Feature Built with an Agent
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Deliver a real feature with a coding agent while remaining its accountable
author.

Students build a feature in their fork with an agent, keep a session log, and must be able to
explain every line.

**What students turn in:**

- A pull request with code, tests and docs, passing tests and hooks.
- The request, acceptance criteria and session log.
- A one-page reflection, and a five-minute presentation with live questions on the diff.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Working feature
     - 20
     - Correct, tested, documented.
     - Partly working.
   * - Specification
     - 15
     - Clear criteria.
     - Vague.
   * - Review and intervention
     - 20
     - Problems caught and corrected.
     - Accepted everything.
   * - Understanding
     - 30
     - Explains any line when asked.
     - Cannot explain key parts.
   * - Reflection
     - 15
     - Specific and honest.
     - Generic.

Capstone B: A Skill That Works
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Improve an agent's results by writing instructions, and prove the
improvement.

Students write a skill for a recurring mistake, and run three tasks with and without it.

**What students turn in:**

- The skill, following ``skills/README.md``.
- Tasks, results and scores.
- A two-page report, and a five-minute presentation.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Problem
     - 15
     - Real and recurring.
     - Hypothetical.
   * - Skill quality
     - 25
     - Concise, specific, clear trigger.
     - Long and generic.
   * - Experiment
     - 25
     - Controlled, three tasks.
     - Uncontrolled.
   * - Results
     - 20
     - Honest.
     - Cherry-picked.
   * - Report and presentation
     - 15
     - Explains why.
     - Results only.

Recommended Texts
-----------------

- **Required:** :doc:`/smarter-framework/developer-reference/agentic-development`, and Anthropic's
  `Building effective agents <https://www.anthropic.com/engineering/building-effective-agents>`__,
  in week 1.
- **Required:** Gene Kim and Steve Yegge, *Vibe Coding* (IT Revolution, 2025), in weeks 1 and 2.
- **Reference:** the `Claude Code documentation <https://code.claude.com/docs>`__ on memory, skills,
  hooks and permissions.
- **In the repository:** `CLAUDE.md <https://github.com/smarter-sh/smarter/blob/main/CLAUDE.md>`__,
  `skills/README.md <https://github.com/smarter-sh/smarter/blob/main/skills/README.md>`__ and each
  skill's ``SKILL.md``.

Further Study
-------------

.. include:: further-study.txt
