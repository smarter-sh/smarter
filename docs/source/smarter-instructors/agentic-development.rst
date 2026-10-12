Agentic Software Development with Claude Code
=============================================

**Why Smarter.** Smarter's :doc:`ImageSearchPlugin </smarter-resources/plugin/plugin/image-search>`
was built by a coding agent during a live in-class demonstration, and the students watched how it
was done. Claude Code wrote a complete new resource kind: the
`plugin <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/plugin/plugin/image_search.py>`__,
its Pydantic manifest models, broker, migrations, sample manifests, documentation and tests. It
then wrote the `commit
<https://github.com/smarter-sh/smarter/commit/1da6bccc3847f0d06e1b801496cbb838cffb0dab>`__, whose
body explains every change and how it was tested, and the work was merged in
`pull request #775 <https://github.com/smarter-sh/smarter/pull/775>`__ and deployed to
production. Students saw the whole process, and how they could use the same skills to build their
own software.

That demonstration was not a special case. Nearly all new Smarter code is now designed, written
and tested by coding agents such as `Claude Code <https://claude.com/claude-code>`__, and the git
history shows it: since late September 2026, most commits have been authored by Claude, and they
carry most of the lines added in that time. Students can study a real code base that has been
shaped for agents, and the written instructions that make them effective:

- `CLAUDE.md <https://github.com/smarter-sh/smarter/blob/main/CLAUDE.md>`__, the short file that
  every session loads, with eight hard rules, such as never running git write commands and faking
  every cloud call in tests, because the development containers hold live credentials.
- Sixteen `Agent Skills <https://github.com/smarter-sh/smarter/tree/main/skills>`__, each a
  ``SKILL.md`` with its own references and scripts, starting from
  `smarter-development <https://github.com/smarter-sh/smarter/blob/main/skills/smarter-development/SKILL.md>`__,
  which says which narrower skill to load for each kind of work.
- Skills that grew from repeated mistakes, such as the caching rules added in
  `commit eeb7a7a19 <https://github.com/smarter-sh/smarter/commit/eeb7a7a19bccd08c0b341feecf3ca444875a1f48>`__,
  and scripts such as
  `check-docs.sh <https://github.com/smarter-sh/smarter/blob/main/skills/smarter-sphinx-docs/scripts/check-docs.sh>`__
  that replace a 20-minute documentation build with a check that takes seconds.
- A code base built to give an agent feedback: more than five thousand unit tests, the
  `pre-commit hooks <https://github.com/smarter-sh/smarter/blob/main/.pre-commit-config.yaml>`__,
  Pydantic models and `typed aliases <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/lib/typing.py>`__
  instead of ``Any``, and an `in-memory cloud provider
  <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/infrastructure/providers/memory.py>`__
  that makes experiments safe.

The same Agent Skills format is also a Smarter feature: a
:doc:`SkillPlugin </smarter-resources/plugin/plugin/skill>` gives an LLMClient a skill fetched
from GitHub, so students can see skills from both sides, as instructions for a coding agent and as
knowledge for an application they build.

**What the course covers.** How a coding agent works: a model in a loop with tools, context and
permissions; why the code base matters more than the prompt; how to ask, with outcomes, evidence
and acceptance criteria; reviewing agent-written code, including tests that were weakened rather
than bugs that were fixed; ``CLAUDE.md`` and Agent Skills, and writing a skill that measurably
helps; hooks, subagents and agents in CI; safety with live credentials, secrets and prompt
injection; measuring productivity honestly; and authorship, attribution and responsibility.

**Look at.**

- `CLAUDE.md <https://github.com/smarter-sh/smarter/blob/main/CLAUDE.md>`__ and
  `skills/README.md <https://github.com/smarter-sh/smarter/blob/main/skills/README.md>`__.
- The ``SKILL.md`` in each folder of `skills/ <https://github.com/smarter-sh/smarter/tree/main/skills>`__,
  especially ``smarter-infrastructure-safety``, ``smarter-python-testing`` and
  ``smarter-git-commits``.
- The commit history: ``git log --author=Claude`` and the bodies of the commits listed in each
  course plan.

Each course plan lists every file and commit that it uses under *Smarter in the Source Code*.

**Read.** :doc:`/smarter-framework/developer-reference/agentic-development`,
:doc:`/smarter-framework/developer-reference/devops/test`,
:doc:`/smarter-framework/developer-reference/devops/ci-cd`.

**Exercises.**

- Give an agent a broad, well-bounded task, such as a new field with tests and docs, and review its
  pull request as you would a colleague's. Discuss what it got right, what it got wrong, and why.
- Give the same task twice, once with the skills and once without them, and compare the results.
- When the agent makes the same mistake twice, write the skill that prevents it.
- Read the ImageSearchPlugin commit, and find in the diff each change that its body describes.
- Discuss responsibility: who is the author of agent-written code, who reviews it, and how to
  recognize a test that was weakened rather than a bug that was fixed.

**Course plans.** Three complete, ready-to-teach plans, each with a schedule, graded assignments
and rubrics, two capstone projects, recommended texts, further study and technical prerequisites.
See :doc:`course-formats` for what the formats have in common.

.. toctree::
   :maxdepth: 1

   Classroom bootcamp: 8 hours <agentic-development/bootcamp>
   Two-week online course: 6 hours <agentic-development/two-week>
   Four-week online course: 12 hours <agentic-development/four-week>

See the :doc:`Smarter Instructor Guide </smarter-instructor>` to install Smarter and set up
a class.
