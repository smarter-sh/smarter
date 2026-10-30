Writing Secure Software: Four-Week Online Course
================================================

A four-week online course on securing web applications and AI systems, using Smarter as the case
study. Smarter assumes that a model will eventually try to do something it should not, and defends
with deterministic controls rather than instructions: `guardrails
<https://github.com/smarter-sh/example-manifests/tree/main/guardrails>`__
on both the prompt and the reply, a single `hardened function
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/llmtool/plugin/safe_http.py>`__
for every outbound request to a user-supplied URL, credentials kept in encrypted `Secrets
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/secret/models.py>`__ that the
model never sees, and parameterized queries and tool allow lists for least privilege. Every defense
is in code that students can read and test. There are twelve 30-minute recorded lectures and a
90-minute live session each week. Week 1 covers classic web security, week 2 attacks on AI
applications, week 3 secrets, outbound requests and infrastructure, and week 4 secure development
and disclosure. See :doc:`../course-formats` for the format, the grading scale and the course
policies, and :doc:`../secure-software` for an overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Developers and security students.
   * - **Deployment**
     - A shared Smarter instance for attack and defense exercises, with an account per team.
       Students install Smarter from source by week 3, to read, test and scan the code.
   * - **Workload**
     - 3 hours of instruction and 4 to 6 hours of assignments each week.
   * - **Cost**
     - Expect less than $8 USD of model charges per student, capped by a per-student
       :doc:`Budget </smarter-resources/smarter-budget>`.

.. warning::

   Students attack only the class's own Smarter instance. Any real vulnerability in Smarter is
   reported privately, as described in the project's ``SECURITY.md``.

Learning Objectives
-------------------

By the end of the course, students can:

1. Find and explain common web vulnerabilities, and the defenses in a Django application.
2. Attack and defend AI applications, including indirect prompt injection through tools and
   retrieved content.
3. Explain and review how an application protects credentials and outbound requests.
4. Threat model an application, and verify its mitigations.
5. Use static analysis, dependency scanning and code review in a development process.
6. Report vulnerabilities responsibly and respond to incidents.

Technical Prerequisites
-----------------------

