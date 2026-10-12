Agentic Software Development: Classroom Bootcamp
================================================

An eight-hour classroom bootcamp on developing software with coding agents such as
`Claude Code <https://claude.com/claude-code>`__, taught on a real code base that has been shaped
for agents: Smarter, where nearly all new code is designed, written and tested by agents working
from ``CLAUDE.md`` and the Agent Skills in ``skills/``. Students delegate real tasks, review the
results as they would a colleague's, and write the instructions that make agents effective. See
:doc:`../course-formats` for the standard bootcamp day, the grading scale and the course policies,
and :doc:`../agentic-development` for an overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Software developers who write Python or JavaScript, and want to work effectively and
       responsibly with coding agents.
   * - **Deployment**
     - Each student runs Smarter from source, installed **before** the bootcamp, with a fork on
       GitHub and Claude Code (or another coding agent) installed and signed in.
   * - **Cost**
     - A coding agent subscription or API usage for each student, typically a few dollars for the
       day with API billing, plus small model charges from Smarter's tests.

Learning Objectives
-------------------

By the end of the bootcamp, students can:

1. Explain how a coding agent works: a model in a loop with tools, context, and instructions.
2. Delegate a broad, well-bounded task to an agent, with clear acceptance criteria.
3. Review agent-written code critically, including its tests, and recognize a test that was
   weakened rather than a bug that was fixed.
4. Explain how ``CLAUDE.md`` and Agent Skills shape an agent's work, and write a skill.
5. Discuss authorship, responsibility and security when agents write code.

Technical Prerequisites
-----------------------

- **Required:** Python or JavaScript, well enough to read and review a pull request in either.
- **Required:** Git and GitHub: branches, diffs, pull requests and code review.
- **Required:** the command line, and Docker basics.
- **Required:** Smarter installed from source and running, and a coding agent installed and
  working in the repository, before the bootcamp.
- **Required:** basic generative AI concepts: prompts, context windows and tool calls.
- **Helpful:** experience with automated tests, and with Markdown.

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
     - **Lecture 1: What a coding agent is.** A model in a loop: reading files, running commands,
       editing code, and checking its work. Context windows, tools and permissions. Why the code
       base matters more than the prompt.
   * - 2
     - 45
     - **Lab 1: Read the instructions.** Read ``CLAUDE.md``, ``skills/README.md`` and two
       ``SKILL.md`` files, and list what they tell an agent to do and never do, and why. Produces
       Assignment 1.
   * - 3
     - 45
     - **Lecture 2: How you ask.** Outcomes, not steps; giving the evidence for narrow problems;
       saying what "done" means; and the pattern-first workflow.
       :doc:`/smarter-framework/developer-reference/agentic-development`.
   * - 4
     - 45
     - **Lab 2: Delegate a task.** Ask the agent for a broad, bounded change, such as a new
       optional field on a resource with tests and docs, and let it work. Produces Assignment 2.
   * - 5
     - 45
     - **Lecture 3: Reviewing agent code.** Reading a diff you did not write; checking tests
       against the behavior; weakened assertions, skipped tests, swallowed errors and invented
       APIs; running the tests and hooks yourself.
   * - 6
     - 45
     - **Lecture 4: Skills.** How Agent Skills work, when they load, what belongs in a skill and
       what belongs in the code, and how Smarter's skills grew from repeated mistakes.
   * - 7
     - 45
     - **Lab 3: With and without.** Give the same task to the agent twice, once with the skills
       and once with them removed from a scratch branch, and compare the results. Produces
       Assignment 3.
   * - 8
     - 45
     - **Lecture 5: Safety.** Permissions, sandboxing, live credentials (and why Smarter's
       instructions forbid touching real infrastructure from tests), secrets in prompts, prompt
       injection through files, and never letting an agent push.
   * - 9
     - 45
     - **Lab 4: Write a skill.** Choose a mistake the agent made today, and draft a skill that
       prevents it. Ungraded.
   * - 10
     - 45
     - **Lecture 6: Responsibility.** Who is the author of agent-written code, who reviews it,
       attribution in commits, licenses, and how the developer's job is changing.
   * - 11
     - 30
     - **Capstone kickoff.** Students choose a capstone and write its acceptance criteria.

Graded Assignments
------------------

Assignment 1: Instruction Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students summarize what ``CLAUDE.md`` and two skills instruct an agent to do, and explain the
reason behind three of the rules, finding the code or incident that motivated each where they can.

