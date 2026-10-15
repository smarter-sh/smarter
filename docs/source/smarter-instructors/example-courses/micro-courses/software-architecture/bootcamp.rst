Software Architecture: Classroom Bootcamp
=========================================

An eight-hour classroom bootcamp on software architecture, taught on a large system that records
why it is built the way it is: Smarter's thirty-one :doc:`Architecture Decision Records </adr>`,
on topics from the choice of Django and Kubernetes to caching, task queues and API versioning.
The course is organized around the principles that working architects share as a vocabulary,
above all `The Twelve-Factor App <https://12factor.net/>`__, and alongside it infrastructure as
code, horizontal scalability, zero trust, extensibility and explicit data models. Smarter adopts
each of these, in code that students can open and read, and :doc:`ADR 004 </adr/004-12-factor>`
makes the twelve factors binding on every pull request. Students diagram the system, check its
decisions and principles against the code, argue the alternatives, and write ADRs of their own.
See :doc:`../course-formats` for the standard bootcamp day, the grading scale and the course
policies, and :doc:`../software-architecture` for an overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Experienced developers moving toward technical leadership, and advanced computer science
       students.
   * - **Deployment**
     - A clone of the repository is enough. A running Smarter (Quick Start or from source) helps
       students confirm what they read.
   * - **Cost**
     - Free.

Learning Objectives
-------------------

By the end of the bootcamp, students can:

1. Explain what architecture is: the decisions that are expensive to change, and the quality
   attributes that drive them.
2. Describe a large system at several levels with the C4 model.
3. Explain each of the twelve factors, and judge from the code whether a system follows it.
4. Recognize infrastructure as code, horizontal scalability, zero trust, extensibility and
   explicit data models in a real codebase, and say what each costs.
5. Trace a request through the classic web patterns, Model-View-Controller, Django's
   Model-View-Template and the LAMP stack, and say where a modern system departs from them.
6. Read an Architecture Decision Record, find the code that implements it, and judge whether they
   still agree.
7. Analyze the trade-offs of a decision, including the alternatives that were not chosen, and
   record a decision of their own as an ADR.

Technical Prerequisites
-----------------------

- **Required:** at least two years of programming, or equivalent coursework, in any language.
- **Required:** reading Python well enough to follow a module, and Git for browsing history.
- **Required:** web application fundamentals: HTTP, databases, background jobs and caching.
- **Helpful:** Docker and Kubernetes concepts, Django, and a diagramming tool (draw.io,
  Structurizr, Mermaid or PlantUML).

Schedule
--------

The file references in the lectures are listed in full under `Principles in the Source Code`_.