- **Required:** structured programming in Python or JavaScript.
- **Required:** HTTP, cookies and the browser's developer tools.
- **Required:** the command line, ``curl``, Git and a GitHub account.
- **Required:** basic generative AI concepts: system and user prompts, and tool calls.
- **Required by week 3:** Docker, and Smarter installed from source.
- **Helpful:** Linux, DNS and IP addressing, Django, Kubernetes, and YAML.

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
     - **The threat landscape.** Attackers, assets, attack surfaces, and the OWASP Top 10.
   * - 1
     - Lecture 2
     - **Injection and cross-site scripting.** SQL injection, XSS, and how Django's ORM and
       templates defend against them. Pre-reading: "The reply is untrusted HTML" in the case
       study `Guardrails: Can You Trust the Model? <https://smarter.sh/case-studies/guardrails>`__,
       on a model's reply rendered as HTML on someone else's site, sanitized by DOMPurify, with
       tests named after attacks.
   * - 1
     - Lecture 3
     - **Authentication and access control.** Sessions, CSRF, hashed API keys, broken
       object-level authorization, and account scoping in Smarter's ownership base model.
       Pre-reading: the case study `One Platform, Many Tenants
       <https://smarter.sh/case-studies/multi-tenancy>`__, and its questions on answering 404
       rather than 403, and on hashing API keys with SHA-512 but passwords with bcrypt.
   * - 1
     - Live session 1
     - Live exercises from PortSwigger's Web Security Academy, then a look at Smarter's defenses
       for each, and "Lab 2: Probe the edges" in `the multi-tenancy case study
       <https://smarter.sh/case-studies/multi-tenancy>`__, which tests CORS and session keys
       with ``curl``. Start Assignment 1.
   * - 2
     - Lecture 4
     - **The OWASP Top 10 for LLM Applications.** New attack surfaces: prompts, retrieved content
       and tools.
   * - 2
     - Lecture 5
     - **Prompt injection.** Direct and indirect injection, jailbreaks and exfiltration.
   * - 2
     - Lecture 6
     - **Deterministic controls.** :doc:`Guardrails </smarter-resources/smarter-guardrail>`,
       least privilege for tools, budgets, and measuring false positives.
   * - 2
     - Live session 2
     - Review of Assignment 1. Red team exercise against prompt-only LLMClients, then against
       the guarded assistant in "Lab 1: Talk to Sam" in `the guardrails case study
       <https://smarter.sh/case-studies/guardrails>`__. Start Assignment 2.
   * - 3
     - Lecture 7
     - **Secrets.** Encryption at rest, :doc:`Secrets </smarter-resources/smarter-secret>`,
       credentials out of prompts and logs, and secret scanning hooks.
   * - 3
     - Lecture 8
     - **SSRF and outbound requests.** Metadata addresses, DNS rebinding, and
       ``smarter/smarter/apps/llmtool/plugin/safe_http.py``. Pre-reading: "URLs a model chooses"
       in `the guardrails case study <https://smarter.sh/case-studies/guardrails>`__.
   * - 3
     - Lecture 9
     - **Infrastructure security.** Containers as non-root users with read-only application
       files, Calico network policies with default-deny ingress, private networks, cloud identity,
       and middleware that blocks scanners.
   * - 3
     - Live session 3
     - Review of Assignment 2. A guided code review of ``safe_http.py``. Capstone proposals
       discussed. Start Assignment 3.
   * - 4
     - Lecture 10
     - **Threat modeling.** Data flow diagrams, trust boundaries, STRIDE and prioritization.
   * - 4
     - Lecture 11
     - **Secure development.** ``bandit``, dependency scanning, pre-commit hooks, code review, and
       :doc:`ADR 016 </adr/016-security>`.
   * - 4
     - Lecture 12
     - **Disclosure and response.** Security policies, CVEs, coordinated disclosure, and incident
       response.
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

Assignment 1: Web Defenses in Django
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students complete five PortSwigger labs (SQL injection, stored XSS, CSRF, an access control flaw
and one of their choice), and for each, explain with code references how Smarter, as a Django
application, defends against that class of attack.

**Turn in:** lab completion screenshots and a two-page explanation.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Labs
     - 5
     - All five completed.
     - Fewer.
   * - Attack understanding
     - 5
     - Each attack explained in the student's own words.
     - Copied lab text.
   * - Defenses in Smarter
     - 7
     - Correct, with file references.
     - Assumed.
   * - Clarity
     - 3
     - Well organized.
     - Disorganized.

Assignment 2: Red Team, Blue Team
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Teams submit their attack log from Live session 2, harden their own LLMClient with guardrails and
least-privilege tools, are attacked again, and report the results.

**Turn in:** both logs, the manifests and a one-page report.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Attacks
     - 5
     - Varied, classified.
     - Repetitive.
   * - Defenses
     - 6
     - Targeted at observed attacks.
     - Random.
   * - Measurement
     - 5
     - Before and after, false positives tested.
     - None.
   * - Honesty
     - 4
     - Residual risk reported.
     - Claims complete protection.

Assignment 3: Secrets and SSRF Review
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students trace a provider API key from the ``.env`` file or a Secret manifest to the outbound HTTP
request, listing every place it is stored, decrypted or could be logged, then assess five SSRF
techniques against ``safe_http.py``.

**Turn in:** a two-page review with code references.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Secret lifecycle
     - 7
     - Every storage and use point, with references.
     - Gaps.
   * - SSRF assessment
     - 7
     - Five techniques correctly assessed.
     - Incorrect or partial.
   * - Recommendations
     - 4
     - Specific, realistic improvements.
     - None.
   * - Responsible handling
     - 2
     - Weaknesses reported privately.
     - Published.

