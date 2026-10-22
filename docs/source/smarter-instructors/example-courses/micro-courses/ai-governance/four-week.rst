AI Governance and Responsible AI: Four-Week Online Course
=========================================================

A four-week online course that turns AI governance from principles into practice. Students build a
risk register, enforce policy with guardrails, budgets and access controls, measure those controls,
and audit the results. In Smarter, every control is a short YAML manifest that a non-programmer can
read and change: `eighteen built-in guardrails
<https://github.com/smarter-sh/example-manifests/tree/main/guardrails>`__,
from personal data redaction to the escalation of GDPR and CCPA privacy requests to a person; `seven
example budgets
<https://github.com/smarter-sh/example-manifests/tree/main/budgets>`__,
such as a monthly allowance for each student; and per-account ownership of every resource. Every
intervention is recorded as a `guardrail event
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/guardrail/models/guardrail.py>`__,
and every prompt, tool call and change to a resource is kept, so students can audit what happened,
not what was intended. There are twelve 30-minute recorded lectures and a 90-minute live session
each week. Week 1 covers frameworks and risk, week 2 technical controls, week 3 money, access and
accountability, and week 4 the parts of governance that software cannot do. No programming is
needed. See :doc:`../course-formats` for the format, the grading scale and the course policies, and
:doc:`../ai-governance` for an overview of the subject.

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
     - Expect less than $8 USD of model charges per student, capped by a per-student
       :doc:`Budget </smarter-resources/smarter-budget>`.

Learning Objectives
-------------------

By the end of the course, students can:

1. Explain and compare the NIST AI RMF, the EU AI Act, ISO/IEC 42001 and the OECD AI Principles.
2. Build and maintain a risk register for an AI application.
3. Translate a policy into enforceable controls, measure their false positives and false
   negatives, and identify what software cannot enforce.
4. Design spending, access and data protection controls for an organization.
5. Audit an AI answer from its records, and investigate an incident.
6. Write a governance program that a board could adopt.

Technical Prerequisites
-----------------------

- **Required:** a computer with a current web browser and a reliable connection for video calls,
  and experience of using a chat assistant.
- **Required:** reading a YAML file well enough to change a value (`Learn YAML in Y minutes
  <https://learnxinyminutes.com/docs/yaml/>`__).
- **Required by week 2:** a GitHub account, for submitting manifests.
- **Helpful:** familiarity with a compliance regime such as GDPR, HIPAA or SOC 2, and a
  spreadsheet program.
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
     - Lecture 1
     - **How AI systems fail.** How a model works, in brief, and a catalog of real incidents from
       the AI Incident Database.
   * - 1
     - Lecture 2
     - **Frameworks.** The NIST AI RMF, ISO/IEC 42001 and the OECD AI Principles.
   * - 1
     - Lecture 3
     - **Regulation.** The EU AI Act's risk tiers and obligations, and sector rules in finance,
       health and employment.
   * - 1
     - Live session 1
     - A tour of a governed application (``customer_support``) and its controls. Teams start a
       risk register. Start Assignment 1.
   * - 2
     - Lecture 4
     - **Instructions versus controls.** Prompt injection and jailbreaks, demonstrated against a
       system prompt and against a :doc:`Guardrail </smarter-resources/smarter-guardrail>`.
   * - 2
     - Lecture 5
     - **The guardrail toolbox.** Stages, strategies, modes and actions, and the built-in
       guardrails.
   * - 2
     - Lecture 6
     - **Measuring controls.** False positives and false negatives, monitor mode before enforce
       mode (a monitored guardrail records what it would have done), and choosing thresholds
       from the severity and confidence of guardrail events.
   * - 2
     - Live session 2
     - Review of Assignment 1. Red team exercise against a classmate's assistant. Start
       Assignment 2.
   * - 3
     - Lecture 7
     - **Money.** :doc:`Budgets </smarter-resources/smarter-budget>` and
       :doc:`cost accounting </smarter-platform/cost-accounting>` as controls.
   * - 3
     - Lecture 8
     - **Access and data.** Accounts, roles, API keys, :doc:`Secrets
       </smarter-resources/smarter-secret>`, personal data, and data residency with self-hosted
       models through :doc:`LLMHost </smarter-resources/smarter-llmhost>`.
   * - 3
     - Lecture 9
     - **Audit.** The :doc:`journal </smarter-platform/smarter-journal>` and
       :doc:`Prompt </smarter-resources/smarter-prompt>` records, retention, and the privacy of the
       audit trail.
   * - 3
     - Live session 3
     - Review of Assignment 2. An audit exercise on the journal. Capstone proposals discussed.
       Start Assignment 3.
   * - 4
     - Lecture 10
     - **Fairness and explainability.** Bias in models and data, what can be measured, and what
       cannot be explained.
   * - 4
     - Lecture 11
     - **Human oversight and incidents.** Human review, escalation, incident response, and
       learning from failures.
   * - 4
     - Lecture 12
     - **Vendors and models.** Model provider contracts, model changes, open versus closed models,
       and concentration risk.
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

