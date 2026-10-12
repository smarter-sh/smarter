AI Governance and Responsible AI
================================

**Why Smarter.** Most discussion of AI governance stays at the level of principles. In Smarter,
governance is concrete: guardrails that inspect every message, budgets that stop spending,
role-based access to every resource, and an audit trail that traces each answer back to the
person and account that asked for it. Policy, ethics, law and business students can see how AI is
controlled in practice, and change those controls themselves, without writing any code.

**Look at.** The built-in guardrails in ``smarter/smarter/apps/guardrail/data/guardrails/``, and
the budget examples in ``smarter/smarter/apps/account/data/example-manifests/budgets/``.

**Read.** :doc:`/smarter-resources/smarter-guardrail`, :doc:`/smarter-resources/smarter-budget`,
:doc:`/smarter-resources/smarter-prompt`, :doc:`/smarter-platform/security`.

**Exercises.**

- Write an acceptable use policy for AI in a fictional organization, then implement as much of it
  as possible as guardrail and budget manifests. Discuss which parts of the policy cannot be
  enforced by software, and why.
- Compare a rule written in a system prompt with the same rule enforced by a guardrail. Try to get
  around each one, and explain the difference.
- Pick one answer from the journal and trace it back through the guardrail checks, tool calls and
  model that produced it. Discuss what an auditor or a regulator would want to see.

**Course plans.** Three complete, ready-to-teach plans, each with a schedule, graded assignments
and rubrics, two capstone projects, recommended texts, further study and technical prerequisites.
See :doc:`course-formats` for what the formats have in common.

.. toctree::
   :maxdepth: 1

   Classroom bootcamp: 8 hours <ai-governance/bootcamp>
   Two-week online course: 6 hours <ai-governance/two-week>
   Four-week online course: 12 hours <ai-governance/four-week>

See the :doc:`Smarter Instructor Guide </smarter-instructor>` to install Smarter and set up
a class.
