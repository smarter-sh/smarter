Documentation with Sphinx: Classroom Bootcamp
=============================================

An eight-hour classroom bootcamp on writing high quality technical documentation with Sphinx and
reStructuredText, taught on Smarter's own documentation: more than a thousand pages that combine
hand-written guides, architecture decision records, and API references generated from Python
docstrings. Students improve a real page, write docstrings, and write an ADR. See
:doc:`../course-formats` for the standard bootcamp day, the grading scale and the course policies,
and :doc:`../sphinx-documentation` for an overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Developers, technical writers, and students in technical communication.
   * - **Deployment**
     - Each student has a fork and clone of the repository, with the Python virtual environment
       set up (``make init``). Building the full documentation takes about 20 minutes, so students
       build a small Sphinx project of their own in Lab 1, and check Smarter pages by previewing
       single files.
   * - **Cost**
     - Free.

Learning Objectives
-------------------

By the end of the bootcamp, students can:

1. Write reStructuredText: headings, lists, links, code blocks, tables, admonitions and
   cross-references.
2. Explain how a Sphinx project is organized: ``conf.py``, extensions, toctrees and the build.
3. Classify documentation by purpose (tutorial, how-to, reference, explanation) and write for one
   purpose at a time.
4. Write reStructuredText docstrings that autodoc renders as API reference.
5. Write an Architecture Decision Record.

Technical Prerequisites
-----------------------

- **Required:** the command line, and a text editor (Visual Studio Code with the reStructuredText
  extension is recommended).
- **Required:** Git: fork, clone, branch, commit, push and pull requests, and a GitHub account.
- **Required:** Python 3 installed, and creating a virtual environment.
- **Helpful:** reading Python (for the docstrings lab), Markdown, and experience writing for an
  audience.

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
     - **Lecture 1: Documentation as a product.** Who reads documentation, and why they give up.
       Docs as code: plain text, version control, review and CI. Diátaxis: tutorials, how-to
       guides, reference and explanation. A tour of ``docs/source/``.
   * - 2
     - 45
     - **Lab 1: Your first Sphinx project.** Run ``sphinx-quickstart``, write three pages with a
       toctree, cross-references, a code block and a note, and build them. Produces Assignment 1.
   * - 3
     - 45
     - **Lecture 2: reStructuredText in depth.** Heading levels, inline markup, ``:doc:`` and
       ``:ref:`` cross-references, ``list-table``, ``literalinclude``, and the common mistakes
       (short underlines, missing blank lines after directives).
   * - 4
     - 45
     - **Lab 2: Improve a page.** Find a page in Smarter's docs that is unclear, out of date or
       missing an example, and improve it. Produces Assignment 2.
   * - 5
     - 45
     - **Lecture 3: Writing clearly.** Audience and purpose, plain language, active voice, one idea
       per paragraph, examples that work, and evergreen prose that does not go stale with each
       release. :doc:`/smarter-framework/guides/documentation`.
   * - 6
     - 45
     - **Lecture 4: Docstrings and autodoc.** Sphinx autodoc, reStructuredText field lists
       (``:param:``, ``:returns:``, ``:raises:``), cross-references to Python objects, and
       :doc:`ADR 029 on docstrings </adr/029-docstrings>`.
   * - 7
     - 45
     - **Lab 3: Document a module.** Write or improve the docstrings of a small Smarter module,
       and render them with autodoc in the Lab 1 project. Produces Assignment 3.
   * - 8
     - 45
     - **Lecture 5: Architecture Decision Records.** Why record decisions, Michael Nygard's
       format, and a reading of two of Smarter's :doc:`ADRs </adr>`.
   * - 9
     - 45
     - **Lab 4: Draft an ADR.** Draft an ADR for a decision in a project of your own, and swap
       it with a neighbor for comments. Ungraded.
   * - 10
     - 45
     - **Lecture 6: Publishing and maintaining.** Read the Docs, building on every release,
       link checking, docs in code review, and keeping docs consistent with the code.
   * - 11
     - 30
     - **Capstone kickoff.** Students choose a capstone and outline it.

Graded Assignments
------------------