Assignment 1: Framework Comparison and Risk Register
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students compare two frameworks in a one-page table, then use one of them to build a risk register
of at least ten risks for a built-in assistant.

**Turn in:** the comparison table and the risk register.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Framework comparison
     - 5
     - Accurate, with the purpose and scope of each.
     - Inaccurate, or a list of headings.
   * - Risk range and specificity
     - 6
     - Risks span several categories, specific to the assistant.
     - Generic.
   * - Rating and controls
     - 5
     - Consistent ratings with reasons, realistic controls.
     - Missing or vague.
   * - Framework use
     - 4
     - Register structured by the chosen framework.
     - Framework named but not used.

Assignment 2: Control Effectiveness Study
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students choose one risk from their register, configure a guardrail for it, and test it with
twenty prompts that should trigger it and twenty that should not, in monitor mode and then in
enforce mode. They report the false positive and false negative rates, and adjust the guardrail
once.

**Turn in:** the manifest before and after adjustment, the forty prompts with results, and a
one-page analysis.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Test set
     - 5
     - Realistic positives and negatives, including borderline cases.
     - Obvious cases only.
   * - Measurement
     - 6
     - Rates calculated correctly from journal records.
     - Rates estimated or missing.
   * - Adjustment
     - 5
     - Targets observed errors, with the effect measured.
     - Changed without remeasuring.
   * - Analysis
     - 4
     - Discusses the trade-off between blocking too much and too little.
     - Reports numbers without interpretation.

Assignment 3: Budget and Access Design
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students design spending and access controls for a fictional department of fifty people with
three AI applications: who gets which application, how much each user and application may spend,
who is warned, and what happens at the limit. They implement the budgets in Smarter.

**Turn in:** a two-page design, the budget manifests, and evidence of a limit being reached.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Design
     - 6
     - Limits based on expected use, with reasons.
     - Arbitrary limits.
   * - Implementation
     - 6
     - Manifests apply and enforce the design.
     - Manifests do not match the design.
   * - Evidence
     - 4
     - Shows a limit reached and the user's experience.
     - Not demonstrated.
   * - Access and secrets
     - 4
     - Addresses API keys, roles and provider credentials.
     - Budget only.

Assignment 4: Bias Probe
~~~~~~~~~~~~~~~~~~~~~~~~

Students design a small experiment to look for bias in an assistant's answers, for example by
asking for the same job reference letter with only the candidate's name changed, run it on two
models, and report what they find and what a governance program should do about it.

**Turn in:** the experimental design, the prompts and answers, and a two-page report.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Design
     - 6
     - Changes one attribute at a time, with enough repetitions.
     - Changes several things at once.
   * - Execution
     - 4
     - Complete results on two models.
     - Partial results.
   * - Interpretation
     - 6
     - Careful about what the data does and does not show.
     - Overclaims from small samples.
   * - Governance response
     - 4
     - Proposes proportionate controls and oversight.
     - No response proposed.

