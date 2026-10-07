Documentation Style Guide & Technical Reference
================================================

.. warning::

    **It doesn't matter how good your code is if no one knows how to use it!**


Good documentation is paramount to our mission of making enterprise-grade software that is
both useful and accessible to all users. The Smarter Project uses `Sphinx <https://www.sphinx-doc.org/en/master/>`__
as the documentation engine, with all eventual documentation being written in `reStructuredText (reST) <https://docutils.sourceforge.io/rst.html>`__.


Style Guide
--------------

A docstring should exist for every module, class, function, method, property, constant, and module-level variable; even when said
element's purpose might seem 'obvious' to it's author. Docstrings should be written with the following conventions in mind:

- Docstrings should use triple double-quote marks (""" """) even for one-liners.
- Use proper English grammar and spelling. Keep your vocabulary simple and clear. Don't use complex words where simple ones will do.
- Keep it simple and direct. Avoid unnecessary content, simply for the sake of 'filling space'.
- The overall content should conform to the `Google Python Style Guide <https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings>`__
- The first line should be a short, ideally 1-line, description of the element's purpose. Less is more: be concise and to the point.
- If more details are merited, add a 'Features' list immediately below the first line.
- For functions and methods, include comprehensive `Args:`, `Returns:`, and `Raises:` sections as needed.
- Include examples where appropriate, using the `doctest <https://docs.python.org/3/library/doctest.html>`__ format.
- Use `Sphinx directives <https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html>`__  like 'seealso' and 'doc' to create clickable cross-references to related elements inside the code.
- If merited, use callouts to highlight important concepts:

  .. note::

     This is a note callout.

  .. warning::

     This is a warning callout.

  .. tip::

     This is a tip callout.

  .. caution::

     This is a caution callout.

  .. important::

     This is an important callout.

  .. danger::

     This is a danger callout.

Tips for Writing Good Documentation
--------------------------------------

- Modules should have their own dedicated documentation page, which should include a brief human-readable
  overview of the module's purpose, as well as a Sphinx-generated 'automodule' directive that generates
  a complete set of reference documentation for all code elements within the module.

- Given effective prompting, LLM's like `GitHub Copilot <https://github.com/features/copilot>`__ and other AI tools
  can be a great help when initially drafting docstrings as these tend to follow fairly standard patterns. However,
  always review and edit any AI-generated content to ensure accuracy and clarity.

- **Awareness of Audience**: Always keep in mind who the intended audience is for the documentation. Tailor the
  content and level of detail accordingly, whether it's for end-users, developers, devops and cloud engineers, or other stakeholders.

- **Consistency**: Refer the existing body of documentation in `Read the Docs <https://docs.smarter.sh/>`__
  to ensure that your writing style, terminology, and formatting are consistent with the rest of the project.
  You should acquaint yourself with the existing documentation (see `https://github.com/smarter-sh/smarter/docs/source <https://github.com/smarter-sh/smarter/tree/main/docs/source>`__)
  structure and conventions before adding new content.

- **Use Visual Aids**: Where appropriate, include diagrams, screenshots, or code snippets to illustrate complex concepts or workflows.


Documentation Build Process
----------------------------

.. code-block:: bash

   # From the root of the Smarter Project repository
   cd docs
   make html

This will generate the HTML documentation files in the `docs/build/html` directory, which can be
opened in any web browser for review. The main entry point is `docs/build/html/index.html`.
