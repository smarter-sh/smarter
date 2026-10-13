AI Governance and Responsible AI: Two-Week Online Course
========================================================

A two-week online course that turns AI governance from principles into practice. Students write an
AI policy, then enforce as much of it as they can with guardrails, budgets and access controls, and
audit the results. In Smarter, every control is a short YAML manifest that a non-programmer can read
and change: `eighteen built-in guardrails
<https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/guardrail/data/guardrails>`__,
from personal data redaction to the escalation of GDPR and CCPA privacy requests to a person; `seven
example budgets
<https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/account/data/example-manifests/budgets>`__,
such as a monthly allowance for each student; and per-account ownership of every resource. Every
intervention is recorded as a `guardrail event
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/guardrail/models/guardrail.py>`__,
and every prompt, tool call and change to a resource is kept, so students can audit what happened,
not what was intended. There are six 30-minute recorded lectures and a 90-minute live session each
week. Week 1 covers risk and control, and week 2 covers money, access and accountability. No
programming is needed. See :doc:`../course-formats` for the format, the grading scale and the course
policies, and :doc:`../ai-governance` for an overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Policy, ethics, law, compliance, risk and business students and professionals.
   * - **Deployment**
     - A shared Smarter instance run by the instructor, with the built-in guardrails and budget
       examples applied, and an account per team.
   * - **Workload**
     - 3 hours of instruction and 4 to 6 hours of assignments each week.
   * - **Cost**
     - Expect less than $5 USD of model charges per student, capped by a per-student
       :doc:`Budget </smarter-resources/smarter-budget>`.

Learning Objectives
-------------------

By the end of the course, students can:

1. Explain the NIST AI RMF, the EU AI Act and ISO/IEC 42001 in plain language, and apply them to a
   real system.
2. Build a risk register for an AI application.
3. Translate a policy into enforceable controls, and identify what software cannot enforce.
4. Demonstrate the difference between instructions and controls.
5. Audit an AI answer from its records, and design spending and access controls.

Technical Prerequisites
-----------------------

- **Required:** a computer with a current web browser and a reliable connection for video calls,
  and experience of using a chat assistant.
- **Required:** reading a YAML file well enough to change a value (`Learn YAML in Y minutes
  <https://learnxinyminutes.com/docs/yaml/>`__).
- **Helpful:** familiarity with a compliance regime such as GDPR, HIPAA or SOC 2.
- **Not needed:** programming.

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
     - **Why AI needs governance.** How a model works, in brief. Real incidents. The NIST AI RMF
       and the risk tiers of the EU AI Act.
   * - 1
     - Lecture 2 (30 min)
     - **Instructions versus controls.** System prompts as requests; guardrails as enforcement.
       Prompt injection demonstrated.
   * - 1
     - Lecture 3 (30 min)
     - **The guardrail toolbox.** Stages, strategies, modes and actions. A tour of the built-in
       guardrails in ``smarter/smarter/apps/guardrail/data/guardrails/``.
   * - 1
     - Live session 1 (90 min)
     - Teams attack an assistant with a rule in its system prompt, then with a guardrail. Debrief
       on what worked. Start Assignment 1.
   * - 2
     - Lecture 4 (30 min)
     - **Money and access.** :doc:`Budgets </smarter-resources/smarter-budget>`,
       :doc:`cost accounting </smarter-platform/cost-accounting>`, accounts, roles, API keys and
       :doc:`Secrets </smarter-resources/smarter-secret>`.
   * - 2
     - Lecture 5 (30 min)
     - **Audit and accountability.** The :doc:`journal </smarter-platform/smarter-journal>` and
       :doc:`Prompt </smarter-resources/smarter-prompt>` records, and what auditors and regulators
       ask for.
   * - 2
     - Lecture 6 (30 min)
     - **What software cannot do.** Fairness, explainability, human oversight, incident response,
       vendor risk, and self-hosted models with :doc:`LLMHost </smarter-resources/smarter-llmhost>`.
   * - 2
     - Live session 2 (90 min)
     - Capstone presentations (about 5 minutes each, with 2 minutes of questions), and a panel
       discussion: which controls appeared in every project, and which in none.

Assignment 1 is due at the end of week 1, Assignment 2 in the middle of week 2, and Assignment 3
and the capstone at the start of Live session 2.

Smarter in the Source Code
--------------------------

.. include:: source-code.txt

Graded Assignments
------------------

Assignment 1: Risk Register and Attack Log
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students write a risk register of at least eight risks for one built-in assistant, and attach the
attack log from Live session 1 with a paragraph explaining why the guardrail held where the system
prompt did not, or did not.

**Turn in:** the register (spreadsheet or document) and the attack log from the journal.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Range and specificity
     - 6
     - Risks span accuracy, privacy, security, fairness, cost and reputation, specific to the
       assistant.
     - Generic or one-dimensional.
   * - Rating and controls
     - 6
     - Consistent ratings with reasons, and a realistic control for each.
     - Ratings or controls missing.
   * - Attack log
     - 4
     - Taken from the journal, with several techniques.
     - Paraphrased, or a single technique.
   * - Explanation
     - 4
     - Explains enforceability correctly.
     - Describes results without explanation.

