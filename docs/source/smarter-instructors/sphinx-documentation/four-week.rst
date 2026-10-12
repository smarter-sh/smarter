Documentation with Sphinx: Four-Week Online Course
==================================================

A four-week online course on writing high quality technical documentation with Sphinx and
reStructuredText, taught on Smarter's own documentation, with twelve 30-minute recorded lectures
and a 90-minute live session each week. Week 1 covers Sphinx and reStructuredText, week 2 the four
kinds of documentation, week 3 API reference and decision records, and week 4 publishing,
maintenance and documentation for AI-assisted development. See :doc:`../course-formats` for the
format, the grading scale and the course policies, and :doc:`../sphinx-documentation` for an
overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Developers, technical writers, and students in technical communication.
   * - **Deployment**
     - Each student has a fork and clone of the repository, and a small Sphinx project of their own.
       Students who will run code examples install Smarter from the Quick Start or from source.
   * - **Workload**
     - 3 hours of instruction and 4 to 6 hours of assignments each week.
   * - **Cost**
     - Free.

Learning Objectives
-------------------

By the end of the course, students can:

1. Write correct reStructuredText, and configure and extend a Sphinx project.
2. Write tutorials, how-to guides, reference and explanation, each for its purpose.
3. Write clear, accurate, evergreen technical prose, and test it on readers.
4. Write docstrings that autodoc renders as API reference, and ADRs that record decisions.
5. Publish documentation, and keep it accurate with links checks, reviews and CI.
6. Write documentation that AI coding agents can use, such as ``CLAUDE.md`` files and Agent
   Skills.

Technical Prerequisites
-----------------------

- **Required:** the command line and a text editor.
- **Required:** Git and GitHub, including pull requests.
- **Required:** Python 3, and virtual environments.
- **Helpful:** reading Python, Markdown, YAML, and Docker for running examples.

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
     - **Documentation as a product.** Readers, docs as code, and a tour of ``docs/source/``.
   * - 1
     - Lecture 2
     - **reStructuredText.** Markup, directives, roles, tables, includes, and common mistakes.
   * - 1
     - Lecture 3
     - **Sphinx.** ``conf.py``, extensions (autodoc, sphinx-design, copybutton), toctrees, themes
       and the build.
   * - 1
     - Live session 1
     - Live setup of a Sphinx project. Start Assignment 1.
   * - 2
     - Lecture 4
     - **Diátaxis.** Tutorials, how-to guides, reference and explanation.
   * - 2
     - Lecture 5
     - **Writing clearly.** Audience, plain language, structure, examples, and evergreen prose.
       :doc:`/smarter-framework/guides/documentation`.
   * - 2
     - Lecture 6
     - **Testing documentation.** User tests, checking examples, and editing.
   * - 2
     - Live session 2
     - Review of Assignment 1. Pairs classify Smarter pages by Diátaxis. Start Assignment 2.
   * - 3
     - Lecture 7
     - **Docstrings and autodoc.** Field lists, cross-references, and
       :doc:`ADR 029 </adr/029-docstrings>`.
   * - 3
     - Lecture 8
     - **Generated reference.** Autodoc for Django models and Pydantic models, and Swagger for
       APIs.
   * - 3
     - Lecture 9
     - **Architecture Decision Records.** Nygard's format, and Smarter's :doc:`ADRs </adr>`.
   * - 3
     - Live session 3
     - Review of Assignment 2. Live docstring editing and rendering. Capstone proposals
       discussed. Start Assignment 3.
   * - 4
     - Lecture 10
     - **Publishing.** Read the Docs, versions, search, and analytics.
   * - 4
     - Lecture 11
     - **Maintenance.** Link checking, docs in review and CI, deprecations, and ownership.
   * - 4
     - Lecture 12
     - **Writing for agents.** ``CLAUDE.md`` and the Agent Skills in ``skills/``: documentation
       whose reader is a coding agent, and what it shares with documentation for people.
       :doc:`/smarter-framework/developer-reference/agentic-development`.
   * - 4
     - Live session 4
     - Capstone presentations (about 6 minutes each, with 2 minutes of questions), and a course
       retrospective.

Assignments 1 to 3 are due before the next live session. Assignment 4 is due in the middle of week
4. The capstone proposal is due before Live session 3, and the capstone at the start of Live
session 4.

Graded Assignments
------------------

Assignment 1: A Small Sphinx Project
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students build a Sphinx project of four pages with a toctree, cross-references, a code block, a
``list-table``, an admonition, an include, and one extension of their choice.

**Turn in:** a repository with the source and the built HTML.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Builds cleanly
     - 5
     - No warnings.
     - Warnings.
   * - Markup
     - 6
     - Every element correct.
     - Missing or broken.
   * - Extension
     - 4
     - Configured and used well.
     - Configured but unused.
   * - Writing
     - 5
     - Clear and purposeful.
     - Unfocused.

