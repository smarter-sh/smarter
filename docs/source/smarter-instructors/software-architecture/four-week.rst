Software Architecture: Four-Week Online Course
==============================================

A four-week online course on software architecture, taught on Smarter's thirty-one
:doc:`Architecture Decision Records </adr>` and the code that implements them, with twelve
30-minute recorded lectures and a 90-minute live session each week. Week 1 covers describing an
architecture, week 2 decisions and their records, week 3 styles, patterns and data, and week 4
cloud, AI and evolution. See :doc:`../course-formats` for the format, the grading scale and the
course policies, and :doc:`../software-architecture` for an overview of the subject.

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
4. Compare architectural styles, integration patterns and data architectures.
5. Explain architecture for cloud-native and AI applications.
6. Plan the evolution of an architecture, with fitness functions and migration strategies.

Technical Prerequisites
-----------------------

- **Required:** at least two years of programming, or equivalent coursework.
- **Required:** reading Python, and Git for browsing history.
- **Required:** web application fundamentals: HTTP, databases, background jobs and caching.
- **Required by week 2:** Docker, to run Smarter.
- **Helpful:** Kubernetes concepts, Django, and a diagramming tool.

Schedule
--------

.. list-table::
   :header-rows: 1
   :widths: 10 18 72

   * - Week
     - Item
     - Content
   * - 1
     - Lecture 1
     - **What architecture is.** Decisions, quality attributes, trade-offs and the architect's
       role.
   * - 1
     - Lecture 2
     - **Quality attribute scenarios.** Making "scalable" and "secure" specific and measurable.
   * - 1
     - Lecture 3
     - **Describing architecture.** The C4 model, other views, and diagrams as code.
   * - 1
     - Live session 1
     - Groups draw Smarter's container diagram, and compare. Start Assignment 1.
   * - 2
     - Lecture 4
     - **Architecture Decision Records.** Nygard's format, and :doc:`ADR 000 </adr/000-intro>`.
   * - 2
     - Lecture 5
     - **Foundational decisions.** :doc:`Django </adr/001-django>`, :doc:`Docker </adr/002-docker>`,
       :doc:`Kubernetes </adr/003-kubernetes>` and the :doc:`twelve-factor app </adr/004-12-factor>`.
   * - 2
     - Lecture 6
     - **The heart of Smarter.** :doc:`Manifests </adr/005-manifests>`, the
       :doc:`REST API </adr/006-rest-api>`, and the :doc:`broker model </adr/024-broker-model>`.
   * - 2
     - Live session 2
     - Review of Assignment 1. A structured debate on one ADR. Start Assignment 2.
   * - 3
     - Lecture 7
     - **Styles.** Monolith, modular monolith, microservices, event-driven and serverless.
   * - 3
     - Lecture 8
     - **Integration and asynchrony.** Queues, :doc:`task queues </adr/030-task-queues>`,
       :doc:`async tasks </adr/009-async-tasks>`, and :doc:`caching </adr/018-caching>`.
   * - 3
     - Lecture 9
     - **Data and contracts.** :doc:`Database </adr/017-database>`, API
       :doc:`versioning </adr/023-api-versioning>`, and :doc:`Pydantic contracts </adr/031-pydantic-over-json>`.
   * - 3
     - Live session 3
     - Review of Assignment 2. A trade-off analysis workshop. Capstone proposals discussed. Start
       Assignment 3.
   * - 4
     - Lecture 10
     - **Cloud-native architecture.** Containers, Kubernetes, configuration, observability, and
       :doc:`/smarter-framework/guides/12-factor-app`.
   * - 4
     - Lecture 11
     - **Architecture for AI applications.** Models as untrusted components, tools, guardrails,
       :doc:`function calling </adr/008-function-calling>`, and cost as a quality attribute.
   * - 4
     - Lecture 12
     - **Evolving architecture.** Technical debt, fitness functions, strangler migrations,
       :doc:`feature flags </adr/022-feature-flags>`, and architecture when agents write code.
   * - 4
     - Live session 4
     - Capstone presentations (about 6 minutes each, with 2 minutes of questions), and a course
       retrospective.

Assignments 1 to 3 are due before the next live session. Assignment 4 is due in the middle of week
4. The capstone proposal is due before Live session 3, and the capstone at the start of Live
session 4.

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
implemented and whether it has drifted.

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

Assignment 3: Trade-off Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students analyze one ADR and its main alternative against their quality attribute scenarios, in a
trade-off matrix, and say which they would choose today and why.

**Turn in:** a matrix and a two-page analysis.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Matrix
     - 6
     - Options scored against scenarios, with reasons.
     - Scores without reasons.
   * - Alternative
     - 5
     - Concrete.
     - Vague.
   * - Judgment
     - 6
     - A reasoned choice for today's context.
     - No choice.
   * - Writing
     - 3
     - Clear.
     - Disorganized.

Assignment 4: An ADR of Your Own
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students write an ADR for a real decision in their own work, with context, alternatives and
consequences, and a fitness function that would detect if the decision were violated.

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
through the architecture, identify risks, sensitivity points and trade-off points, and recommend
changes with draft ADRs and fitness functions.

**What students turn in:**

- A seven- to ten-page review with diagrams and a utility tree of scenarios.
- Risks, sensitivity points and trade-off points.
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
     - Evidence-based, through code and configuration.
     - Opinions.
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
rollout plan.

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
- **Reference:** John Ousterhout, *A Philosophy of Software Design* (2nd edition, Yaknyam Press,
  2021), and Neal Ford, Mark Richards, Pramod Sadalage and Zhamak Dehghani, *Software
  Architecture: The Hard Parts* (O'Reilly, 2021).
- **Smarter documentation:** :doc:`/adr`, :doc:`/smarter-framework/smarter-broker-model`,
  :doc:`/smarter-framework/guides/12-factor-app` and :doc:`/smarter-framework/smarter-on-kubernetes`.

Further Study
-------------

.. include:: further-study.txt