Capstone Projects
-----------------

Students choose one, propose it before Live session 3, and present it in Live session 4.

Capstone A: An AI Governance Program
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Design a complete governance program for a real or realistic organization,
combining policy, technical controls, measurement and human oversight, mapped to recognized
frameworks.

**What students turn in:**

- A six-page governance program: scope, roles, policy, risk register, controls, measurement of
  their effectiveness, oversight, incident response and review cycle.
- The guardrail and budget manifests, with effectiveness measurements for at least two controls.
- A mapping to the NIST AI RMF and to ISO/IEC 42001 or the EU AI Act.
- A six-minute presentation to a "board" (the class), asking for a decision.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Organization fit
     - 15
     - Reflects the sector's real risks and regulations.
     - Generic.
   * - Governance design
     - 20
     - Clear roles, decisions, escalation and review.
     - No owners or reviews.
   * - Controls and measurement
     - 25
     - Controls work, and their effectiveness is measured.
     - Controls applied without measurement.
   * - Framework mapping
     - 20
     - Accurate across two frameworks, gaps acknowledged.
     - Superficial.
   * - Presentation
     - 20
     - Persuasive, on time, with a clear decision requested.
     - No decision requested.

Capstone B: An AI Incident Investigation and Policy Response
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Investigate an AI failure from the audit trail, find its technical,
process and human causes, and change policy and controls so that it does not happen again.

The instructor stages two related incidents on the shared instance. Students investigate from the
journal and manifests, write an incident report, revise the organization's policy, and implement
and test new controls.

**What students turn in:**

- An incident report: summary, timeline, evidence, root causes, impact and recommendations.
- The revised policy, with changes marked.
- The new manifests, and tests that show they stop a repeat without blocking normal use.
- A one-page executive briefing, and a six-minute presentation.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Investigation
     - 25
     - Complete timeline; every claim tied to a record; both incidents connected.
     - Gaps, or incidents treated separately.
   * - Root causes
     - 20
     - Technical, process and human causes distinguished.
     - "The model made a mistake".
   * - Policy revision
     - 15
     - Targeted, proportionate changes.
     - A rewrite unrelated to the causes.
   * - Controls and tests
     - 20
     - Stop a repeat, with false positives checked.
     - Not tested.
   * - Briefing and presentation
     - 20
     - Plain language, clear decisions requested, on time.
     - Technical detail without a summary.

Recommended Texts
-----------------

- **Required:** National Institute of Standards and Technology, `AI Risk Management Framework 1.0
  <https://www.nist.gov/itl/ai-risk-management-framework>`__ (NIST AI 100-1, 2023), and its
  Generative AI Profile (NIST AI 600-1, 2024), in week 1.
- **Required:** Arvind Narayanan and Sayash Kapoor, *AI Snake Oil* (Princeton University Press,
  2024), across weeks 1 and 2.
- **Required:** Qinghua Lu, Liming Zhu, Jon Whittle and Xiwei Xu, *Responsible AI: Best Practices
  for Creating Trustworthy AI Systems* (Addison-Wesley, 2023), selected chapters on governance
  patterns in weeks 2 and 3.
- **Week 4:** Cathy O'Neil, *Weapons of Math Destruction* (Crown, 2016), and Joy Buolamwini,
  *Unmasking AI* (Random House, 2023), one chosen by each student, for the fairness discussion.
- **Optional:** Brian Christian, *The Alignment Problem* (W. W. Norton, 2020).
- **Smarter documentation:** :doc:`/smarter-resources/smarter-guardrail`,
  :doc:`/smarter-resources/smarter-budget`, :doc:`/smarter-resources/smarter-prompt`,
  :doc:`/smarter-platform/smarter-journal`, :doc:`/smarter-platform/security` and
  :doc:`/smarter-resources/smarter-llmhost`.

Further Study
-------------

.. include:: further-study.txt
