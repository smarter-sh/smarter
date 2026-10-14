Writing Secure Software: Classroom Bootcamp
===========================================

An eight-hour classroom bootcamp on securing web applications and AI systems, using Smarter as the
case study. Students attack an AI application with prompt injection, defend it with deterministic
controls, map its defenses to the OWASP Top 10 lists, and study how it handles secrets and outbound
requests. Smarter assumes that a model will eventually try to do something it should not, and
defends with deterministic controls rather than instructions: `guardrails
<https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/guardrail/data/guardrails>`__
on both the prompt and the reply, a single `hardened function
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/llmtool/plugin/safe_http.py>`__
for every outbound request to a user-supplied URL, credentials kept in encrypted `Secrets
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/secret/models.py>`__ that the
model never sees, and parameterized queries and tool allow lists for least privilege. Every defense
is in code that students can read and test. See :doc:`../course-formats` for the standard bootcamp
day, the grading scale and the course policies, and :doc:`../secure-software` for an overview of the
subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Developers and security students who want to understand both classic web security and the
       new attacks on AI systems.
   * - **Deployment**
     - A shared Smarter instance run by the instructor for the attack and defense labs, with an
       account per team. Students who want to read and run the code clone the repository.
   * - **Cost**
     - Expect less than $3 USD of model charges per student, capped by a per-student
       :doc:`Budget </smarter-resources/smarter-budget>`.

.. warning::

   Students attack only the class's own Smarter instance, within the rules set by the instructor.
   Any real vulnerability found in Smarter is reported privately, as described in the project's
   ``SECURITY.md``, never in a public issue or an assignment.

Learning Objectives
-------------------

By the end of the bootcamp, students can:

1. Explain the OWASP Top 10 and the OWASP Top 10 for LLM Applications, with an example of each
   category.
2. Carry out and explain direct and indirect prompt injection against an AI application.
3. Explain why deterministic controls (guardrails, allow lists, least privilege) are stronger than
   instructions to a model.
4. Explain how an application keeps credentials out of prompts, code and logs.
5. Explain server-side request forgery, and how an application that fetches URLs defends against
   it.

Technical Prerequisites
-----------------------

- **Required:** structured programming in Python or JavaScript, enough to read a function and
  follow its logic.
- **Required:** HTTP: methods, headers, cookies, status codes, and the browser's developer tools.
- **Required:** the command line, ``curl``, Git and a GitHub account.
- **Required:** basic generative AI concepts: system and user prompts, and tool calls.
- **Helpful:** Linux, Docker, DNS and IP addressing, and YAML.

Schedule
--------

The files that the lectures refer to are listed in full under `Smarter in the Source Code`_.

.. list-table::
   :header-rows: 1
   :widths: 8 8 84

   * - Block
     - Min
     - Content
   * - 1
     - 45
     - **Lecture 1: The threat landscape.** Attackers, assets and attack surfaces. The OWASP Top 10
       and the OWASP Top 10 for LLM Applications. Why AI applications add new attack surfaces: the
       prompt, retrieved content and tools.
   * - 2
     - 45
     - **Lab 1: Red team.** Each team builds an LLMClient that guards a secret phrase with system
       prompt instructions only, then attacks another team's. The journal records every attempt.
       Produces Assignment 1.
   * - 3
     - 45
     - **Lecture 2: Prompt injection.** Direct and indirect injection, jailbreaks, data
       exfiltration through links and images, and why no instruction can make a model reliably
       ignore instructions. :doc:`Guardrails </smarter-resources/smarter-guardrail>` as
       deterministic controls, and their limits.
   * - 4
     - 45
     - **Lab 2: Blue team.** Teams add the built-in guardrails ``prompt_injection_llm_judge_input``,
       ``secrets_leak_output`` and ``script_injection_output`` to their LLMClient, and the
       attackers try again. Produces Assignment 2.
   * - 5
     - 45
     - **Lecture 3: Secrets.** How Smarter stores provider and plugin credentials as encrypted
       :doc:`Secrets </smarter-resources/smarter-secret>`, why an API plugin's credentials never
       appear in a prompt, and the ``.env`` file, ``detect-private-key`` and
       ``detect-aws-credentials`` hooks.
   * - 6
     - 45
     - **Lecture 4: Outbound requests and SSRF.** Server-side request forgery, cloud metadata
       addresses, DNS rebinding, and a reading of
       ``smarter/smarter/apps/llmtool/plugin/safe_http.py``: public https only, fresh DNS resolution,
       and why that check must never be cached.
   * - 7
     - 45
     - **Lab 3: Map the defenses.** In groups, map each Smarter defense to a category of the two
       OWASP lists, with the file or document that implements it, and find the gaps. Produces
       Assignment 3.
   * - 8
     - 45
     - **Lecture 5: Secure development.** Static analysis with ``bandit``, dependency scanning,
       pre-commit hooks, code review, and Smarter's :doc:`ADR 016 on security </adr/016-security>`.
   * - 9
     - 45
     - **Lab 4: Read the code like an attacker.** Run ``bandit`` on one Smarter app, triage its
       findings, and decide which are real. Ungraded.
   * - 10
     - 45
     - **Lecture 6: Disclosure and response.** Responsible disclosure, security policies, CVEs,
       how open source projects handle reports, and incident response.
   * - 11
     - 30
     - **Capstone kickoff.** Students choose a capstone and scope it with the instructor.

