Software Architecture: Two-Week Online Course
=============================================

A two-week online course on software architecture, taught on Smarter's thirty-one
:doc:`Architecture Decision Records </adr>` and the code that implements them, with six 30-minute
recorded lectures and a 90-minute live session each week. Week 1 covers describing and reading an
architecture, and week 2 covers styles, trade-offs and evolution. See :doc:`../course-formats` for
the format, the grading scale and the course policies, and :doc:`../software-architecture` for an
overview of the subject.

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
3. Verify ADRs against code, and recognize drift.
4. Compare architectural styles and patterns for a given problem.
5. Write ADRs, and plan the evolution of an architecture.

Technical Prerequisites
-----------------------

- **Required:** at least two years of programming, or equivalent coursework.
- **Required:** reading Python, and Git for browsing history.
- **Required:** web application fundamentals: HTTP, databases, background jobs and caching.
- **Helpful:** Docker and Kubernetes concepts, Django, and a diagramming tool.

Schedule
--------

.. list-table::
   :header-rows: 1
   :widths: 10 18 72

   * - Week
     - Item
     - Content
   * - 1
     - Lecture 1 (30 min)
     - **What architecture is.** Decisions, quality attributes and trade-offs; a first look at
       Smarter.
   * - 1
     - Lecture 2 (30 min)
     - **Describing architecture.** The C4 model, views, and diagrams as code.
   * - 1
     - Lecture 3 (30 min)
     - **Architecture Decision Records.** Nygard's format, and readings of
       :doc:`ADR 001 </adr/001-django>`, :doc:`ADR 005 </adr/005-manifests>` and
       :doc:`ADR 024 </adr/024-broker-model>`.
   * - 1
     - Live session 1 (90 min)
     - Groups draw Smarter's container diagram together, and compare. Start Assignment 1.
   * - 2
     - Lecture 4 (30 min)
     - **Styles and patterns.** Monoliths and microservices, layers, queues, and the
       :doc:`broker model </smarter-framework/smarter-broker-model>`.
   * - 2
     - Lecture 5 (30 min)
     - **Cross-cutting decisions.** Caching, task queues, versioning, feature flags and contracts,
       through Smarter's ADRs.
   * - 2
     - Lecture 6 (30 min)
     - **Evolving architecture.** The twelve-factor app, technical debt, fitness functions, and
       architecture when agents write code.
   * - 2
     - Live session 2 (90 min)
     - Capstone presentations (about 5 minutes each, with 2 minutes of questions).

Assignment 1 is due at the end of week 1, Assignment 2 in the middle of week 2, and Assignment 3
and the capstone at the start of Live session 2.

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

Assignment 3: The Road Not Taken
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students argue for the alternative to one ADR, with the costs and benefits on several quality
attributes, and the reasons the original choice was made.

**Turn in:** a two-page position paper.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Concrete alternative
     - 6
     - What would change, specifically.
     - Vague.
   * - Trade-offs
     - 7
     - Several attributes.
     - Benefits only.
   * - Fairness
     - 4
     - Original reasons acknowledged.
     - Dismissed.
   * - Writing
     - 3
     - Clear.
     - Disorganized.

Capstone Projects
-----------------

Students choose one, and present it in Live session 2.

Capstone A: An Architecture Review of Smarter
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Review a real system against stated quality attributes, and recommend
changes with evidence.

Students review Smarter against two quality attributes with scenarios, trace them through the
architecture, rank the risks, and draft an ADR for the most important recommendation.

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

Students design a feature Smarter does not have, place it in the architecture with C4 diagrams,
and write ADRs for its two most important decisions.

**What students turn in:**

- A design document with diagrams, and two ADRs.
- A list of the existing ADRs it depends on.
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
     - Uses existing patterns.
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
  <https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions>`__ (2011), in week 1.
- **Reference:** John Ousterhout, *A Philosophy of Software Design* (2nd edition, Yaknyam Press,
  2021).
- **Smarter documentation:** :doc:`/adr`, :doc:`/smarter-framework/smarter-broker-model` and
  :doc:`/smarter-framework/guides/12-factor-app`.

Further Study
-------------

.. include:: further-study.txt