Assignment 1: A Small Sphinx Project
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students build a three-page Sphinx project about a topic they know well, with a toctree,
cross-references, a code block, a table and an admonition.

**Turn in:** a Git repository with the source, and the built HTML (or a screenshot of each page).

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
     - Warnings or errors.
   * - Markup
     - 6
     - Every required element used correctly.
     - Elements missing or broken.
   * - Structure
     - 5
     - Toctree and cross-references make it navigable.
     - Pages not linked.
   * - Writing
     - 4
     - Clear and purposeful.
     - Unfocused.

Assignment 2: An Improved Page
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students improve one page of Smarter's documentation, and explain what was wrong and why the change
helps.

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
     - Fixes an error, adds a missing example, or clarifies a confusing passage.
     - Cosmetic changes only.
   * - Accuracy
     - 5
     - Checked against the code; examples work.
     - Untested examples.
   * - Markup
     - 4
     - Valid; ``:doc:`` targets exist.
     - Broken links or markup.
   * - Pull request
     - 4
     - Explains the problem and the fix.
     - No description.

Assignment 3: Docstrings for a Module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students write the docstrings for a small module in Smarter's style, and show how autodoc renders
them.

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
     - Every public function and class, with parameters, returns and raises.
     - Some objects undocumented.
   * - Usefulness
     - 6
     - Explains why and when, not only what.
     - Restates the function name.
   * - Style
     - 4
     - Field lists and cross-references as in ADR 029; hooks pass.
     - Inconsistent.
   * - Rendering
     - 4
     - Renders without warnings.
     - Broken rendering.

Capstone Projects
-----------------

Students choose one. Capstones are due one week after the bootcamp.

Capstone A: A Tutorial for Smarter
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Write a tutorial that takes a newcomer from nothing to a working result, and
test it on a real reader.

Students write a new tutorial for Smarter's documentation, for example "Your first LLMClient with a
plugin and a guardrail", following the Diátaxis definition of a tutorial, with manifests that they
have verified, and test it on someone who has never used Smarter.

**What students turn in:**

- A pull request against their fork with the page, linked into a toctree.
- Notes from the user test: where the reader got stuck, and what was changed.
- A half-page note on the tutorial's audience and scope.

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
     - Learning by doing, one path, a visible result at each step.
     - A reference page with steps.
   * - Accuracy
     - 25
     - Every command and manifest works as written.
     - Steps fail.
   * - User test
     - 20
     - Real reader; problems found and fixed.
     - No test.
   * - Writing
     - 20
     - Clear, friendly and concise.
     - Wordy or confusing.
   * - Markup and integration
     - 15
     - Valid, linked, consistent with neighbors.
     - Orphaned or broken.

Capstone B: Documentation for Your Own Project
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Build and publish a complete documentation site for a project, covering all
four kinds of documentation.

Students set up Sphinx for a project of their own (or an open source project that lacks docs),
with a tutorial, a how-to guide, an explanation page, an API reference from docstrings, and an ADR,
and publish it on Read the Docs.

**What students turn in:**

- A repository with the docs source, configuration and docstrings.
- A link to the published site.
- A half-page note mapping each page to its Diátaxis category.

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
     - Each page serves one purpose well.
     - Pages mix purposes.
   * - API reference
     - 20
     - Generated from complete docstrings.
     - Sparse docstrings.
   * - ADR
     - 15
     - A real decision, with alternatives and consequences.
     - A description, not a decision.
   * - Published
     - 20
     - Builds on Read the Docs without warnings.
     - Not published.
   * - Writing
     - 20
     - Clear and consistent.
     - Inconsistent.

Recommended Texts
-----------------

- **Pre-reading:** `Diátaxis <https://diataxis.fr/>`__, the four short pages on tutorials, how-to
  guides, reference and explanation.
- **Reference:** Jared Bhatti, Zachary Sarah Corleissen, Jen Lambourne, David Nunez and Heidi
  Waterhouse, *Docs for Developers* (Apress, 2021).
- **Smarter documentation:** :doc:`/smarter-framework/guides/documentation` and
  :doc:`/adr/029-docstrings`.

Further Study
-------------

.. include:: further-study.txt