Smarter in the Source Code
--------------------------

.. include:: source-code.txt

Graded Assignments
------------------

Assignment 1: Red Team Log
~~~~~~~~~~~~~~~~~~~~~~~~~~

Teams record their attacks on another team's prompt-only LLMClient: at least ten attempts with
different techniques, and which succeeded.

**Turn in:** the attack log, taken from the journal, with each technique named, and a half-page
summary.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Variety
     - 6
     - Ten or more attempts across several techniques (role play, encoding, translation,
       instruction override).
     - Repeats of one technique.
   * - Evidence
     - 5
     - From the journal.
     - Paraphrased.
   * - Classification
     - 5
     - Each attempt mapped to an OWASP LLM category.
     - Unclassified.
   * - Summary
     - 4
     - Explains why the successful attacks worked.
     - Lists results only.

Assignment 2: Blue Team Report
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Teams add guardrails to their LLMClient, are attacked again, and report the before-and-after
results, including legitimate prompts that were wrongly blocked.

**Turn in:** the guardrail manifests, the second attack log, and a one-page report.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Controls
     - 6
     - Guardrails chosen for the observed attacks, and configured correctly.
     - Guardrails added at random.
   * - Effectiveness
     - 5
     - Most attacks now fail, shown by the log.
     - No measured improvement.
   * - False positives
     - 5
     - Legitimate prompts tested; wrongful blocks reported.
     - Not tested.
   * - Honesty
     - 4
     - What still gets through is reported.
     - Claims complete protection.

Assignment 3: Defense Map
~~~~~~~~~~~~~~~~~~~~~~~~~

Groups map Smarter's defenses to the OWASP Top 10 and the OWASP Top 10 for LLM Applications, citing
the file or document that implements each, and identify three categories where defense is weak or
depends on the operator.

**Turn in:** a table and a one-page gap analysis.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Coverage
     - 5
     - Every category of both lists considered.
     - Several skipped.
   * - Accuracy
     - 7
     - Each defense correctly described and cited.
     - Defenses assumed, not found.
   * - Gap analysis
     - 6
     - Three well-reasoned gaps with suggested mitigations.
     - Vague gaps.
   * - Clarity
     - 2
     - Well organized.
     - Hard to follow.

Capstone Projects
-----------------

Students choose one. Capstones are due one week after the bootcamp.

Capstone A: A Threat Model of an AI Application
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Produce a structured threat model of a real AI application, and verify its
most important mitigations by testing.

Students choose a built-in LLMClient with tools (for example ``research_analyst`` or
``data_analyst``) and threat model it with STRIDE and the OWASP LLM list: a data flow diagram with
trust boundaries, threats, existing mitigations, residual risk, and tests of the three most
important mitigations on the class instance.

**What students turn in:**

- A threat model document (four to six pages) with a data flow diagram.
- Evidence of the three mitigation tests, from the journal.
- A prioritized list of recommendations.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Data flow and trust boundaries
     - 20
     - Accurate, with every boundary marked.
     - Boundaries missing.
   * - Threat identification
     - 25
     - Systematic, covering classic and AI-specific threats.
     - A few obvious threats.
   * - Mitigations
     - 20
     - Existing defenses correctly identified in code or docs.
     - Assumed.
   * - Verification
     - 20
     - Three mitigations tested, with evidence.
     - Untested.
   * - Recommendations
     - 15
     - Prioritized by risk, realistic.
     - Unprioritized.

Capstone B: A Hardened Assistant
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Build an AI application with defense in depth, and prove its security
properties with an adversarial test suite.

Students build an LLMClient with at least one tool plugin and access to sensitive information (a
fictional employee directory, for example), then harden it with least-privilege configuration,
guardrails on input and output, a budget, and a tight system prompt. They write and run an
adversarial test suite of at least twenty-five attacks and ten legitimate requests.

**What students turn in:**

- The manifests, with comments explaining each security decision.
- The test suite and its results from the journal, with attack success rate and false positive
  rate.
- A two-page security design note.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Defense in depth
     - 25
     - Several independent layers, each justified.
     - Relies on the system prompt.
   * - Least privilege
     - 15
     - Tools can do only what the job needs.
     - Broad access.
   * - Test suite
     - 25
     - Twenty-five varied attacks, including indirect injection, plus legitimate requests.
     - Few or repetitive attacks.
   * - Results
     - 20
     - Rates measured and honestly reported.
     - Cherry-picked results.
   * - Design note
     - 15
     - Explains residual risk.
     - Claims the system is secure.

Recommended Texts
-----------------

- **Pre-reading:** the `OWASP Top 10 for LLM Applications <https://genai.owasp.org/llm-top-10/>`__.
- **Reference:** Steve Wilson, *The Developer's Playbook for Large Language Model Security*
  (O'Reilly, 2024).
- **Reference:** Tanya Janca, *Alice and Bob Learn Application Security* (Wiley, 2020).
- **Smarter documentation:** :doc:`/smarter-platform/security`,
  :doc:`/smarter-platform/security-faq`, :doc:`/smarter-resources/smarter-guardrail`,
  :doc:`/smarter-resources/smarter-secret` and :doc:`/adr/016-security`.

Further Study
-------------

.. include:: further-study.txt
