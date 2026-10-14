Writing Secure Software: Two-Week Online Course
===============================================

A two-week online course on securing web applications and AI systems, using Smarter as the case
study. Smarter assumes that a model will eventually try to do something it should not, and defends
with deterministic controls rather than instructions: `guardrails
<https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/guardrail/data/guardrails>`__
on both the prompt and the reply, a single `hardened function
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/llmtool/plugin/safe_http.py>`__
for every outbound request to a user-supplied URL, credentials kept in encrypted `Secrets
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/secret/models.py>`__ that the
model never sees, and parameterized queries and tool allow lists for least privilege. Every defense
is in code that students can read and test. There are six 30-minute recorded lectures and a
90-minute live session each week. Week 1 covers attacks on AI applications and their defenses, and
week 2 covers secrets, outbound requests and secure development. See :doc:`../course-formats` for
the format, the grading scale and the course policies, and :doc:`../secure-software` for an overview
of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Developers and security students.
   * - **Deployment**
     - A shared Smarter instance run by the instructor for attack and defense exercises, with an
       account per team. Students clone the repository to read and scan the code.
   * - **Workload**
     - 3 hours of instruction and 4 to 6 hours of assignments each week.
   * - **Cost**
     - Expect less than $5 USD of model charges per student, capped by a per-student
       :doc:`Budget </smarter-resources/smarter-budget>`.

.. warning::

   Students attack only the class's own Smarter instance. Any real vulnerability in Smarter is
   reported privately, as described in the project's ``SECURITY.md``.

Learning Objectives
-------------------

By the end of the course, students can:

1. Explain both OWASP Top 10 lists with examples.
2. Attack an AI application with direct and indirect prompt injection, and defend it with
   deterministic controls.
3. Explain how an application protects credentials throughout their life.
4. Explain and defend against server-side request forgery.
5. Use static analysis and code review to find vulnerabilities, and handle them responsibly.

Technical Prerequisites
-----------------------

- **Required:** structured programming in Python or JavaScript.
- **Required:** HTTP, cookies and the browser's developer tools.
- **Required:** the command line, ``curl``, Git and a GitHub account.
- **Required:** basic generative AI concepts: system and user prompts, and tool calls.
- **Helpful:** Linux, Docker, DNS and IP addressing, YAML, and Python virtual environments for
  running ``bandit``.

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
     - **The threat landscape.** Attackers, assets, attack surfaces, and both OWASP Top 10 lists.
   * - 1
     - Lecture 2 (30 min)
     - **Prompt injection.** Direct and indirect injection, jailbreaks and data exfiltration.
   * - 1
     - Lecture 3 (30 min)
     - **Deterministic controls.** :doc:`Guardrails </smarter-resources/smarter-guardrail>`,
       allow lists, least privilege for tools, and measuring false positives.
   * - 1
     - Live session 1 (90 min)
     - Red team exercise: teams attack each other's prompt-only LLMClients, live. Start
       Assignment 1.
   * - 2
     - Lecture 4 (30 min)
     - **Secrets.** Encrypted :doc:`Secrets </smarter-resources/smarter-secret>`, credentials kept
       out of prompts, and the ``detect-private-key`` and ``detect-aws-credentials`` hooks.
   * - 2
     - Lecture 5 (30 min)
     - **SSRF and outbound requests.** Metadata addresses, DNS rebinding, and
       ``smarter/smarter/apps/llmtool/plugin/safe_http.py``.
   * - 2
     - Lecture 6 (30 min)
     - **Secure development and disclosure.** ``bandit``, dependency scanning, code review,
       :doc:`ADR 016 </adr/016-security>`, responsible disclosure and incident response.
   * - 2
     - Live session 2 (90 min)
     - Capstone presentations (about 5 minutes each, with 2 minutes of questions).

Assignment 1 is due at the end of week 1, Assignment 2 in the middle of week 2, and Assignment 3
and the capstone at the start of Live session 2.

Smarter in the Source Code
--------------------------

.. include:: source-code.txt

Graded Assignments
------------------

Assignment 1: Red Team, Blue Team
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Teams submit the log of their attacks from Live session 1, then add guardrails to their own
LLMClient, invite the attackers back, and report the before-and-after results.

**Turn in:** both attack logs from the journal, the guardrail manifests and a one-page report.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Attacks
     - 5
     - Ten or more, varied and classified by OWASP LLM category.
     - Repetitive or unclassified.
   * - Defenses
     - 6
     - Guardrails chosen for the observed attacks.
     - Added at random.
   * - Measurement
     - 5
     - Before and after, with false positives tested.
     - No measurement.
   * - Honesty
     - 4
     - Residual risk reported.
     - Claims complete protection.

