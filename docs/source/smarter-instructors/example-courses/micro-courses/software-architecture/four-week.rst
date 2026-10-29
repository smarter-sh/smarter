Software Architecture: Four-Week Online Course
==============================================

A four-week online course on software architecture, taught on a large system that records why it is
built the way it is: Smarter's thirty-one :doc:`Architecture Decision Records </adr>`, and the `code
<https://github.com/smarter-sh/smarter>`__ and `infrastructure
<https://github.com/smarter-sh/smarter-infrastructure>`__ that implement them. The course is
organized around the principles that working architects share as a vocabulary, above all `The
Twelve-Factor App <https://12factor.net/>`__, which :doc:`ADR 004 </adr/004-12-factor>` makes
binding on every pull request, and alongside it infrastructure as code, horizontal scalability, zero
trust, extensibility and explicit data models. Every principle is traced to the files that implement
it, listed under `Principles in the Source Code`_. There are twelve 30-minute recorded lectures and
a 90-minute live session each week. Week 1 covers describing an architecture, week 2 decisions,
their records and the twelve factors, week 3 styles, scalability, data and contracts, and week 4
infrastructure as code, zero trust, AI and evolution. See :doc:`../course-formats` for the format,
the grading scale and the course policies, and :doc:`../software-architecture` for an overview of
the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Experienced developers moving toward technical leadership, and advanced computer science
       students.
   * - **Deployment**
     - A clone of the repository, and a running Smarter (Quick Start or from source) by week 2.
   * - **Workload**
     - 3 hours of instruction and 4 to 6 hours of assignments each week.
   * - **Cost**
     - Free.

Learning Objectives
-------------------

By the end of the course, students can:

1. Explain architecture as decisions and trade-offs between quality attributes, and write quality
   attribute scenarios.
2. Describe a large system with the C4 model and other views.
3. Read, verify and write Architecture Decision Records.
4. Explain each of the twelve factors, and judge from the code whether a system follows it.
5. Compare architectural styles, classic patterns (Model-View-Controller, Model-View-Template
   and the LAMP stack), integration patterns and data architectures, and recognize
   infrastructure as code, horizontal scalability, zero trust, extensibility and explicit data
   models in a real codebase.
6. Explain architecture for cloud-native and AI applications, including cost as a quality
   attribute and the model as an untrusted component.
7. Plan the evolution of an architecture, with fitness functions and migration strategies.

Technical Prerequisites
-----------------------

