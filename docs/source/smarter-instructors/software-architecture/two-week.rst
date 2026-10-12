Software Architecture: Two-Week Online Course
=============================================

A two-week online course on software architecture, taught on a large system that records why it
is built the way it is: Smarter's thirty-one :doc:`Architecture Decision Records </adr>`, and the
`code <https://github.com/smarter-sh/smarter>`__ that implements them. The course is organized
around the principles that working architects share as a vocabulary, above all
`The Twelve-Factor App <https://12factor.net/>`__, which :doc:`ADR 004 </adr/004-12-factor>` makes
binding on every pull request, and alongside it infrastructure as code, horizontal scalability,
zero trust, extensibility and explicit data models. Every principle is traced to the files that
implement it, listed under `Principles in the Source Code`_. There are six 30-minute recorded
lectures and a 90-minute live session each week. Week 1 covers describing and reading an
architecture and its decisions, and week 2 covers the twelve factors, styles, patterns and
evolution. See :doc:`../course-formats` for the format, the grading scale and the course policies,
and :doc:`../software-architecture` for an overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Experienced developers moving toward technical leadership, and advanced computer science
       students.
   * - **Deployment**
     - A clone of the repository. A running Smarter helps students confirm what they read.
   * - **Workload**
     - 3 hours of instruction and 4 to 6 hours of assignments each week.
   * - **Cost**
     - Free.

Learning Objectives
-------------------

By the end of the course, students can:

1. Explain architecture as decisions and trade-offs between quality attributes.
2. Describe a large system with the C4 model.
3. Explain each of the twelve factors, and judge from the code whether a system follows it.
4. Recognize infrastructure as code, horizontal scalability, zero trust, extensibility and
   explicit data models in a real codebase, and say what each costs.
5. Verify ADRs against code, and recognize drift.
6. Compare architectural styles and patterns for a given problem, write ADRs, and plan the
   evolution of an architecture.

Technical Prerequisites
-----------------------

- **Required:** at least two years of programming, or equivalent coursework.
- **Required:** reading Python, and Git for browsing history.
- **Required:** web application fundamentals: HTTP, databases, background jobs and caching.
- **Helpful:** Docker and Kubernetes concepts, Django, and a diagramming tool.

Schedule
--------

The file references in the lectures are listed in full under `Principles in the Source Code`_.

.. list-table::
   :header-rows: 1
   :widths: 10 18 72

   * - Week
     - Item
     - Content
   * - 1
     - Lecture 1 (30 min)
     - **What architecture is.** Decisions that are hard to reverse, quality attributes and
       trade-offs. Principles as a shared vocabulary: the twelve factors, infrastructure as code,
       horizontal scalability, zero trust, extensibility and data models. A first look at Smarter:
       browser, CLI, API, workers, database, cache, model providers and Kubernetes.
   * - 1
     - Lecture 2 (30 min)
     - **Describing architecture.** The C4 model, views, and diagrams as code.
   * - 1
     - Lecture 3 (30 min)
     - **Architecture Decision Records.** Nygard's format, and readings of
       :doc:`ADR 001 on Django </adr/001-django>`,
       :doc:`ADR 004 on the twelve-factor app </adr/004-12-factor>` (an ADR that adopts a whole
       methodology), :doc:`ADR 005 on manifests </adr/005-manifests>` and
       :doc:`ADR 024 on the broker model </adr/024-broker-model>`.
   * - 1
     - Live session 1 (90 min)
     - Groups draw Smarter's container diagram together, and compare. Start Assignment 1.
   * - 2
     - Lecture 4 (30 min)
     - **The twelve-factor app.** Factor by factor, each shown in Smarter's code: a settings
       module per environment, config validated by a Pydantic ``Settings`` class, attached
       resources, a multi-stage Dockerfile, stateless processes with sessions in Redis, four
       process types, health and readiness probes, logs to standard output, and admin work as
       ``manage.py`` commands and a Kubernetes Job. Smarter's own
       :doc:`twelve-factor guide </smarter-framework/guides/12-factor-app>` is read critically.
   * - 2
     - Lecture 5 (30 min)
     - **Styles, patterns and extensibility.** Modular monolith (one Django app per resource
       family), ports and adapters in the infrastructure service layer, the
       :doc:`broker model </smarter-framework/smarter-broker-model>` and its registry of kinds,
       and Django models for storage beside Pydantic models for contracts
       (:doc:`ADR 031 </adr/031-pydantic-over-json>`). Horizontal scalability with autoscalers,
       caching (:doc:`ADR 018 </adr/018-caching>`) and task queues
       (:doc:`ADR 030 </adr/030-task-queues>`).
   * - 2
     - Lecture 6 (30 min)
     - **Zero trust and evolution.** Every API call authenticated, every query filtered by owner,
       secrets encrypted, network policies, server-side request forgery blocked, and the model
       treated as untrusted. Then technical debt, API versioning
       (:doc:`ADR 023 </adr/023-api-versioning>`), feature flags
       (:doc:`ADR 022 </adr/022-feature-flags>`), fitness functions in CI, and architecture when
       coding agents write much of the code and the conventions live in ``CLAUDE.md`` and
       ``skills/``.
   * - 2
     - Live session 2 (90 min)
     - Capstone presentations (about 5 minutes each, with 2 minutes of questions).