.. list-table::
   :header-rows: 1
   :widths: 8 8 84

   * - Block
     - Min
     - Content
   * - 1
     - 45
     - **Lecture 1: What architecture is.** Decisions that are hard to reverse, quality attributes
       (scalability, security, maintainability, cost), trade-offs, and the role of the architect.
       Principles as a shared vocabulary: the twelve factors, infrastructure as code, horizontal
       scalability, zero trust, extensibility and data models. A first look at Smarter: browser,
       CLI, API, workers, database, cache, model providers and Kubernetes.
   * - 2
     - 45
     - **Lab 1: Draw it.** In pairs, draw Smarter's C4 context and container diagrams, from the
       code, the Compose file and the docs. Produces Assignment 1.
   * - 3
     - 45
     - **Lecture 2: Architecture Decision Records.** Why record decisions, Nygard's format, and a
       guided reading of :doc:`ADR 001 on Django </adr/001-django>`,
       :doc:`ADR 004 on the twelve-factor app </adr/004-12-factor>` (an ADR that adopts a whole
       methodology), :doc:`ADR 005 on manifests </adr/005-manifests>` and
       :doc:`ADR 024 on the broker model </adr/024-broker-model>`.
   * - 4
     - 45
     - **Lab 2: Does the code agree?** Each student takes one ADR, finds the code that implements
       it, and judges whether the code still matches the decision. Produces Assignment 2.
   * - 5
     - 45
     - **Lecture 3: The twelve-factor app.** Heroku's methodology, factor by factor, each shown in
       Smarter's code: one codebase with a settings module per environment; config in the
       environment, validated by a Pydantic ``Settings`` class; MariaDB, Redis, S3 and SMTP as
       attached resources; a multi-stage Dockerfile and separate build, release and deploy
       workflows; stateless processes with sessions in the cache; port binding with uvicorn; web,
       worker, infrastructure worker and beat as separate process types; health and readiness
       probes; one image from laptop to production; logs to standard output; and admin work as
       ``manage.py`` commands and a Kubernetes Job. Smarter's own
       :doc:`twelve-factor guide </smarter-framework/guides/12-factor-app>` is read critically: a
       claim is only as good as the code behind it.
   * - 6
     - 45
     - **Lecture 4: Styles, patterns and extensibility.** A pattern review: Model-View-Controller
       and the separation it makes between data, presentation and input; Django's
       Model-View-Template, traced through the ``Secret`` model, its URLconf, views and
       templates; and the LAMP stack, set beside Smarter's Debian, uvicorn, MariaDB and Python.
       Then monolith, modular monolith (one Django app per resource family) and microservices;
       layered architecture; ports and adapters, in
       the infrastructure service layer that hides AWS behind
       ``infrastructure.dns``, ``.certificates``, ``.kubernetes`` and ``.email`` and swaps in an
       in-memory provider for tests; the
       :doc:`broker model </smarter-framework/smarter-broker-model>` and its registry of kinds;
       extension points for new plugin types, installable Extensions and new LLM providers. Data models: Django models
       for storage, Pydantic models for manifests and contracts
       (:doc:`ADR 031 </adr/031-pydantic-over-json>`), and the ownership base class that makes
       every resource belong to an account.
   * - 7
     - 45
     - **Lab 3: Twelve-factor audit.** Each pair audits four of the twelve factors against the
       code, with file and line references, and the class assembles a scorecard for the whole
       system. Produces Assignment 3.
   * - 8
     - 45
     - **Lecture 5: Architecture for the cloud and for AI.** Infrastructure as code: Terraform for
       the AWS foundation, a Helm chart for the platform, and Smarter itself as a declarative
       system that turns YAML manifests into DNS records, certificates and Kubernetes ingresses.
       Horizontal scalability: stateless pods, Horizontal Pod Autoscalers, a shared Redis cache
       (:doc:`ADR 018 </adr/018-caching>`) and Celery queues
       (:doc:`ADR 030 </adr/030-task-queues>`). Zero trust: every API call authenticated, every
       query filtered by owner, secrets encrypted at rest, network policies between pods,
       server-side request forgery blocked, and the model itself treated as untrusted, with
       guardrails on its input and output. Where Smarter stops short of full zero trust, and why.
   * - 9
     - 45
     - **Lab 4: Argue the opposite.** Teams take one ADR or principle and argue for the
       alternative: what would Smarter look like without it, and what would that have cost? A
       short debate follows, and each team drafts the losing side as an ADR. Ungraded.
   * - 10
     - 45
     - **Lecture 6: Evolving architecture.** Technical debt, migrations, API versioning
       (:doc:`ADR 023 </adr/023-api-versioning>`), feature flags
       (:doc:`ADR 022 </adr/022-feature-flags>`), fitness functions in CI (tests, coverage and
       pre-commit hooks), the audit journal as a record of change, and how architecture changes
       when coding agents write much of the code and the conventions live in ``CLAUDE.md`` and
       ``skills/``.
   * - 11
     - 30
     - **Capstone kickoff.** Students choose a capstone and its scope.

Principles in the Source Code
-----------------------------

.. include:: source-code.txt

Graded Assignments
------------------

Assignment 1: C4 Diagrams
~~~~~~~~~~~~~~~~~~~~~~~~~

Students draw Smarter's C4 context and container diagrams, with every container's technology and
responsibility, and the main relationships.

**Turn in:** the two diagrams (source and image) and a half-page key.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Accuracy
     - 8
     - Every container and external system correct, confirmed in code or config.
     - Missing or invented parts.
   * - C4 notation
     - 4
     - Correct levels, with technology and responsibility on each box.
     - Mixed levels.
   * - Relationships
     - 5
     - Labeled with purpose and protocol.
     - Unlabeled arrows.
   * - Clarity
     - 3
     - Readable at a glance.
     - Cluttered.

Assignment 2: ADR Verification
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students check one ADR against the code: where it is implemented, whether the code follows it,
and where it has drifted.

**Turn in:** a two-page report with code references.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Understanding
     - 5
     - The decision and its reasons summarized accurately.
     - Misread.
   * - Evidence
     - 7
     - Specific files and functions cited.
     - General statements.
   * - Judgment
     - 6
     - Clear verdict on conformance and drift, with reasons.
     - No verdict.
   * - Recommendation
     - 2
     - Update the code, or update the ADR.
     - None.

