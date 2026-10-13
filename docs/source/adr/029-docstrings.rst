ADR 029: Docstring Style
=======================================================================

Context
-------

Our codebase uses Django with strong type hints, Pydantic models for data validation, and Django REST Framework (DRF) for API development. Consistent and clear documentation is essential for maintainability, onboarding, and effective collaboration, especially as type annotations and third-party integrations become more prevalent.

Docstrings also have a second reader: Sphinx autodoc renders them as the technical reference on docs.smarter.sh. A docstring is therefore reStructuredText, whatever its field style, and it cross-references other objects with Sphinx roles such as ``:class:`` and ``:meth:``.

Alternatives Considered
-----------------------

- **No Standard Docstring Style:** Leads to inconsistent documentation and confusion.
- **reStructuredText (Sphinx) Style:** Sphinx's native field lists. Rendered by autodoc without an extension, and consistent with the reST markup that the rest of a docstring already uses.
- **NumPy Style:** Popular in scientific computing, but more complex than necessary for our needs.
- **Google Style:** Clean and concise, but it needs the napoleon extension, and mixes a second syntax into otherwise reST docstrings.

Decision
--------

Adopt the **reStructuredText field list** docstring format for all Python code, including Django models, views, DRF serializers, and Pydantic models.

- Use type hints in function signatures. ``sphinx_autodoc_typehints`` renders them, so ``:type:`` and ``:rtype:`` are needed only where an annotation is missing.
- Document parameters with ``:param name:``, the return value with ``:returns:``, and exceptions with ``:raises SomeError:``.
- Leverage field descriptions in Pydantic models where appropriate.
- Ensure docstrings are concise and focused on intent and usage.
- pydocstringformatter, a pre-commit hook, enforces the layout: an opening ``"""`` on its own line, then a one-line summary that ends with a period.

Example:

.. code-block:: python

    def create_user(username: str, email: str) -> User:
        """
        Create a new user.

        :param username: The user's username.
        :param email: The user's email address.
        :returns: The created user instance.
        :raises ValueError: If the username is invalid.
        """

The napoleon extension stays enabled, so the older docstrings that use Google style (``Args:``, ``Returns:``) still render. New and edited code uses reST fields.

Consequences
------------

**Positive:**

- Improves readability and consistency across the codebase.
- Docstrings render in Sphinx without translation, in the same syntax as their cross-references and code blocks.
- Matches the code: reST fields are the large majority of the codebase's docstrings.

**Negative:**

- Requires discipline to maintain consistency.
- Some legacy docstrings use Google style, and are converted when they are edited.

References
----------

- `Sphinx: Info field lists <https://www.sphinx-doc.org/en/master/usage/domains/python.html#info-field-lists>`_
- `sphinx-autodoc-typehints <https://github.com/tox-dev/sphinx-autodoc-typehints>`_
- Related ADRs: None
