ADR 029: Docstring Style
=======================================================================

Context
-------

Our codebase uses Django with strong type hints, Pydantic models for data validation, and Django REST Framework (DRF) for API development. Consistent and clear documentation is essential for maintainability, onboarding, and effective collaboration, especially as type annotations and third-party integrations become more prevalent.

Alternatives Considered
-----------------------

- **No Standard Docstring Style:** Leads to inconsistent documentation and confusion.
- **reStructuredText (Sphinx) Style:** Verbose and less readable for everyday development.
- **NumPy Style:** Popular in scientific computing, but more complex than necessary for our needs.
- **Google Style:** Clean, concise, and widely supported by tools and IDEs.

Decision
--------

Adopt the **Google style** docstring format for all Python code, including Django models, views, DRF serializers, and Pydantic models.

- Use type hints in function signatures.
- Document parameters, return values, and exceptions using Google style.
- Leverage field descriptions in Pydantic models where appropriate.
- Ensure docstrings are concise and focused on intent and usage.

Example:

    def create_user(username: str, email: str) -> User:
        """Create a new user.

        Args:
            username (str): The user's username.
            email (str): The user's email address.

        Returns:
            User: The created user instance.

        Raises:
            ValueError: If the username is invalid.
        """

Consequences
------------

**Positive:**
- Improves readability and consistency across the codebase.
- Enhances IDE support and documentation generation (e.g., Sphinx with napoleon).
- Eases onboarding for new developers familiar with Google style.

**Negative:**
- Requires discipline to maintain consistency.
- Some legacy code may need to be updated to match the new style.

References
----------

- `Google Python Style Guide: Docstrings <https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings>`_
- `Sphinx Napoleon Extension <https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html>`_
- Related ADRs: None