Assignment 2: An Improved Page, Tested on a Reader
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students improve a Smarter how-to or tutorial page, test it with a reader before and after, and
report what changed.

**Turn in:** a pull request against their fork, and the user test notes.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Improvement
     - 6
     - Substantive.
     - Cosmetic.
   * - User tests
     - 6
     - Before and after, with observations.
     - None.
   * - Accuracy
     - 4
     - Examples tested.
     - Untested.
   * - Markup
     - 4
     - Valid.
     - Broken.

Assignment 3: Docstrings and an Autodoc Page
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students write the docstrings for a module, and the autodoc page that publishes it, following
Smarter's technical reference pages.

**Turn in:** a pull request against their fork, and a screenshot of the rendered page.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Completeness
     - 6
     - Every public object.
     - Gaps.
   * - Usefulness
     - 6
     - Why and when.
     - Restates names.
   * - Autodoc page
     - 4
     - Follows the existing reference pages.
     - Inconsistent.
   * - Rendering
     - 4
     - No warnings.
     - Broken.

Assignment 4: An ADR
~~~~~~~~~~~~~~~~~~~~

Students write an ADR for a real decision, with context, alternatives and consequences.

**Turn in:** the ADR in reStructuredText.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Context
     - 5
     - Clear forces and constraints.
     - Missing.
   * - Decision
     - 4
     - Stated plainly.
     - Buried.
   * - Alternatives
     - 6
     - Fairly compared.
     - None.
   * - Consequences
     - 5
     - Good and bad.
     - Benefits only.

Capstone Projects
-----------------

Students choose one, propose it before Live session 3, and present it in Live session 4.

Capstone A: A Documentation Set for a Smarter Feature
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Plan and write complete documentation for a real feature, covering every
kind of documentation its readers need.

Students choose a Smarter feature whose documentation is thin (ask the maintainers in GitHub
Discussions), interview a user or maintainer, and write a tutorial, a how-to guide, an explanation
and improved docstrings, all woven into the existing pages rather than added as a separate
section.

**What students turn in:**

- A pull request against their fork, ideally offered upstream.
- A documentation plan: readers, their tasks, and which page serves each.
- User test notes, and a six-minute presentation.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Plan
     - 15
     - Readers and tasks drive the pages.
     - Pages without a plan.
   * - Four kinds
     - 25
     - Each page serves one purpose well.
     - Mixed purposes.
   * - Accuracy
     - 20
     - Verified against the code.
     - Unverified.
   * - Integration
     - 20
     - Woven into existing pages; links and markup valid.
     - Separate silo.
   * - User test and presentation
     - 20
     - Real reader; clear presentation.
     - None.

Capstone B: Documentation for People and Agents
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Document a project for both human contributors and AI coding agents, and
test both.

Students take a project of their own and write a Sphinx site for people (tutorial, how-to,
explanation, API reference, an ADR) and agent instructions (a ``CLAUDE.md`` and one Agent Skill),
modeled on Smarter's. They test the site on a human reader and the instructions on a coding agent
given a real task.

**What students turn in:**

- A repository with the docs, ``CLAUDE.md`` and skill, and a link to the published site.
- Test notes from both the human and the agent test, and the changes made.
- A six-minute presentation.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Human docs
     - 25
     - Four kinds, clear and published.
     - Partial.
   * - Agent docs
     - 20
     - Concise, specific, and consistent with the human docs.
     - Generic advice.
   * - Human test
     - 15
     - Real reader; changes made.
     - None.
   * - Agent test
     - 20
     - Real task; instructions improved from the result.
     - None.
   * - Presentation
     - 20
     - Compares writing for people and for agents.
     - Superficial.

Recommended Texts
-----------------

- **Required:** Jared Bhatti, Zachary Sarah Corleissen, Jen Lambourne, David Nunez and Heidi
  Waterhouse, *Docs for Developers* (Apress, 2021), across weeks 1 to 4.
- **Required:** `Diátaxis <https://diataxis.fr/>`__, in week 2.
- **Required:** Anne Gentle, *Docs Like Code* (3rd edition, self-published, 2022), in week 4.
- **Reference:** the `Google developer documentation style guide <https://developers.google.com/style>`__,
  and Cyrille Martraire, *Living Documentation* (Addison-Wesley, 2019).
- **Smarter documentation:** :doc:`/smarter-framework/guides/documentation`,
  :doc:`/adr/029-docstrings`, :doc:`/adr` and
  :doc:`/smarter-framework/developer-reference/agentic-development`.

Further Study
-------------

.. include:: further-study.txt