- **Required:** at least two years of programming, or equivalent coursework.
- **Required:** reading Python, and Git for browsing history.
- **Required:** web application fundamentals: HTTP, databases, background jobs and caching.
- **Required by week 2:** Docker, to run Smarter.
- **Helpful:** Kubernetes concepts, Django, and a diagramming tool.

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
     - Lecture 1
     - **What architecture is.** Decisions, quality attributes, trade-offs and the architect's
       role. Principles as a shared vocabulary: the twelve factors, infrastructure as code,
       horizontal scalability, zero trust, extensibility and data models.
   * - 1
     - Lecture 2
     - **Quality attribute scenarios.** Making "scalable" and "secure" specific and measurable.
   * - 1
     - Lecture 3
     - **Describing architecture.** The C4 model, other views, and diagrams as code. A first look
       at Smarter: browser, CLI, API, workers, database, cache, model providers and Kubernetes.
   * - 1
     - Live session 1
     - Groups draw Smarter's container diagram from
       `docker-compose.yml <https://github.com/smarter-sh/smarter/blob/main/docker-compose.yml>`__
       and the `Helm templates
       <https://github.com/smarter-sh/smarter/tree/main/helm/charts/smarter/templates>`__, and
       compare. Start Assignment 1.
   * - 2
     - Lecture 4
     - **Architecture Decision Records.** Nygard's format, :doc:`ADR 000 </adr/000-intro>`, and
       :doc:`ADR 004 </adr/004-12-factor>` as an ADR that adopts a whole methodology.
   * - 2
     - Lecture 5
     - **Foundational decisions.** :doc:`Django </adr/001-django>`, :doc:`Docker </adr/002-docker>`,
       :doc:`Kubernetes </adr/003-kubernetes>`, :doc:`manifests </adr/005-manifests>`, the
       :doc:`REST API </adr/006-rest-api>` and the :doc:`broker model </adr/024-broker-model>`.
   * - 2
     - Lecture 6
     - **The twelve-factor app.** Factor by factor, each shown in Smarter's code: a settings
       module per environment, config validated by a Pydantic ``Settings`` class
       (:doc:`ADR 007 </adr/007-settings>`), attached resources, a multi-stage Dockerfile and
       separate build, release and deploy workflows, stateless processes with sessions in Redis,
       port binding with uvicorn, four process types, health and readiness probes, logs to
       standard output (:doc:`ADR 011 </adr/011-logging>`), and admin work as ``manage.py``
       commands and a Kubernetes Job (:doc:`ADR 010 </adr/010-management-commands>`).
   * - 2
     - Live session 2
     - Review of Assignment 1. A structured debate on one ADR. The instructor assigns factors for
       the twelve-factor audit. Start Assignment 2.
   * - 3
     - Lecture 7
     - **Styles and extensibility.** A pattern review: Model-View-Controller from Smalltalk to the
       web, Django's Model-View-Template traced through the ``Secret`` model, URLconf, views and
       templates, the web console's split of MVC between Django and React, and the LAMP stack
       beside Smarter's Debian, uvicorn, MariaDB and Python. Then monolith, modular monolith (one
       Django app per resource family), microservices, event-driven and serverless. Ports and adapters in the
       infrastructure service layer, the broker registry of kinds, ``PluginBase`` for new plugin
       types, Extensions installed at run time, and Provider manifests for new LLM providers.
   * - 3
     - Lecture 8
     - **Integration, asynchrony and horizontal scalability.** Queues, :doc:`task queues
       </adr/030-task-queues>`, :doc:`async tasks </adr/009-async-tasks>`,
       :doc:`caching </adr/018-caching>`, stateless pods and Horizontal Pod Autoscalers.
   * - 3
     - Lecture 9
     - **Data and contracts.** The :doc:`database </adr/017-database>`, Django models for storage
       and :doc:`Pydantic models for contracts </adr/031-pydantic-over-json>`, the ownership base
       class that makes every resource belong to an account, and API
       :doc:`versioning </adr/023-api-versioning>`. Pre-reading: "Where to put the seam",
       "Generated, never written" and "Breaking changes and versions" in the case study
       `One Contract, Five Clients <https://smarter.sh/case-studies/api-contract>`__.
   * - 3
     - Live session 3
     - Review of Assignment 2, and the class's twelve-factor scorecard. A trade-off analysis
       workshop. Capstone proposals discussed. Start Assignment 3.
   * - 4
     - Lecture 10
     - **Infrastructure as code and cloud-native architecture.** Terraform and Terragrunt in
       `smarter-infrastructure <https://github.com/smarter-sh/smarter-infrastructure>`__, a Helm
       chart validated by a JSON schema, and Smarter itself as a declarative system that turns
       manifests into DNS records, certificates and ingresses, followed in "One deploy, end to
       end" and "Waiting without blocking" in the case study `What Happens When You Click Deploy
       <https://smarter.sh/case-studies/deploy>`__. Observability with logs and the
       :doc:`journal </smarter-platform/smarter-journal>`.
   * - 4
     - Lecture 11
     - **Zero trust and architecture for AI.** :doc:`ADR 016 </adr/016-security>`: every call
       authenticated, every query filtered by owner, secrets encrypted, network policies, and
       server-side request forgery blocked. Models as untrusted components, guardrails on input
       and output, :doc:`function calling </adr/008-function-calling>`, and cost as a quality
       attribute. Where Smarter stops short of full zero trust, and why.
   * - 4
     - Lecture 12
     - **Evolving architecture.** Technical debt, fitness functions in CI (tests, coverage and
       pre-commit hooks), strangler migrations, :doc:`feature flags </adr/022-feature-flags>`, and
       architecture when coding agents write much of the code and the conventions live in
       ``CLAUDE.md`` and ``skills/``. Pre-reading: "Five success factors", "The antipattern" and
       "Fixing it" in the case study `Converge or Diverge: AI Coding Agents
       <https://smarter.sh/case-studies/ai-coding-agents>`__, whose "Lab 2: Measure the series"
       measures a spreading pattern across release tags with git.
   * - 4
     - Live session 4
     - Capstone presentations (about 6 minutes each, with 2 minutes of questions), and a course
       retrospective.

