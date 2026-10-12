AI Governance and Responsible AI: Classroom Bootcamp
====================================================

An eight-hour classroom bootcamp that turns AI governance from principles into practice. Students
write an AI policy, then enforce as much of it as they can with guardrails, budgets and access
controls, and audit the results in Smarter's journal. No programming is needed. See
:doc:`../course-formats` for the standard bootcamp day, the grading scale and the course policies,
and :doc:`../ai-governance` for an overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Policy, ethics, law, compliance, risk and business students and professionals.
   * - **Deployment**
     - A shared Smarter instance run by the instructor, with the built-in guardrails and budget
       examples applied, and an account per team so that teams can audit their own journal.
   * - **Cost**
     - Expect less than $2 USD of model charges per student, capped by a per-student
       :doc:`Budget </smarter-resources/smarter-budget>`.

Learning Objectives
-------------------

By the end of the bootcamp, students can:

1. Explain the main frameworks for AI governance (NIST AI RMF, the EU AI Act, ISO/IEC 42001) in
   plain language.
2. Translate an AI use policy into enforceable controls, and identify the parts that software
   cannot enforce.
3. Explain the difference between a rule in a system prompt and a rule enforced by a guardrail,
   and demonstrate it.
4. Trace an AI answer back through the guardrails, tools and model that produced it, as an
   auditor would.
5. Design spending controls and access rules for an organization.

Technical Prerequisites
-----------------------

- **Required:** a laptop with a current web browser, and experience of using a chat assistant.
- **Required:** reading a YAML file well enough to change a value (`Learn YAML in Y minutes
  <https://learnxinyminutes.com/docs/yaml/>`__, 15 minutes).
- **Helpful:** familiarity with a compliance regime such as GDPR, HIPAA, SOC 2 or a sector
  regulator's guidance.
- **Not needed:** programming.

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
     - **Lecture 1: Why AI needs governance.** How a language model works, in ten minutes. Real
       incidents: invented citations, leaked data, unauthorized promises, runaway costs. The
       NIST AI RMF functions (govern, map, measure, manage) and the risk tiers of the EU AI Act.
   * - 2
     - 45
     - **Lab 1: Map the risks.** For an assistant chosen from the built-ins (``customer_support``,
       ``data_analyst`` or ``workplace_assistant``), list what could go wrong, who would be harmed,
       and how likely it is. Produces Assignment 1.
   * - 3
     - 45
     - **Lecture 2: Instructions versus controls.** A rule in a system prompt is a request that a
       model may ignore; a :doc:`Guardrail </smarter-resources/smarter-guardrail>` is checked by
       software on every message. Live demonstration of prompt injection against a system prompt,
       then against a guardrail.
   * - 4
     - 45
     - **Lab 2: Try to get around it.** Teams attack an assistant that has a rule only in its
       system prompt, then the same assistant with a guardrail, and record each attempt and
       result. Produces Assignment 2.
   * - 5
     - 45
     - **Lecture 3: The guardrail toolbox.** Input and output stages, strategies (keyword, regular
       expression, detector, moderation, semantic similarity, LLM judge), enforce and monitor
       modes, and actions (block, redact, flag, escalate, transform). A tour
       of the built-in guardrails: personal data, secrets, regulated advice, off-topic, invented
       citations, self-harm.
   * - 6
     - 45
     - **Lecture 4: Money and access.** :doc:`Budgets </smarter-resources/smarter-budget>` per
       user, application and account; :doc:`cost accounting </smarter-platform/cost-accounting>`;
       accounts, roles and API keys; encrypted :doc:`Secrets </smarter-resources/smarter-secret>`.
       Who should be able to do what.
   * - 7
     - 45
     - **Lab 3: From policy to manifest.** Write a one-page acceptable use policy for a fictional
       organization, then implement what you can as guardrail and budget manifests, and mark what
       you cannot. Produces Assignment 3.
   * - 8
     - 45
     - **Lecture 5: Audit and accountability.** The :doc:`journal </smarter-platform/smarter-journal>`
       and :doc:`Prompt </smarter-resources/smarter-prompt>` records: who asked what, which model
       answered, which tools ran and which guardrails intervened. What a regulator, an auditor
       or a court would ask for. Privacy of the audit trail itself.
   * - 9
     - 45
     - **Lab 4: Audit an answer.** Pick one answer from the journal, and reconstruct the chain of
       events that produced it. Ungraded.
   * - 10
     - 45
     - **Lecture 6: What software cannot do.** Bias, fairness and explainability; human oversight;
       accountability; incident response; vendor and model risk. Self-hosted models with
       :doc:`LLMHost </smarter-resources/smarter-llmhost>` when data must not leave the network.
   * - 11
     - 30
     - **Capstone kickoff.** Students choose a capstone and an organization, and outline their
       approach with the instructor's feedback.

Graded Assignments
------------------

Assignment 1: Risk Register
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students produce a risk register for one built-in assistant: at least eight risks, each with the
people affected, likelihood, impact and a proposed control.