Assignment 3: Twelve-Factor Audit
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pairs audit four of the twelve factors against the code. For each factor they state what the
factor requires, find where Smarter meets it or falls short, and give a verdict: follows,
partly follows, or does not follow. At least one verdict must test a claim in Smarter's own
:doc:`twelve-factor guide </smarter-framework/guides/12-factor-app>` against the code. The
instructor assigns factors so that the class covers all twelve, and the pairs' findings are
combined into a scorecard for the whole system.

**Turn in:** a one-page table (factor, evidence with file and line references, verdict) and a
half page on the most important gap found.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Understanding
     - 5
     - Each factor's requirement stated accurately, in the pair's own words.
     - Copied or misstated.
   * - Evidence
     - 7
     - Files, settings and manifests cited for every verdict.
     - Verdicts without references.
   * - Judgment
     - 5
     - Verdicts that distinguish the letter of a factor from its intent, including the guide's
       claims.
     - Accepts the documentation at face value.
   * - Gap analysis
     - 3
     - The most important gap, its risk and a remedy.
     - None.

Capstone Projects
-----------------

Students choose one. Capstones are due one week after the bootcamp.

Capstone A: An Architecture Review of Smarter
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Carry out an architecture review of a real system against stated quality
attributes and established principles, and make evidence-based recommendations.

Students choose two quality attributes (for example scalability and security) and review Smarter
against them, using the ADRs, the code and the deployment configuration. They complete the
class's twelve-factor scorecard, and assess one of the principles in
`Beyond the Twelve Factors`_ (for example how far Smarter goes toward zero trust). They identify
risks and sensitivity points, and recommend changes.

**What students turn in:**

- An architecture review document (five to seven pages) with C4 diagrams.
- Quality attribute scenarios ("when X happens, the system should Y within Z").
- A complete twelve-factor scorecard, with code references.
- A ranked list of risks, and at least one recommendation written as a draft ADR.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Scenarios
     - 15
     - Specific, measurable quality attribute scenarios.
     - Vague goals.
   * - Analysis
     - 25
     - Traces each scenario through the architecture, with evidence.
     - Opinions.
   * - Principles
     - 15
     - Scorecard and principle assessment backed by code, not by the documentation alone.
     - Restates the documentation.
   * - Risks
     - 15
     - Ranked, with likelihood and impact.
     - Unranked.
   * - Recommendations
     - 15
     - Realistic, with a draft ADR.
     - Generic.
   * - Writing and diagrams
     - 15
     - Clear and accurate.
     - Unclear.

Capstone B: An Architecture for a New Feature
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Design a significant feature that fits an existing architecture and its
principles, and record the decisions it requires.

Students design a feature Smarter does not have, for example per-team model routing rules, a
scheduled report resource, or multi-region deployment. They place it in the existing architecture,
show that it keeps to the twelve factors and to Smarter's other principles (stateless processes,
the infrastructure facade, owned resources, a declarative manifest), identify the decisions it
needs, and write ADRs for the two most important.

**What students turn in:**

- A design document with C4 container and component diagrams.
- Two ADRs in the format of :doc:`/adr`.
- A list of the existing ADRs and principles the design depends on, and how it respects them.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Fit
     - 25
     - Uses existing patterns (brokers, manifests, tasks, the infrastructure facade) where they
       apply, and keeps to the twelve factors.
     - Ignores the existing architecture.
   * - Design
     - 20
     - Complete, with responsibilities and interfaces.
     - Sketchy.
   * - ADRs
     - 25
     - Real decisions, alternatives and consequences.
     - Descriptions, not decisions.
   * - Dependencies on existing ADRs and principles
     - 15
     - Correctly identified and respected.
     - Not considered.
   * - Diagrams and writing
     - 15
     - Clear.
     - Unclear.

Recommended Texts
-----------------

- **Pre-reading:** Adam Wiggins, `The Twelve-Factor App <https://12factor.net/>`__ (all twelve
  short chapters), Michael Nygard, `Documenting Architecture Decisions
  <https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions>`__ (2011), and
  :doc:`ADR 000 </adr/000-intro>`.
- **Reference:** Mark Richards and Neal Ford, *Fundamentals of Software Architecture* (2nd edition,
  O'Reilly, 2025).
- **Zero trust:** NIST, `SP 800-207, Zero Trust Architecture
  <https://csrc.nist.gov/pubs/sp/800/207/final>`__ (2020).
- **Smarter documentation:** :doc:`/adr`, :doc:`/smarter-framework/smarter-broker-model`,
  :doc:`/smarter-framework/guides/12-factor-app`, :doc:`/smarter-platform/cloud-infrastructure`
  and :doc:`/smarter-framework/smarter-on-kubernetes`.

Further Study
-------------

.. include:: further-study.txt
