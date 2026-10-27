Creating High Quality Documentation with Sphinx
===============================================

**Why Smarter.** Documentation is usually taught on a toy project with three pages, so students
never face the real problems: keeping hundreds of pages consistent, generating reference from code
without it going stale, checking links quickly, and writing for readers who arrive from a search
engine. This documentation, published at `docs.smarter.sh <https://docs.smarter.sh>`__ from
`docs/source/ <https://github.com/smarter-sh/smarter/tree/main/docs/source>`__, is itself a large
Sphinx project that has all of them:

- **More than nine hundred pages.** Hand-written guides for every resource, the platform and the
  framework, which follow one pattern (see the
  `Guardrail page <https://github.com/smarter-sh/smarter/blob/main/docs/source/smarter-resources/smarter-guardrail.rst>`__),
  thirty-one :doc:`Architecture Decision Records </adr>`, these instructor course plans, and more
  than five hundred pages of API reference.
- **Reference generated from the code.** Autodoc publishes reStructuredText docstrings, with
  ``sphinxcontrib_django`` for Django models, ``autodoc_pydantic`` for Pydantic models and
  ``sphinx_autodoc_typehints`` for type hints, all configured in
  `conf.py <https://github.com/smarter-sh/smarter/blob/main/docs/source/conf.py>`__.
- **Examples that are real files.** Manifests are kept in
  `example-manifests/ <https://github.com/smarter-sh/smarter/tree/main/docs/source/example-manifests>`__
  and included with ``literalinclude``, so an example in the docs is the same file that a reader
  can apply.
- **A pipeline that keeps up.** Read the Docs builds every release from
  `.readthedocs.yml <https://github.com/smarter-sh/smarter/blob/main/.readthedocs.yml>`__, the
  pydocstringformatter and codespell hooks check every commit, and a
  `script <https://github.com/smarter-sh/smarter/blob/main/skills/smarter-sphinx-docs/scripts/check-docs.sh>`__
  checks every link and autodoc target in seconds, because the full build takes twenty minutes.
- **Written rules.** Evergreen prose with no "what's new" sections, terms defined on first use,
  valid manifests in every example, and docs updated in the same change as the code, as the
  `smarter-sphinx-docs <https://github.com/smarter-sh/smarter/blob/main/skills/smarter-sphinx-docs/SKILL.md>`__
  and `smarter-docstrings <https://github.com/smarter-sh/smarter/blob/main/skills/smarter-docstrings/SKILL.md>`__
  skills set out.
- **A new kind of reader.** The documentation is written as much for coding agents as for people,
  and ``CLAUDE.md`` and the Agent Skills are documentation whose only reader is an agent.

Students can contribute to it on their first day, and see their page published.

**What the course covers.** Documentation as a product, and who reads it; docs as code: plain
text, version control, review and CI; reStructuredText: markup, directives, roles, tables and
includes; Sphinx: ``conf.py``, extensions, toctrees, themes and the build; the four kinds of
documentation in Diátaxis; writing clearly, with examples that work and evergreen prose; testing
documentation on readers; docstrings, autodoc and generated reference for Django and Pydantic
models; Architecture Decision Records; publishing on Read the Docs; maintenance, link checking and
ownership; and writing for coding agents.

**Look at.**

- `docs/source/ <https://github.com/smarter-sh/smarter/tree/main/docs/source>`__ and its
  `conf.py <https://github.com/smarter-sh/smarter/blob/main/docs/source/conf.py>`__.
- The reStructuredText docstrings in any Python module, such as
  `safe_http.py <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/llmtool/plugin/safe_http.py>`__,
  and the pages that autodoc builds from them.
- `docs/source/adr/ <https://github.com/smarter-sh/smarter/tree/main/docs/source/adr>`__, the
  decision records.

Each course plan lists every file that it uses under *Smarter in the Source Code*.

**Read.** :doc:`/smarter-framework/guides/documentation`, :doc:`ADR 029 on docstrings
</adr/029-docstrings>`, :doc:`/adr`, `Part 3: What Claude Code Actually Reads
<https://blog.smarter.sh/2026/10/17/claude-code-data-sources/>`__.

**Exercises.**

- Find a page that is unclear or out of date, and improve it in a pull request.
- Write an Architecture Decision Record for a decision of their own, following the existing ones.
- Write the docstrings for a module, and see how autodoc renders them.
- Run ``check-docs.sh`` on a page, break one of its links on purpose, and see the check catch it.

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