Assignment 2: Policy to Controls
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students write a one-page acceptable use policy for a fictional organization, implement it with
guardrail and budget manifests, and map each clause to a control or to a non-technical measure.

**Turn in:** the policy, the manifests, evidence of each control working, and the mapping table.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Policy
     - 5
     - Specific clauses an employee could follow.
     - Principles only.
   * - Controls
     - 6
     - Apply cleanly, enforce stated clauses, and are shown working.
     - Unrelated to the policy, or not demonstrated.
   * - Mapping
     - 5
     - Every clause mapped, including to training, contracts or review.
     - Clauses left unmapped.
   * - Proportionality
     - 4
     - Controls do not block legitimate use; false positives tested.
     - Controls that block normal work.

Assignment 3: Audit Trail Reconstruction
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students pick three answers from their team's journal, one of which a guardrail intervened in, and
reconstruct for each the user, the application, the model, the tools called, the guardrail checks
and the cost. They finish with a page on what is missing for a regulator.

**Turn in:** three reconstructions and a one-page gap analysis.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Accuracy
     - 8
     - Every element correctly identified from the records.
     - Elements guessed or missing.
   * - Guardrail case
     - 4
     - Explains what triggered the intervention and what the user saw.
     - Notes the intervention without explaining it.
   * - Gap analysis
     - 6
     - Names specific missing information, and why a regulator would want it.
     - Generic statements about transparency.
   * - Privacy awareness
     - 2
     - Notes the privacy risk of the audit trail itself.
     - Not mentioned.

Capstone Projects
-----------------

Students choose one, and present it in Live session 2.

Capstone A: An AI Governance Program
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Design a governance program that combines policy, technical controls and
human oversight, mapped to a recognized framework.

Students choose an organization in a regulated sector and an AI assistant it plans to deploy,
write its governance program, implement the controls in Smarter, and map everything to the NIST AI
RMF and, where relevant, the EU AI Act.

**What students turn in:**

- A four-page governance document: scope, roles, policy, risk register, oversight, monitoring and
  incident response.
- The guardrail and budget manifests, with evidence of each control working.
- A mapping table to the AI RMF functions and categories.
- A five-minute presentation to a "board" (the class).

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Sector fit
     - 20
     - Reflects the sector's real risks and regulations.
     - Generic.
   * - Governance design
     - 20
     - Clear roles, decisions, escalation and review cycles.
     - No owners or review process.
   * - Technical controls
     - 25
     - Working, demonstrated, and tied to the policy.
     - Not demonstrated, or unrelated.
   * - Framework mapping
     - 20
     - Accurate, with gaps acknowledged.
     - Superficial.
   * - Presentation
     - 15
     - Persuasive to a non-technical board, on time.
     - Technical detail without decisions.

Capstone B: A Regulatory Readiness Assessment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Assess an AI system against a specific regulation, and build the evidence
that an auditor would request.

Students take one built-in assistant, assume a deployment that falls under a named regime (for
example, the EU AI Act's transparency obligations, or a sector rule on financial advice), and assess
the system against it. They gather evidence from Smarter, close the gaps that they can, and list
the rest.

**What students turn in:**

- A readiness assessment: each requirement, its status, the evidence, and the gap.
- An evidence pack: manifests, journal extracts and screenshots.
- A remediation plan with owners and dates for the gaps that remain.
- A five-minute presentation.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Regulatory accuracy
     - 25
     - Requirements correctly identified and interpreted.
     - Requirements misread or missing.
   * - Evidence
     - 25
     - Every status claim backed by evidence from Smarter.
     - Claims without evidence.
   * - Gap closure
     - 20
     - Gaps closed with working controls where software can close them.
     - No gaps closed.
   * - Remediation plan
     - 15
     - Realistic owners, dates and priorities.
     - A list of wishes.
   * - Presentation
     - 15
     - Clear and on time.
     - Overruns or unclear.

Recommended Texts
-----------------

- **Required:** National Institute of Standards and Technology, `AI Risk Management Framework 1.0
  <https://www.nist.gov/itl/ai-risk-management-framework>`__ (NIST AI 100-1, 2023), in full, in
  week 1.
- **Required:** Arvind Narayanan and Sayash Kapoor, *AI Snake Oil* (Princeton University Press,
  2024). Week 1: chapters 1 to 4. Week 2: chapters 5 to 8.
- **Optional:** Brian Christian, *The Alignment Problem* (W. W. Norton, 2020), for the history of
  fairness and safety research.
- **Smarter documentation:** :doc:`/smarter-resources/smarter-guardrail`,
  :doc:`/smarter-resources/smarter-budget`, :doc:`/smarter-resources/smarter-prompt`,
  :doc:`/smarter-platform/smarter-journal` and :doc:`/smarter-platform/security`.

Further Study
-------------

.. include:: further-study.txt
