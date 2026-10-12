Software Architecture: Classroom Bootcamp
=========================================

An eight-hour classroom bootcamp on software architecture, taught on a large system that records
why it is built the way it is: Smarter's thirty-one :doc:`Architecture Decision Records </adr>`,
on topics from the choice of Django and Kubernetes to caching, task queues and API versioning.
Students diagram the system, check decisions against the code, argue the alternatives, and write an
ADR of their own. See :doc:`../course-formats` for the standard bootcamp day, the grading scale and
the course policies, and :doc:`../software-architecture` for an overview of the subject.

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
3. Read an Architecture Decision Record, find the code that implements it, and judge whether they
   still agree.
4. Analyze the trade-offs of a decision, including the alternatives that were not chosen.
5. Write an ADR for a decision of their own.

Technical Prerequisites
-----------------------

- **Required:** at least two years of programming, or equivalent coursework, in any language.
- **Required:** reading Python well enough to follow a module, and Git for browsing history.
- **Required:** web application fundamentals: HTTP, databases, background jobs and caching.
- **Helpful:** Docker and Kubernetes concepts, Django, and a diagramming tool (draw.io,
  Structurizr, Mermaid or PlantUML).

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
     - **Lecture 1: What architecture is.** Decisions that are hard to reverse, quality attributes
       (scalability, security, maintainability, cost), trade-offs, and the role of the architect.
       A first look at Smarter: browser, CLI, API, workers, database, cache, model providers and
       Kubernetes.
   * - 2
     - 45
     - **Lab 1: Draw it.** In pairs, draw Smarter's C4 context and container diagrams, from the
       code, the Compose file and the docs. Produces Assignment 1.
   * - 3
     - 45
     - **Lecture 2: Architecture Decision Records.** Why record decisions, Nygard's format, and a
       guided reading of :doc:`ADR 001 on Django </adr/001-django>`,
       :doc:`ADR 005 on manifests </adr/005-manifests>` and
       :doc:`ADR 024 on the broker model </adr/024-broker-model>`.
   * - 4
     - 45
     - **Lab 2: Does the code agree?** Each student takes one ADR, finds the code that implements
       it, and judges whether the code still matches the decision. Produces Assignment 2.
   * - 5
     - 45
     - **Lecture 3: Styles and patterns.** Monolith, modular monolith and microservices; layered
       architecture; asynchronous work with queues; the
       :doc:`broker model </smarter-framework/smarter-broker-model>` as a pattern that turns
       declarative manifests into database rows.
   * - 6
     - 45
     - **Lecture 4: Cross-cutting decisions.** Caching (:doc:`ADR 018 </adr/018-caching>`), task
       queues (:doc:`ADR 030 </adr/030-task-queues>`), API versioning
       (:doc:`ADR 023 </adr/023-api-versioning>`), feature flags
       (:doc:`ADR 022 </adr/022-feature-flags>`) and Pydantic contracts
       (:doc:`ADR 031 </adr/031-pydantic-over-json>`).
   * - 7
     - 45
     - **Lab 3: Argue the opposite.** Teams take one ADR and argue for the alternative: what would
       Smarter look like, and what would it have cost? A short debate follows. Produces
       Assignment 3.
   * - 8
     - 45
     - **Lecture 5: Architecture for the cloud and for AI.** The twelve-factor app
       (:doc:`/smarter-framework/guides/12-factor-app`), Kubernetes, and the architecture of AI
       applications: tools, guardrails, and the decision to treat the model as untrusted.
   * - 9
     - 45
     - **Lab 4: Draft an ADR.** Draft an ADR for a decision in a project of your own. Ungraded.
   * - 10
     - 45
     - **Lecture 6: Evolving architecture.** Technical debt, fitness functions, migrations, and
       how architecture changes when coding agents write much of the code.
   * - 11
     - 30
     - **Capstone kickoff.** Students choose a capstone and its scope.

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

Assignment 3: The Road Not Taken
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Teams argue for the alternative to one ADR, and write up the case on both sides.

**Turn in:** a two-page position paper per team.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Alternative design
     - 6
     - Concrete: what would change in the system.
     - Vague ("use microservices").
   * - Trade-offs
     - 7
     - Costs and benefits on several quality attributes.
     - Benefits only.
   * - Fairness
     - 4
     - Acknowledges why the original decision was made.
     - Dismisses it.
   * - Writing
     - 3
     - Clear and concise.
     - Disorganized.

Capstone Projects
-----------------

Students choose one. Capstones are due one week after the bootcamp.

Capstone A: An Architecture Review of Smarter
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Carry out an architecture review of a real system against stated quality
attributes, and make evidence-based recommendations.

Students choose two quality attributes (for example scalability and maintainability) and review
Smarter against them, using the ADRs, the code and the deployment configuration. They identify
risks and sensitivity points, and recommend changes.

**What students turn in:**

- An architecture review document (five to seven pages) with C4 diagrams.
- Quality attribute scenarios ("when X happens, the system should Y within Z").
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
     - 20
     - Specific, measurable quality attribute scenarios.
     - Vague goals.
   * - Analysis
     - 25
     - Traces each scenario through the architecture, with evidence.
     - Opinions.
   * - Risks
     - 20
     - Ranked, with likelihood and impact.
     - Unranked.
   * - Recommendations
     - 20
     - Realistic, with a draft ADR.
     - Generic.
   * - Writing and diagrams
     - 15
     - Clear and accurate.
     - Unclear.

Capstone B: An Architecture for a New Feature
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Design a significant feature that fits an existing architecture, and record
the decisions it requires.

Students design a feature Smarter does not have, for example per-team model routing rules, a
scheduled report resource, or multi-region deployment. They place it in the existing architecture,
identify the decisions it needs, and write ADRs for the two most important.

**What students turn in:**

- A design document with C4 container and component diagrams.
- Two ADRs in the format of :doc:`/adr`.
- A list of the existing ADRs the design depends on, and how it respects them.

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
     - Uses existing patterns (brokers, manifests, tasks) where they apply.
     - Ignores the existing architecture.
   * - Design
     - 20
     - Complete, with responsibilities and interfaces.
     - Sketchy.
   * - ADRs
     - 25
     - Real decisions, alternatives and consequences.
     - Descriptions, not decisions.
   * - Dependencies on existing ADRs
     - 15
     - Correctly identified and respected.
     - Not considered.
   * - Diagrams and writing
     - 15
     - Clear.
     - Unclear.

Recommended Texts
-----------------

- **Pre-reading:** Michael Nygard, `Documenting Architecture Decisions
  <https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions>`__ (2011), and
  :doc:`ADR 000 </adr/000-intro>`.
- **Reference:** Mark Richards and Neal Ford, *Fundamentals of Software Architecture* (2nd edition,
  O'Reilly, 2025).
- **Smarter documentation:** :doc:`/adr`, :doc:`/smarter-framework/smarter-broker-model` and
  :doc:`/smarter-framework/guides/12-factor-app`.

Further Study
-------------

.. include:: further-study.txt