Assignments 1 to 3 are due before the next live session. Assignment 4 is due in the middle of week
4. The capstone proposal is due before Live session 3, and the capstone at the start of Live
session 4.

Principles in the Source Code
-----------------------------

.. include:: source-code.txt

Graded Assignments
------------------

Assignment 1: C4 Diagrams and Scenarios
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students draw Smarter's context, container and one component diagram, and write five quality
attribute scenarios that the architecture should satisfy.

**Turn in:** the diagrams and the scenarios.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Diagram accuracy
     - 7
     - Confirmed in code and configuration.
     - Invented parts.
   * - Notation
     - 4
     - Correct levels and labels.
     - Mixed.
   * - Scenarios
     - 6
     - Source, stimulus, response and measure for each.
     - Vague goals.
   * - Clarity
     - 3
     - Readable.
     - Cluttered.

Assignment 2: ADR Verification
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students verify three ADRs against the code and the git history, including when each was
implemented and whether it has drifted. One of the three is :doc:`ADR 004 </adr/004-12-factor>`,
checked for the factors that the instructor assigned in Live session 2.

**Turn in:** a three-page report with code and commit references.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Understanding
     - 4
     - Accurate summaries.
     - Misread.
   * - Evidence
     - 7
     - Code and commit references.
     - General.
   * - Judgment
     - 6
     - Verdicts with reasons.
     - None.
   * - Recommendations
     - 3
     - Specific.
     - None.

Assignment 3: Principles Audit
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students audit four of the twelve factors and one principle from `Beyond the Twelve Factors`_
(for example zero trust or horizontal scalability) against the code. For each they state what it
requires, find where Smarter meets it or falls short, and give a verdict: follows, partly follows,
or does not follow. At least one verdict must test a claim in Smarter's own
:doc:`twelve-factor guide </smarter-framework/guides/12-factor-app>` against the code. Then they
analyze the most important gap and its main remedy against their quality attribute scenarios, in
a short trade-off matrix.

**Turn in:** a one-page table (principle, evidence with file and line references, verdict), and a
two-page analysis of the most important gap, with the matrix.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Evidence
     - 7
     - Files, settings and manifests cited for every verdict.
     - Verdicts without references.
   * - Judgment
     - 5
     - Distinguishes the letter of a principle from its intent, including the guide's claims.
     - Accepts the documentation at face value.
   * - Trade-off matrix
     - 5
     - Options scored against scenarios, with reasons.
     - Scores without reasons.
   * - Writing
     - 3
     - Clear.
     - Disorganized.

Assignment 4: An ADR of Your Own
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students write an ADR for a real decision in their own work, with context, alternatives and
consequences, and a fitness function that would detect if the decision were violated. The step
"Add a mechanical guard where you can" in `the AI coding agents case study
<https://smarter.sh/case-studies/ai-coding-agents>`__ is a worked example: a test, proposed but
not yet written, that would catch a second way of caching.

**Turn in:** the ADR in the format of :doc:`/adr`.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Context
     - 4
     - Clear forces.
     - Missing.
   * - Alternatives
     - 6
     - Fairly compared.
     - None.
   * - Consequences
     - 5
     - Good and bad.
     - Benefits only.
   * - Fitness function
     - 5
     - Automatable and specific.
     - Vague.

Capstone Projects
-----------------

Students choose one, propose it before Live session 3, and present it in Live session 4.

