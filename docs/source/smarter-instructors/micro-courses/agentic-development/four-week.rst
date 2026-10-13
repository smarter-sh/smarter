Agentic Software Development: Four-Week Online Course
=====================================================

A four-week online course on developing software with coding agents such as `Claude Code
<https://claude.com/claude-code>`__, taught on a real production code base. Smarter is a code base
shaped for agents: nearly all of its new code is now designed, written and tested by agents working
from `CLAUDE.md <https://github.com/smarter-sh/smarter/blob/main/CLAUDE.md>`__ and the sixteen
`Agent Skills <https://github.com/smarter-sh/smarter/tree/main/skills>`__ in ``skills/``, and its
git history shows it: since late September 2026, most commits have been authored by Claude. Its
:doc:`ImageSearchPlugin </smarter-resources/plugin/plugin/image-search>` was built by Claude Code in
a live class demonstration, from the request to a `merged pull request
<https://github.com/smarter-sh/smarter/pull/775>`__ with tests and documentation. There are twelve
30-minute recorded lectures and a 90-minute live session each week. Week 1 covers how agents work,
week 2 delegation and review, week 3 instructions, skills and automation, and week 4 safety,
measurement and responsibility. See :doc:`../course-formats` for the format, the grading scale and
the course policies, and :doc:`../agentic-development` for an overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Software developers who write Python or JavaScript.
   * - **Deployment**
     - Each student runs Smarter from source, with a fork on GitHub and a coding agent installed.
       Week 1 includes time for setup.
   * - **Workload**
     - 3 hours of instruction and 4 to 6 hours of assignments each week.
   * - **Cost**
     - A coding agent subscription or API usage for each student, plus small model charges from
       Smarter's tests.

Learning Objectives
-------------------

By the end of the course, students can:

1. Explain how coding agents work, and what makes a code base agent-friendly.
2. Delegate tasks of different sizes, and decide when not to delegate.
3. Review and verify agent-written code and tests rigorously.
4. Write instructions, skills and hooks that improve an agent's results, and measure the effect.
5. Work safely with agents, including credentials, permissions and untrusted content.
6. Measure the effect of agents on their own productivity honestly, and take responsibility for
   what agents produce.

Technical Prerequisites
-----------------------

- **Required:** Python or JavaScript, well enough to review a pull request.
- **Required:** Git and GitHub, including code review.
- **Required:** the command line, and Docker basics.
- **Required by the end of week 1:** Smarter installed from source, and a coding agent working in
  the repository.
- **Required:** basic generative AI concepts: prompts, context windows and tool calls.
- **Helpful:** automated testing, Markdown, and shell scripting (for hooks).

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
     - Lecture 1
     - **What a coding agent is.** A model in a loop with tools, context and permissions.
   * - 1
     - Lecture 2
     - **Context.** What an agent can see, context windows, and why the code base matters more
       than the prompt.
   * - 1
     - Lecture 3
     - **Agent-friendly code bases.** Consistent structure, tests that run, and documented
       patterns, using Smarter as the example: the identical layout of the ``guardrail`` and
       ``secret`` apps, more than five thousand unit tests, the pre-commit hooks, typed aliases in
       ``lib/typing.py``, and logs that name the code that wrote them.
   * - 1
     - Live session 1
     - Setup triage, then a first delegated task, live. Start Assignment 1.
   * - 2
     - Lecture 4
     - **How you ask.** Outcomes, evidence, acceptance criteria and the pattern-first workflow.
       :doc:`/smarter-framework/developer-reference/agentic-development`.
   * - 2
     - Lecture 5
     - **Reviewing agent code.** Weakened tests, swallowed errors, invented APIs and silent scope
       creep.
   * - 2
     - Lecture 6
     - **When not to delegate.** Tasks where the agent lacks the evidence, and debugging with an
       agent: a failing test first.
   * - 2
     - Live session 2
     - Review of Assignment 1. A live review of an agent's pull request. Start Assignment 2.
   * - 3
     - Lecture 7
     - **Instructions.** ``CLAUDE.md``: what belongs in it and what does not, read line by line
       against Smarter's eight hard rules.
   * - 3
     - Lecture 8
     - **Skills.** Agent Skills, their triggers, and how Smarter's skills grew from repeated
       mistakes, such as the caching rules added by `commit eeb7a7a19
       <https://github.com/smarter-sh/smarter/commit/eeb7a7a19bccd08c0b341feecf3ca444875a1f48>`__.
       The same format as a product feature: the
       :doc:`SkillPlugin </smarter-resources/plugin/plugin/skill>`.
   * - 3
     - Lecture 9
     - **Automation.** Hooks, subagents, and running agents in CI.
   * - 3
     - Live session 3
     - Review of Assignment 2. Skill writing workshop. Capstone proposals discussed. Start
       Assignment 3.
   * - 4
     - Lecture 10
     - **Safety.** Permissions, sandboxes, live credentials, secrets, and prompt injection through
       files, issues and web pages.
   * - 4
     - Lecture 11
     - **Measuring productivity.** What studies show, why self-reports mislead, and how to
       measure your own. Smarter's own history as data: ``git shortlog`` and ``git log
       --shortstat`` before and after agents began authoring commits.
   * - 4
     - Lecture 12
     - **Responsibility.** Authorship, attribution, licenses, open source contributions, and the
       changing developer role.
   * - 4
     - Live session 4
     - Capstone presentations (about 6 minutes each, with 2 minutes of questions), and a course
       retrospective.