Assignment 1 is due at the end of week 1, Assignment 2 in the middle of week 2, and Assignment 3
and the capstone at the start of Live session 2.

Principles in the Source Code
-----------------------------

.. include:: source-code.txt

Graded Assignments
------------------

Assignment 1: C4 Diagrams
~~~~~~~~~~~~~~~~~~~~~~~~~

Students draw Smarter's context, container and one component diagram (for example, of the broker
layer), confirmed against the code.

**Turn in:** the diagrams (source and image) and a key.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Accuracy
     - 8
     - Confirmed in code and configuration.
     - Missing or invented parts.
   * - Notation
     - 4
     - Correct levels and labels.
     - Mixed levels.
   * - Component diagram
     - 5
     - Correct responsibilities and interactions.
     - Superficial.
   * - Clarity
     - 3
     - Readable.
     - Cluttered.

Assignment 2: ADR Verification
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students check two ADRs against the code, and report conformance and drift.

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
     - Accurate summaries.
     - Misread.
   * - Evidence
     - 7
     - Specific references.
     - General.
   * - Judgment
     - 6
     - Clear verdicts with reasons.
     - None.
   * - Recommendation
     - 2
     - Code or ADR to update.
     - None.

Assignment 3: Twelve-Factor Audit
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students audit four of the twelve factors against the code. For each factor they state what it
requires, find where Smarter meets it or falls short, and give a verdict: follows, partly follows,
or does not follow. At least one verdict must test a claim in Smarter's own
:doc:`twelve-factor guide </smarter-framework/guides/12-factor-app>` against the code. The
instructor assigns factors so that the class covers all twelve, and the findings are combined into
a scorecard for the whole system, reviewed in Live session 2.

**Turn in:** a one-page table (factor, evidence with file and line references, verdict) and a half
page on the most important gap found.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Understanding
     - 5
     - Each factor's requirement stated accurately.
     - Copied or misstated.
   * - Evidence
     - 7
     - Files, settings and manifests cited for every verdict.
     - Verdicts without references.
   * - Judgment
     - 5
     - Distinguishes the letter of a factor from its intent.
     - Accepts the documentation at face value.
   * - Gap analysis
     - 3
     - The most important gap, its risk and a remedy.
     - None.

Capstone Projects
-----------------

Students choose one, and present it in Live session 2.

Capstone A: An Architecture Review of Smarter
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Review a real system against stated quality attributes, and recommend
changes with evidence.

Students review Smarter against two quality attributes with scenarios, trace them through the
architecture, assess one of the principles in `Beyond the Twelve Factors`_ (for example how far
Smarter goes toward zero trust), rank the risks, and draft an ADR for the most important
recommendation.

**What students turn in:**

- A five- to seven-page review with diagrams and scenarios.
- A ranked risk list and a draft ADR.
- A five-minute presentation.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Scenarios
     - 20
     - Specific and measurable.
     - Vague.
   * - Analysis
     - 25
     - Evidence-based.
     - Opinions.
   * - Risks
     - 20
     - Ranked.
     - Unranked.
   * - Recommendation
     - 20
     - Draft ADR, realistic.
     - Generic.
   * - Presentation
     - 15
     - Clear and on time.
     - Overruns.

Capstone B: An Architecture for a New Feature
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Design a significant feature that fits an existing architecture, and record
its decisions.

Students design a feature Smarter does not have, for example per-team model routing rules, a
scheduled report resource, or multi-region deployment. They place it in the architecture with C4
diagrams, show that it keeps to the twelve factors and to Smarter's other principles (stateless
processes, the infrastructure facade, owned resources, a declarative manifest), and write ADRs for
its two most important decisions.

**What students turn in:**

- A design document with diagrams, and two ADRs.
- A list of the existing ADRs and principles it depends on, and how it respects them.
- A five-minute presentation.

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
     - Uses existing patterns (brokers, manifests, tasks, the infrastructure facade), and keeps
       to the twelve factors.
     - Ignores them.
   * - Design
     - 20
     - Complete.
     - Sketchy.
   * - ADRs
     - 25
     - Real decisions with alternatives.
     - Descriptions.
   * - Dependencies
     - 15
     - Identified and respected.
     - Ignored.
   * - Presentation
     - 15
     - Clear.
     - Unclear.

Recommended Texts
-----------------

- **Required:** Mark Richards and Neal Ford, *Fundamentals of Software Architecture* (2nd edition,
  O'Reilly, 2025). Week 1: part 1 (foundations). Week 2: selected chapters of part 2
  (architecture styles).
- **Required:** Michael Nygard, `Documenting Architecture Decisions
  <https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions>`__ (2011), in week 1,
  and Adam Wiggins, `The Twelve-Factor App <https://12factor.net/>`__ (all twelve short chapters),
  before Lecture 4.
- **Zero trust:** NIST, `SP 800-207, Zero Trust Architecture
  <https://csrc.nist.gov/pubs/sp/800/207/final>`__ (2020).
- **Reference:** John Ousterhout, *A Philosophy of Software Design* (2nd edition, Yaknyam Press,
  2021).
- **Smarter documentation:** :doc:`/adr`, :doc:`/smarter-framework/smarter-broker-model`,
  :doc:`/smarter-framework/guides/12-factor-app`, :doc:`/smarter-platform/cloud-infrastructure`
  and :doc:`/smarter-framework/smarter-on-kubernetes`.

Further Study
-------------

.. include:: further-study.txt