Capstone A: An Architecture Review of Smarter
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Carry out an architecture review of a real system in the style of an
architecture tradeoff analysis, and make evidence-based recommendations.

Students review Smarter against three quality attributes with prioritized scenarios, trace each
through the architecture, complete the class's twelve-factor scorecard, assess how far Smarter goes
toward one principle in `Beyond the Twelve Factors`_, identify risks, sensitivity points and
trade-off points, and recommend changes with draft ADRs and fitness functions.

**What students turn in:**

- A seven- to ten-page review with diagrams and a utility tree of scenarios.
- Risks, sensitivity points and trade-off points.
- A complete twelve-factor scorecard, with code references.
- Two draft ADRs with fitness functions.
- A six-minute presentation.

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
     - Prioritized and measurable.
     - Vague.
   * - Analysis
     - 25
     - Evidence-based, through code and configuration, including the scorecard.
     - Opinions, or the documentation restated.
   * - Risks and trade-offs
     - 20
     - Sensitivity and trade-off points identified.
     - Risks only.
   * - Recommendations
     - 20
     - Draft ADRs and fitness functions.
     - Generic.
   * - Presentation
     - 20
     - Clear and on time.
     - Overruns.

Capstone B: Architecture for a New Product on Smarter
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Design the architecture of a new system that builds on an existing platform,
and record its decisions.

Students design a product built on Smarter's API, for example a multi-tenant customer support
service, or an internal AI portal for a university. They produce scenarios, C4 diagrams down to
components for the most important container, ADRs for its three key decisions, and a migration or
rollout plan. The design keeps to the twelve factors and to Smarter's principles, and uses its
resources through the :doc:`REST API </smarter-framework/smarter-api>` rather than rebuilding
them.

**What students turn in:**

- A design document with scenarios and diagrams.
- Three ADRs with fitness functions.
- A rollout plan, and a six-minute presentation.

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
     - Drive the design.
     - Absent or ignored.
   * - Design
     - 25
     - Complete, with responsibilities and interfaces.
     - Sketchy.
   * - Use of the platform
     - 15
     - Uses Smarter's resources and API appropriately.
     - Rebuilds what exists.
   * - ADRs
     - 25
     - Real decisions, alternatives, fitness functions.
     - Descriptions.
   * - Rollout and presentation
     - 20
     - Realistic plan, clear presentation.
     - Missing.

Recommended Texts
-----------------

- **Required:** Mark Richards and Neal Ford, *Fundamentals of Software Architecture* (2nd edition,
  O'Reilly, 2025), across weeks 1 to 3.
- **Required:** Neal Ford, Rebecca Parsons, Patrick Kua and Pramod Sadalage, *Building Evolutionary
  Architectures* (2nd edition, O'Reilly, 2022), chapters on fitness functions, in week 4.
- **Required:** Martin Kleppmann, *Designing Data-Intensive Applications* (O'Reilly, 2017),
  chapter 1 (reliability, scalability and maintainability) and chapter 11 (stream processing), or
  the corresponding chapters of the second edition, in week 3.
- **Required:** Adam Wiggins, `The Twelve-Factor App <https://12factor.net/>`__ (all twelve short
  chapters), before Lecture 6, and NIST, `SP 800-207, Zero Trust Architecture
  <https://csrc.nist.gov/pubs/sp/800/207/final>`__ (2020), sections 2 and 3, before Lecture 11.
- **Reference:** John Ousterhout, *A Philosophy of Software Design* (2nd edition, Yaknyam Press,
  2021), and Neal Ford, Mark Richards, Pramod Sadalage and Zhamak Dehghani, *Software
  Architecture: The Hard Parts* (O'Reilly, 2021).
- **Smarter documentation:** :doc:`/adr`, :doc:`/smarter-framework/smarter-broker-model`,
  :doc:`/smarter-framework/guides/12-factor-app`, :doc:`/smarter-platform/cloud-infrastructure`,
  :doc:`/smarter-platform/security` and :doc:`/smarter-framework/smarter-on-kubernetes`.

Further Study
-------------

.. include:: further-study.txt
