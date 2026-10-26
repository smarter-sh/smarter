Python Programming with Agentic AI Master Class
===============================================

**Why Smarter.** For its first three and a half years, Smarter was written by one developer, and
released fifteen minor versions, v0.0 to v0.14. Between September 30 and October 17, 2026, with
`Claude Code <https://claude.com/claude-code>`__ designing and writing most of the code, it
released nineteen more, v0.15 to v0.33, and about fifty patch releases: more feature releases in
three weeks than in its whole history before, all of them deployed to production. About 290,000
lines were added in those weeks, some 250,000 of them by the agent, while Python test coverage
rose to about 97%. Few codebases have had a coding agent turned loose on them at this scale with
the history, the commits and the agent's own transcripts all public, so that every claim can be
checked.

The speed is not the lesson. An agent multiplies whatever it finds in a codebase. Where it finds
one canonical way to do each thing, tests that define correct, linters, and written rules, each
change's errors are cancelled by what comes after them, and the codebase *converges*, like a
telescoping series. Where it finds a second way, it copies the nearest example rather than the
best one, each copy becomes the next feature's template, and the codebase *diverges*, like a
geometric series whose ratio is one or more. Smarter has done both. Its hand-rolled caches grew
from four files at v0.14 to nine at v0.19, carrying the same bugs into each new plugin, until
`commit eeb7a7a19
<https://github.com/smarter-sh/smarter/commit/eeb7a7a19bccd08c0b341feecf3ca444875a1f48>`__ fixed
every copy in one change and wrote the rule where the agent reads first. A DNS change that ran
on every deployment invented the host data it lacked and took production offline for twenty
minutes. The `fix
<https://github.com/smarter-sh/smarter/commit/eb6995baff0d9e91800edf831d93e8338dbc44e7>`__ was
small; what lasted was a skill that keeps every cloud call out of the tests. The
three-part *Converge or Diverge* series on `blog.smarter.sh <https://blog.smarter.sh/>`__
measures all of this, down to what the agent reads in each session, and this course is built on
it.

**The learning objective.** Students leave able to make their own large software project
converge under an AI coding agent, and to prove that it does. Each student brings *the student's
project*, a large Python codebase of their own, and works on it in every lab, with Smarter as the
case study read in every lecture. By the end of the course each student has a *convergence kit*
of Python scripts and tests, built in the labs, that measures the project's history, finds a
second way to do things, reports what the agent actually reads, and fails the build when a
copy comes back.

**What the course covers.** Eighteen one-hour modules, each a 30-minute lecture and a 30-minute
lab, in six themes:

- **Converge or diverge.** Smarter's eighteen days in October, measured; the telescoping and
  geometric series, and the one question that sets the ratio; and measuring a codebase from its
  history.
- **The foundation.** The subsystems a human should design by hand, so that the agent writes
  only the difference; one way to do each thing, as base classes and patterns to copy; and types
  and contracts, tested from the outside.
- **Feedback.** Tests as the definition of correct, and the coverage campaign that found well
  over a hundred bugs; linters that cancel mistakes mechanically; and an environment that the
  agent starts and tests by itself.
- **Guidance.** What the agent actually reads, from its transcripts; ``CLAUDE.md`` and Agent
  Skills; and docstrings, ADRs and commit bodies written for the next agent.
- **The antipattern.** A second way to do things; detecting divergence across the codebase and
  across release tags; and the four-step fix, with a mechanical guard.
- **The human in the loop.** Irreversible steps and guardrails in the environment; prompts as
  units of work, review and honest numbers; and keeping the agent's sources from decaying.

**Look at.**

- `CLAUDE.md <https://github.com/smarter-sh/smarter/blob/main/CLAUDE.md>`__ and the 24 Agent
  Skills in `skills/ <https://github.com/smarter-sh/smarter/tree/main/skills>`__, most of them
  written by the agent after the work, with the traps it hit.
- `cache_results/decorators.py <https://github.com/smarter-sh/cache-results/blob/main/src/cache_results/decorators.py>`__,
  the canonical helper at the center of the course's case study, and
  `lib/manifest/broker/abstract_broker_class.py <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/lib/manifest/broker/abstract_broker_class.py>`__,
  the pattern every resource kind copies.
- `.pre-commit-config.yaml <https://github.com/smarter-sh/smarter/blob/main/.pre-commit-config.yaml>`__
  and `lib/unittest/base_classes.py <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/lib/unittest/base_classes.py>`__,
  the feedback behind more than five thousand Python unit tests.
- The commit history since late September 2026: ``git log --author=Claude``, and the bodies of
  the commits listed in each course plan.

Each course plan lists every file and commit that it uses, module by module, under *The Modules
in the Source Code*.

**Read.** `Part 1: Maintaining Long-Term Code Quality With Agentic AI
<https://blog.smarter.sh/2026/10/10/claude-code-large-django-codebase/>`__, `Part 2: The
Antipattern That Makes a Codebase Diverge
<https://blog.smarter.sh/2026/10/11/blog-prologue-geometric-series/>`__, `Part 3: What Claude
Code Actually Reads <https://blog.smarter.sh/2026/10/17/claude-code-data-sources/>`__,
:doc:`/smarter-framework/developer-reference/agentic-development`,
:doc:`/smarter-framework/developer-reference/devops/test`, :doc:`ADR 024 </adr/024-broker-model>`,
:doc:`ADR 027 </adr/027-annotations>`.

**Exercises.**

- Count Smarter's commits, releases and lines by author and by week, and decide which measure of
  its productivity is honest.
- Count the files that call ``cache.get()`` or ``cache.set()`` directly at every release tag
  from v0.14 to today, and decide which of today's are exceptions and which are copies.
- Classify your own Claude Code transcripts, and rank what the agent read by reach.
- Write a guard test with Python's ``ast`` module that fails when a primitive is used outside
  its helper's home, and watch it fail on a planted copy.
- Read the DNS outage's fix and the skill it led to, and list your own project's irreversible
  steps and how a test fakes each one.

**Course plans.** Two complete, ready-to-teach plans of 18 hours each, with a schedule, graded
assignments and rubrics, two capstone projects, recommended texts, further study and technical
prerequisites. This course is longer than the micro courses in this guide, and has formats of its
own, described in each plan. The grading scale and the course policies are those of
:doc:`/smarter-instructors/example-courses/micro-courses/course-formats`. Students new to coding
agents can start with
:doc:`/smarter-instructors/example-courses/micro-courses/agentic-development`, and students who
want to go deeper into the Django that Smarter is built on can continue with the
:doc:`/smarter-instructors/example-courses/master-classes/django-master-class`.

.. toctree::
   :maxdepth: 1

   Three-day classroom course: 18 hours <python-agentic-ai/three-day>
   Six-week online course: 18 hours <python-agentic-ai/six-week>

See the :doc:`Smarter Instructor Guide </smarter-instructor>` to install Smarter and set up
a class.