Assignments 1 to 3 are due before the next live session. Assignment 4 is due in the middle of week
4. The capstone proposal is due before Live session 3, and the capstone at the start of Live
session 4.

Smarter in the Source Code
--------------------------

.. include:: source-code.txt

Graded Assignments
------------------

Assignment 1: Instruction Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students summarize ``CLAUDE.md`` and three skills, and explain the reason behind four rules, with
evidence from the code or the history.

**Turn in:** a two-page analysis.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Accuracy
     - 6
     - Correct summaries.
     - Misread.
   * - Reasons
     - 8
     - Four rules, with evidence.
     - Guessed.
   * - Insight
     - 4
     - What would help a human newcomer too.
     - None.
   * - Clarity
     - 2
     - Concise.
     - Rambling.

Assignment 2: Delegation, Review and the Bug Hunt
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students delegate a change and review the result, then find the planted problems in three
agent-written pull requests provided by the instructor, with tests that catch them.

**Turn in:** the request, pull request and review; and a report and tests for the three planted
problems.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Delegation and review
     - 7
     - Clear request; substantive review; independent verification.
     - Vague request; "looks good".
   * - Planted problems
     - 7
     - All three found and explained.
     - One.
   * - Tests
     - 6
     - Fail on the problem, pass when fixed.
     - Ineffective.

Assignment 3: A Skill with an Experiment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students write a skill for a mistake they observed, and test it on two tasks with and without the
skill.

**Turn in:** the skill, both sets of results, and a one-page report.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Problem
     - 4
     - Real and observed.
     - Hypothetical.
   * - Skill
     - 7
     - Concise, specific, clear trigger.
     - Generic.
   * - Experiment
     - 6
     - Controlled.
     - Uncontrolled.
   * - Report
     - 3
     - Honest.
     - Cherry-picked.

Assignment 4: A Safety Hook
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students write a hook that stops the agent from doing something dangerous in this repository, for
example running a command that writes to real infrastructure, or committing a file that matches a
secret pattern, and show it blocking the action while allowing normal work.

**Turn in:** the hook configuration and script, and a log showing a block and an allowed action.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Threat
     - 4
     - A real risk in this repository.
     - Hypothetical.
   * - Works
     - 7
     - Blocks the action, with a clear message to the agent.
     - Blocks nothing, or everything.
   * - False positives
     - 5
     - Normal work unaffected, tested.
     - Not tested.
   * - Limits
     - 4
     - Explains how it could be bypassed.
     - Claims to be complete.

Capstone Projects
-----------------

Students choose one, propose it before Live session 3, and present it in Live session 4.

Capstone A: A Contribution Built with an Agent
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Deliver a real contribution with a coding agent, to the standard of a
reviewed open source pull request, while remaining its accountable author.

Students choose an open issue in Smarter (agreed with the maintainers in the issue first), build
it with an agent, review and verify it themselves, and open the pull request upstream, disclosing
how the agent was used.

**What students turn in:**

- The upstream pull request, with code, tests and docs, passing CI.
- The session log, with interventions and why.
- A two-page reflection, and a six-minute presentation with live questions on the diff.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Contribution quality
     - 25
     - Ready to merge; CI passes; follows the project's patterns.
     - Needs substantial rework.
   * - Process
     - 15
     - Discussed in the issue first; responds to review.
     - Unannounced; ignores review.
   * - Review and intervention
     - 20
     - Problems caught and corrected.
     - Accepted everything.
   * - Understanding
     - 25
     - Explains any line when asked.
     - Cannot explain key parts.
   * - Reflection and presentation
     - 15
     - Specific and honest.
     - Generic.

Capstone B: Making a Code Base Agent-Ready
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Apply the practices that make Smarter effective for agents to another code
base, and measure the effect.

Students take a project of their own or an open source project, and make it agent-ready: a
``CLAUDE.md``, two or three skills, a safety hook, a test command that runs in one step, and fixes
to the worst inconsistencies. They run the same three tasks before and after.

**What students turn in:**

- A repository (or pull request) with the changes.
- Before-and-after results on three tasks, with scores and time.
- A three-page report, and a six-minute presentation.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Instructions
     - 20
     - Concise ``CLAUDE.md`` and focused skills.
     - Long, generic text.
   * - Code base changes
     - 20
     - One-step tests, consistent patterns.
     - Instructions only.
   * - Safety
     - 15
     - A working hook for a real risk.
     - None.
   * - Experiment
     - 25
     - Controlled before and after.
     - Anecdotes.
   * - Report and presentation
     - 20
     - Honest about what helped and what did not.
     - One-sided.

Recommended Texts
-----------------

- **Required:** :doc:`/smarter-framework/developer-reference/agentic-development`, in week 1.
- **Required:** Gene Kim and Steve Yegge, *Vibe Coding* (IT Revolution, 2025), across weeks 1 to 4.
- **Required:** the `Claude Code documentation <https://code.claude.com/docs>`__ on memory, skills,
  hooks, subagents and permissions, in week 3.
- **Required:** METR, *Measuring the Impact of Early-2025 AI on Experienced Open-Source Developer
  Productivity* (2025), in week 4.
- **Reference:** John Ousterhout, *A Philosophy of Software Design* (2nd edition, Yaknyam Press,
  2021), on the design qualities that help human and agent readers alike.
- **In the repository:** `CLAUDE.md <https://github.com/smarter-sh/smarter/blob/main/CLAUDE.md>`__,
  `skills/README.md <https://github.com/smarter-sh/smarter/blob/main/skills/README.md>`__ and each
  skill's ``SKILL.md``.

Further Study
-------------

.. include:: further-study.txt