**Turn in:** a one-page analysis.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Accuracy
     - 6
     - Rules summarized correctly.
     - Misread.
   * - Reasons
     - 8
     - Three rules explained, with evidence from the code or history.
     - Guessed reasons.
   * - Insight
     - 4
     - Notes which rules would help a human newcomer too.
     - None.
   * - Clarity
     - 2
     - Concise.
     - Rambling.

Assignment 2: Delegation and Review
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students submit the agent's pull request (against their own fork) with their own review: what it
got right, what it got wrong, what they changed, and the evidence that the tests and hooks pass.

**Turn in:** the pull request, the request they gave the agent, and a review of at least five
comments.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Request quality
     - 4
     - Outcome and acceptance criteria stated.
     - Step-by-step or vague.
   * - Review depth
     - 8
     - Substantive comments on correctness, tests and fit with the code base.
     - Style comments only, or "looks good".
   * - Verification
     - 5
     - Tests and hooks run by the student, results shown.
     - Took the agent's word for it.
   * - Honesty
     - 3
     - Problems reported, not hidden.
     - Problems omitted.

Assignment 3: With and Without Skills
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students compare the agent's work on the same task with and without the skills, on correctness,
fit with existing patterns, tests and time.

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
     - Same task, same model, fresh context each time.
     - Different tasks or carried-over context.
   * - Criteria
     - 6
     - Correctness, patterns, tests and time all compared.
     - One criterion.
   * - Analysis
     - 6
     - Links differences to specific skill content.
     - Describes differences only.
   * - Conclusion
     - 3
     - Honest, including if the skills made little difference.
     - Assumes the answer.

Capstone Projects
-----------------

Students choose one. Capstones are due one week after the bootcamp.

Capstone A: A Feature Built with an Agent
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Deliver a real feature with a coding agent while remaining its accountable
author: specifying, reviewing, verifying and explaining every line.

Students use an agent to build a feature in their fork, for example a new management command, a
new field with a console column, or a docs page with examples. They keep a log of the session, and
must be able to explain every line in the final diff.

**What students turn in:**

- A pull request against their fork with code, tests and documentation, passing tests and hooks.
- The request and acceptance criteria they gave the agent, and a session log with their
  interventions and why.
- A one-page reflection: what the agent did well, what it got wrong, and what they would do
  differently.
- A ten-minute oral check with the instructor on any part of the diff.

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
     - Correct, tested, documented, hooks pass.
     - Partly working.
   * - Specification
     - 15
     - Clear outcome and acceptance criteria.
     - Vague request.
   * - Review and intervention
     - 20
     - Log shows problems caught and corrected.
     - Accepted everything.
   * - Understanding
     - 30
     - Explains any line in the oral check.
     - Cannot explain key parts.
   * - Reflection
     - 15
     - Specific and honest.
     - Generic.

Capstone B: A Skill That Works
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Improve an agent's results by writing instructions, and prove the
improvement with an experiment.

Students identify a class of mistake that agents make in Smarter (or in a project of their own),
write a skill that prevents it, and run the same three tasks with and without the skill.

**What students turn in:**

- The skill (``SKILL.md`` and any references or scripts), following ``skills/README.md``.
- The three tasks, both sets of results, and a scoring table.
- A two-page report on the effect and on what made the skill work, or not.

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
     - A real, recurring mistake, with examples.
     - Hypothetical.
   * - Skill quality
     - 25
     - Concise, specific, with a clear trigger description; follows the repository's format.
     - Long and generic.
   * - Experiment
     - 25
     - Three tasks, fresh contexts, same model.
     - One task, or uncontrolled.
   * - Results
     - 20
     - Scored honestly.
     - Cherry-picked.
   * - Report
     - 15
     - Explains why it worked or did not.
     - Results only.

Recommended Texts
-----------------

- **Pre-reading:** :doc:`/smarter-framework/developer-reference/agentic-development`, and
  Anthropic's `Building effective agents
  <https://www.anthropic.com/engineering/building-effective-agents>`__.
- **Reference:** Gene Kim and Steve Yegge, *Vibe Coding* (IT Revolution, 2025), on building
  production software with agents.
- **In the repository:** ``CLAUDE.md``, ``skills/README.md`` and each skill's ``SKILL.md``.

Further Study
-------------

.. include:: further-study.txt
