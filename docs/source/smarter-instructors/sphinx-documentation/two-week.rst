Documentation with Sphinx: Two-Week Online Course
=================================================

A two-week online course on writing high quality technical documentation with Sphinx and
reStructuredText, taught on Smarter's own documentation, with six 30-minute recorded lectures and a
90-minute live session each week. Week 1 covers Sphinx, reStructuredText and writing, and week 2
covers docstrings, ADRs and publishing. See :doc:`../course-formats` for the format, the grading
scale and the course policies, and :doc:`../sphinx-documentation` for an overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Developers, technical writers, and students in technical communication.
   * - **Deployment**
     - Each student has a fork and clone of the repository with the virtual environment set up,
       and a small Sphinx project of their own for building quickly. The full Smarter docs build
       takes about 20 minutes; students may run it once, overnight.
   * - **Workload**
     - 3 hours of instruction and 4 to 6 hours of assignments each week.
   * - **Cost**
     - Free.

Learning Objectives
-------------------

By the end of the course, students can:

1. Write correct reStructuredText, and organize a Sphinx project.
2. Classify documentation by purpose, and write each kind well.
3. Write clear, accurate, evergreen technical prose.
4. Write docstrings that autodoc renders as API reference.
5. Write ADRs, and publish documentation on Read the Docs.

Technical Prerequisites
-----------------------

- **Required:** the command line and a text editor.
- **Required:** Git and GitHub, including pull requests.
- **Required:** Python 3, and virtual environments.
- **Helpful:** reading Python, and Markdown.

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
     - **Documentation as a product.** Readers, docs as code, Diátaxis, and a tour of
       ``docs/source/``.
   * - 1
     - Lecture 2 (30 min)
     - **Sphinx and reStructuredText.** ``conf.py``, extensions, toctrees, markup,
       cross-references, tables and includes.
   * - 1
     - Lecture 3 (30 min)
     - **Writing clearly.** Audience, plain language, examples that work, and evergreen prose.
       :doc:`/smarter-framework/guides/documentation`.
   * - 1
     - Live session 1 (90 min)
     - Live edit of a Smarter page, then pairs critique two pages against Diátaxis. Start
       Assignment 1.
   * - 2
     - Lecture 4 (30 min)
     - **Docstrings and autodoc.** Field lists, cross-references to Python objects, and
       :doc:`ADR 029 </adr/029-docstrings>`.
   * - 2
     - Lecture 5 (30 min)
     - **Architecture Decision Records.** Nygard's format and Smarter's :doc:`ADRs </adr>`.
   * - 2
     - Lecture 6 (30 min)
     - **Publishing and maintenance.** Read the Docs, link checking, docs in review, and keeping
       docs consistent with code.
   * - 2
     - Live session 2 (90 min)
     - Capstone presentations (about 5 minutes each, with 2 minutes of questions).

Assignment 1 is due at the end of week 1, Assignment 2 in the middle of week 2, and Assignment 3
and the capstone at the start of Live session 2.

Graded Assignments
------------------

Assignment 1: An Improved Page
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students improve one page of Smarter's documentation (an error, a missing example, a confusing
passage), verified against the code.

**Turn in:** a pull request against their fork.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Real improvement
     - 7
     - Substantive.
     - Cosmetic.
   * - Accuracy
     - 5
     - Examples tested.
     - Untested.
   * - Markup
     - 4
     - Valid; targets exist.
     - Broken.
   * - Pull request
     - 4
     - Problem and fix explained.
     - No description.

Assignment 2: Docstrings for a Module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students write the docstrings for a small module in Smarter's style, and render them with autodoc
in a small Sphinx project.

**Turn in:** a pull request against their fork, and a screenshot.

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
     - Why and when, not only what.
     - Restates names.
   * - Style
     - 4
     - Follows ADR 029; hooks pass.
     - Inconsistent.
   * - Rendering
     - 4
     - No warnings.
     - Broken.

Assignment 3: An ADR
~~~~~~~~~~~~~~~~~~~~

Students write an ADR for a real decision, either in a project of their own or one already made in
Smarter that has no ADR (for example a choice of library visible in the code).

**Turn in:** the ADR in reStructuredText, in the format of :doc:`/adr`.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Context
     - 5
     - The forces and constraints are clear.
     - Missing context.
   * - Decision
     - 4
     - Stated plainly.
     - Buried.
   * - Alternatives
     - 6
     - Two or more, fairly compared.
     - None.
   * - Consequences
     - 5
     - Good and bad consequences.
     - Benefits only.

Capstone Projects
-----------------

Students choose one, and present it in Live session 2.

Capstone A: A Tutorial for Smarter
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Write a tutorial that takes a newcomer to a working result, and test it on a
real reader.

Students write a new tutorial for Smarter's docs, with verified manifests, test it on a newcomer,
and revise it.

**What students turn in:**

- A pull request against their fork, linked into a toctree.
- User test notes and changes made.
- A five-minute presentation.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Tutorial form
     - 20
     - One path, visible results.
     - Reference with steps.
   * - Accuracy
     - 25
     - Everything works as written.
     - Steps fail.
   * - User test
     - 20
     - Real reader; fixes made.
     - None.
   * - Writing
     - 20
     - Clear and concise.
     - Wordy.
   * - Integration and presentation
     - 15
     - Linked, valid; clear presentation.
     - Orphaned.

Capstone B: Documentation for Your Own Project
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Build and publish a complete documentation site covering all four kinds of
documentation.

Students set up Sphinx for a project of their own, with a tutorial, a how-to, an explanation, an
API reference from docstrings and an ADR, published on Read the Docs.

**What students turn in:**

- A repository and a link to the published site.
- A Diátaxis mapping of the pages.
- A five-minute presentation.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Four kinds of docs
     - 25
     - Each serves one purpose.
     - Mixed.
   * - API reference
     - 20
     - Complete docstrings.
     - Sparse.
   * - ADR
     - 15
     - Real decision with alternatives.
     - Description only.
   * - Published
     - 20
     - Builds cleanly.
     - Not published.
   * - Writing and presentation
     - 20
     - Clear.
     - Inconsistent.

Recommended Texts
-----------------

- **Required:** Jared Bhatti, Zachary Sarah Corleissen, Jen Lambourne, David Nunez and Heidi
  Waterhouse, *Docs for Developers* (Apress, 2021). Week 1: chapters 1 to 5. Week 2: chapters 6
  to 11.
- **Required:** `Diátaxis <https://diataxis.fr/>`__, in week 1.
- **Reference:** the `Google developer documentation style guide <https://developers.google.com/style>`__.
- **Smarter documentation:** :doc:`/smarter-framework/guides/documentation` and
  :doc:`/adr/029-docstrings`.

Further Study
-------------

.. include:: further-study.txt
