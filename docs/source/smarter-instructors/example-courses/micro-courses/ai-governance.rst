AI Governance and Responsible AI
================================

**Why Smarter.** Most discussion of AI governance stays at the level of principles, because
students have no system on which to try them. In Smarter, governance is concrete, and every
control is a short YAML manifest that a policy, ethics, law or business student can read, change
and apply without writing any code:

- **Guardrails that inspect every message.** Smarter ships with
  `eighteen built-in guardrails <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/guardrail/data/guardrails>`__,
  for personal data, secrets, prompt injection, jailbreaks, moderation, self-harm, off-topic
  requests, regulated advice, invented citations and privacy requests. Each one states its stage
  (the user's message, the model's reply, or both), its strategy (keywords, regular expressions,
  detectors, semantic similarity, a moderation model or an LLM judge), its action (log, flag,
  redact, transform, block, or escalate to a person) and its mode: enforce, or monitor, which
  records what it would have done. The `pipeline
  <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/guardrail/services/pipeline.py>`__
  that runs them is software, not an instruction that a model may ignore.
- **Budgets that stop spending.** A :doc:`Budget </smarter-resources/smarter-budget>` limits
  dollars or tokens per hour, day, week or month, for an account, a user, an application, a
  provider or a self-hosted model, and blocks or warns at the limit. The
  `seven example budgets <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/account/data/example-manifests/budgets>`__
  include a monthly allowance for each student and a daily limit on one provider.
- **Access that follows ownership.** Every resource belongs to an
  :doc:`account and a user </smarter-platform/account-management>`, and every query is
  `filtered by owner <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/account/models/metadata_with_ownership.py>`__.
  Provider keys and passwords are encrypted :doc:`Secrets </smarter-resources/smarter-secret>`,
  never shown to users or models.
- **An audit trail that traces each answer.** Every guardrail intervention is a
  `guardrail event <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/guardrail/models/guardrail.py>`__
  with its severity, confidence, rationale and review status; every prompt, tool call and plugin
  selection is recorded with the person and account that asked; and the
  :doc:`journal </smarter-platform/smarter-journal>` records every change to a resource.
- **Data that stays in the network.** With :doc:`LLMHost </smarter-resources/smarter-llmhost>`,
  open models run on the organization's own cluster, so a class can compare the governance of a
  commercial model with that of a self-hosted one.

Students can see how AI is controlled in practice, change those controls themselves, and find the
parts of a policy that no software can enforce.

**What the course covers.** How AI systems fail, from invented citations to runaway costs; the
NIST AI Risk Management Framework, ISO/IEC 42001, the OECD AI Principles and the EU AI Act;
mapping risks for a real application; why a rule in a system prompt is a request while a guardrail
is a control; the guardrail toolbox, and measuring controls by their false positives and false
negatives; budgets and cost accounting as controls; access, secrets, personal data and data
residency; audit, retention and the privacy of the audit trail itself; fairness and
explainability; human oversight and incident response; and vendor and model risk.

**Look at.**

- `guardrail/data/guardrails/ <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/guardrail/data/guardrails>`__,
  the built-in guardrails.
- `account/data/example-manifests/budgets/ <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/account/data/example-manifests/budgets>`__,
  the example budgets.
- The `customer_support
  <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/llmclient/data/llm-clients/llmclient-customer-support.yaml>`__
  LLMClient, a governed application with four input guardrails.

Each course plan lists every manifest and file that it uses under *Smarter in the Source Code*.

**Read.** :doc:`/smarter-resources/smarter-guardrail`, :doc:`/smarter-resources/smarter-budget`,
:doc:`/smarter-resources/smarter-prompt`, :doc:`/smarter-platform/cost-accounting`,
:doc:`/smarter-platform/smarter-journal`, :doc:`/smarter-platform/security`.

**Exercises.**

- Write an acceptable use policy for AI in a fictional organization, then implement as much of it
  as possible as guardrail and budget manifests. Discuss which parts of the policy cannot be
  enforced by software, and why.
- Compare a rule written in a system prompt with the same rule enforced by a guardrail. Try to get
  around each one, and explain the difference.
- Run a new guardrail in monitor mode, read the events it records, and decide whether it is ready
  to enforce.
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