**Turn in:** the risk register as a table (spreadsheet or document).

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Range of risks
     - 6
     - Covers accuracy, privacy, security, fairness, cost and reputation.
     - Mostly one kind of risk.
   * - Specificity
     - 5
     - Risks are specific to this assistant's job and users.
     - Generic risks of AI.
   * - Rating
     - 4
     - Likelihood and impact are rated consistently, with reasons.
     - Ratings without reasons.
   * - Controls
     - 5
     - Each control is realistic, and names whether it is technical or organizational.
     - Controls missing or vague ("monitor closely").

Assignment 2: Prompt Rule versus Guardrail
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Teams record at least eight attempts to get around a rule, first enforced only by the system
prompt, then by a guardrail, and explain the difference.

**Turn in:** an attack log with the prompts and results, taken from the journal, and a one-page
explanation.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Attempts
     - 5
     - Eight or more, using several techniques.
     - Repeats of the same attempt.
   * - Evidence
     - 5
     - Taken from the journal, including guardrail interventions.
     - Paraphrased from memory.
   * - Explanation
     - 6
     - Explains why one approach is enforceable and the other is not.
     - Describes results without explaining them.
   * - Limits
     - 4
     - Notes what got past the guardrail, or what it blocked wrongly.
     - Claims the guardrail is perfect.

Assignment 3: Policy to Controls
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students write a one-page acceptable use policy for AI in a fictional organization, and implement
as much of it as possible by adapting built-in guardrail and budget manifests.

**Turn in:** the policy, the manifests, and a table that maps each policy clause to a control or
explains why it cannot be enforced in software.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Policy
     - 5
     - Clear, specific clauses that an employee could follow.
     - Principles without concrete rules.
   * - Controls
     - 6
     - Manifests apply, and each enforces a stated clause.
     - Manifests unrelated to the policy, or fail to apply.
   * - Mapping
     - 5
     - Every clause is mapped to a control or a reason.
     - Clauses left unmapped.
   * - Insight
     - 4
     - Identifies which clauses need people, training or contracts instead.
     - Assumes software can enforce everything.

Capstone Projects
-----------------

Students choose one. Capstones are due one week after the bootcamp.

Capstone A: An AI Governance Program for an Organization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Design a governance program that combines policy, technical controls and
human oversight, mapped to a recognized framework.

Students choose an organization, such as a hospital, a university, a bank or a city council, and
one AI assistant it plans to deploy. They write the policy, implement the controls in Smarter,
and map both to the NIST AI RMF.

**What students turn in:**

- A three-page governance document: scope, roles and responsibilities, the policy, oversight and
  incident response.
- The guardrail and budget manifests, and a short demonstration (screenshots or video) of each
  control working.
- A table mapping each control to an AI RMF function and category.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Fit to the organization
     - 20
     - Controls reflect the sector's real risks and rules.
     - Generic controls that would fit any organization.
   * - Policy and roles
     - 20
     - Clear owners, decisions and escalation paths.
     - No one is responsible for anything in particular.
   * - Technical controls
     - 25
     - Each control works, is shown working, and enforces a stated rule.
     - Controls applied but not demonstrated.
   * - Framework mapping
     - 20
     - Accurate mapping, with gaps acknowledged.
     - Mapping is superficial or wrong.
   * - Writing
     - 15
     - Clear and concise enough for a board to read.
     - Long, vague or jargon-heavy.

Capstone B: An AI Incident Investigation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Investigate an AI failure from the audit trail, find its root causes, and
recommend controls that would prevent it.

The instructor stages an incident on the shared instance, for example an assistant that gave
regulated financial advice or revealed a customer's personal data. Students investigate from the
journal and the manifests, and write an incident report.

**What students turn in:**

- An incident report: summary, timeline, evidence from the journal, root causes, impact and
  recommendations.
- The manifests that implement the recommended controls, with evidence that they stop a repeat.
- A one-page briefing note for a non-technical executive.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Timeline and evidence
     - 25
     - Complete, accurate, and every claim tied to a journal record.
     - Gaps in the timeline, or claims without evidence.
   * - Root cause analysis
     - 25
     - Distinguishes technical, process and human causes.
     - Stops at "the model made a mistake".
   * - Recommendations
     - 20
     - Specific, proportionate, and implemented where possible.
     - Vague, or not implemented.
   * - Verification
     - 15
     - Shows that the new controls stop a repeat.
     - No test of the controls.
   * - Executive briefing
     - 15
     - One page, plain language, clear decisions requested.
     - Technical detail without a summary.

Recommended Texts
-----------------

- **Pre-reading:** National Institute of Standards and Technology, `AI Risk Management Framework
  1.0 <https://www.nist.gov/itl/ai-risk-management-framework>`__ (NIST AI 100-1, 2023), parts 1
  and 2. Free.
- **Reference:** Arvind Narayanan and Sayash Kapoor, *AI Snake Oil* (Princeton University Press,
  2024). A clear-eyed account of what AI can and cannot do.
- **Smarter documentation:** :doc:`/smarter-resources/smarter-guardrail`,
  :doc:`/smarter-resources/smarter-budget`, :doc:`/smarter-resources/smarter-prompt` and
  :doc:`/smarter-platform/security`.

Further Study
-------------

.. include:: further-study.txt