Assignment 2: SSRF Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students explain, with references to the code, how ``safe_http.py`` stops a plugin from reaching
private and metadata addresses, then list five SSRF techniques (for example redirects, DNS
rebinding, IPv6 and decimal IP notation) and say whether each would be stopped and where.

**Turn in:** a two-page analysis with code references.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Code understanding
     - 7
     - Each check explained with line references.
     - General description.
   * - Techniques
     - 6
     - Five techniques, each correctly assessed.
     - Fewer, or incorrect assessments.
   * - Reasoning
     - 5
     - Explains why DNS must be resolved fresh before every request.
     - Not explained.
   * - Responsible handling
     - 2
     - Any suspected weakness reported privately.
     - Published.

Assignment 3: Static Analysis Triage
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students run ``bandit`` on one Smarter app, triage every finding as a true positive, false positive
or accepted risk, and justify each decision.

**Turn in:** the ``bandit`` output and a triage table.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Complete triage
     - 6
     - Every finding classified.
     - Some skipped.
   * - Justification
     - 8
     - Each decision supported by reading the code.
     - Decisions without reasons.
   * - Insight
     - 4
     - Notes what static analysis cannot find.
     - Treats a clean scan as proof of security.
   * - Clarity
     - 2
     - Well organized.
     - Disorganized.

Capstone Projects
-----------------

Students choose one, and present it in Live session 2.

Capstone A: A Threat Model of an AI Application
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Produce a structured threat model of a real AI application, and verify its
key mitigations by testing.

Students threat model a built-in LLMClient with tools, using STRIDE and the OWASP LLM list: data
flow diagram, trust boundaries, threats, mitigations found in the code, residual risk, and tests of
the three most important mitigations.

**What students turn in:**

- A threat model document with a data flow diagram.
- Evidence of mitigation tests.
- Prioritized recommendations, and a five-minute presentation.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Data flow and boundaries
     - 20
     - Accurate and complete.
     - Boundaries missing.
   * - Threats
     - 25
     - Systematic, classic and AI-specific.
     - A few obvious ones.
   * - Mitigations in code
     - 20
     - Found and cited.
     - Assumed.
   * - Verification
     - 20
     - Three tested, with evidence.
     - Untested.
   * - Recommendations and presentation
     - 15
     - Prioritized; clear presentation.
     - Unprioritized.

Capstone B: A Hardened Assistant with an Adversarial Test Suite
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Build an AI application with defense in depth, and prove its security
properties with tests.

Students build an LLMClient with a tool and access to fictional sensitive data, harden it, and run
an adversarial suite of at least thirty attacks (including indirect injection through a web page
or document it reads) and fifteen legitimate requests. Classmates are invited to attack it during
the week before presentations.

**What students turn in:**

- Commented manifests.
- The test suite, results, attack success rate and false positive rate.
- A two-page design note on residual risk, and a five-minute presentation.

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
     - Independent layers, each justified.
     - System prompt only.
   * - Least privilege
     - 15
     - Tools limited to the job.
     - Broad access.
   * - Test suite
     - 25
     - Thirty varied attacks, including indirect, plus legitimate requests.
     - Repetitive.
   * - Results and honesty
     - 20
     - Rates measured; classmates' successful attacks reported.
     - Cherry-picked.
   * - Design note and presentation
     - 15
     - Residual risk explained.
     - Claims to be secure.

Recommended Texts
-----------------

- **Required:** Steve Wilson, *The Developer's Playbook for Large Language Model Security*
  (O'Reilly, 2024), in week 1.
- **Required:** the `OWASP Top 10 <https://owasp.org/www-project-top-ten/>`__ and the
  `OWASP Top 10 for LLM Applications <https://genai.owasp.org/llm-top-10/>`__, in week 1.
- **Required:** the OWASP `SSRF Prevention Cheat Sheet
  <https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html>`__,
  in week 2.
- **Reference:** Tanya Janca, *Alice and Bob Learn Application Security* (Wiley, 2020), and Adam
  Shostack, *Threat Modeling: Designing for Security* (Wiley, 2014), for the capstone.
- **Smarter documentation:** :doc:`/smarter-platform/security`,
  :doc:`/smarter-platform/security-faq`, :doc:`/smarter-resources/smarter-guardrail`,
  :doc:`/smarter-resources/smarter-secret` and :doc:`/adr/016-security`.

Further Study
-------------

.. include:: further-study.txt
