Creating High Quality Documentation with Sphinx
===============================================

**Why Smarter.** This documentation is itself a large Sphinx project, with more than a thousand
pages, that combines hand-written guides, architecture decision records, and API references
generated from Python docstrings by autodoc, and is published to Read the Docs at every release.
Students can contribute to it on their first day.

**Look at.** ``docs/source/``, its ``conf.py``, and the reStructuredText docstrings in any Python
module.

**Read.** :doc:`/smarter-framework/guides/documentation`, :doc:`ADR 029 on docstrings </adr/029-docstrings>`.

**Exercises.**

- Find a page that is unclear or out of date, and improve it in a pull request.
- Write an Architecture Decision Record for a decision of their own, following the existing ones.
- Write the docstrings for a module, and see how autodoc renders them.

**Course plans.** Three complete, ready-to-teach plans, each with a schedule, graded assignments
and rubrics, two capstone projects, recommended texts, further study and technical prerequisites.
See :doc:`course-formats` for what the formats have in common.

.. toctree::
   :maxdepth: 1

   Classroom bootcamp: 8 hours <sphinx-documentation/bootcamp>
   Two-week online course: 6 hours <sphinx-documentation/two-week>
   Four-week online course: 12 hours <sphinx-documentation/four-week>

See the :doc:`Smarter Instructor Guide </smarter-instructor>` to install Smarter and set up
a class.