Assignment 4: Static Analysis and Dependencies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students run ``bandit`` on one Smarter app and a dependency scanner (such as ``pip-audit`` or
``npm audit``) on the project, triage the findings, and judge which matter.

**Turn in:** the tool output and a triage table with justifications.

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
     - 7
     - Based on reading the code and the advisory.
     - Unjustified.
   * - Prioritization
     - 4
     - Ranked by exploitability and impact.
     - Unranked.
   * - Limits
     - 3
     - Notes what scanners miss.
     - Clean scan treated as proof.

Capstone Projects
-----------------

Students choose one, propose it before Live session 3, and present it in Live session 4.

Capstone A: A Full Threat Model and Security Review
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Carry out a professional-quality security review of a real application
feature, from threat model to verified findings.

Students pick a feature of Smarter that crosses trust boundaries, such as API plugins, MCP clients,
Extensions or the chat API, and produce a threat model, a code review of the relevant modules, tests of the
key mitigations, and a findings report.

**What students turn in:**

- A threat model with a data flow diagram and STRIDE analysis.
- A code review with references, and evidence of mitigation tests.
- A findings report ranked by severity. Real vulnerabilities are reported privately to the
  maintainers and only summarized in the report.
- A six-minute presentation.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Threat model
     - 20
     - Complete and accurate.
     - Superficial.
   * - Code review
     - 25
     - Careful, with references.
     - Skims.
   * - Verification
     - 20
     - Mitigations tested.
     - Untested.
   * - Findings
     - 20
     - Ranked, reproducible, with fixes.
     - Vague.
   * - Responsible handling and presentation
     - 15
     - Private disclosure followed; clear presentation.
     - Details published.

Capstone B: A Security Feature for Smarter
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Design, build and test a security control in a real application.

Students build a security improvement on their fork, for example a new guardrail strategy, a
detector for a class of secret not yet covered, an additional check in outbound request handling,
or a pre-commit hook. It needs tests that show attacks blocked and legitimate use allowed, and
documentation.

**What students turn in:**

- A pull request against their fork with the code, tests and documentation.
- A two-page design note: the threat, the control, its limits, and its false positive rate.
- A six-minute presentation.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Threat and design
     - 20
     - Real threat; control fits it.
     - Unclear threat.
   * - Implementation
     - 20
     - Correct, follows the code base's patterns.
     - Inconsistent.
   * - Tests
     - 25
     - Attacks blocked, legitimate use allowed, edge cases covered.
     - Happy path only.
   * - Limits
     - 15
     - Honest about what it does not stop.
     - Overclaims.
   * - Documentation and presentation
     - 20
     - Documented; clear presentation.
     - Undocumented.

Recommended Texts
-----------------

- **Required:** Tanya Janca, *Alice and Bob Learn Application Security* (Wiley, 2020), in weeks 1
  and 4.
- **Required:** Steve Wilson, *The Developer's Playbook for Large Language Model Security*
  (O'Reilly, 2024), in week 2.
- **Required:** Adam Shostack, *Threat Modeling: Designing for Security* (Wiley, 2014), part 1, in
  week 4.
- **Required:** the OWASP Top 10 lists and the `OWASP Cheat Sheet Series
  <https://cheatsheetseries.owasp.org/>`__ (SSRF, secrets management, Django), throughout.
- **Reference:** Corey Ball, *Hacking APIs* (No Starch Press, 2022).
- **Smarter documentation:** :doc:`/smarter-platform/security`,
  :doc:`/smarter-platform/security-faq`, :doc:`/smarter-resources/smarter-guardrail`,
  :doc:`/smarter-resources/smarter-secret`, :doc:`/adr/016-security` and
  :doc:`/smarter-framework/smarter-on-kubernetes`.

Further Study
-------------

.. include:: further-study.txt
