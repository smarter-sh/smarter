ADR-025: Django Templates
=========================

Status
------
Accepted

Context
-------
Template engines are used to render dynamic content in web applications. Django provides a powerful and flexible built-in templating engine that integrates seamlessly with the rest of the framework.

Decision
--------
The project exclusively uses Django's built-in templating engine.

Alternatives Considered
-----------------------
- Using third-party template engines (e.g., Jinja2, Mako).
- Mixing multiple template engines within the project.

Consequences
------------
- **Positive:**
  - Ensures consistency and maintainability across all templates.
  - Simplifies onboarding and reduces cognitive overhead for contributors.
  - Leverages Django’s robust template features and security.
- **Negative:**
  - Limits flexibility to use features unique to other template engines.

Related ADRs
------------
- [ADR-000: Introduction](000-intro)
