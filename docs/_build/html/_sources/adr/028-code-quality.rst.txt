ADR-028: Code Quality
=====================

Status
------
Accepted

Context
-------
Maintaining high code quality is essential for reliability, maintainability, and collaboration. Automated tools help enforce code style, formatting, and best practices across the codebase.

Decision
--------
We manage code quality with pre-commit. See `./pre-commit-config.yaml` for the complete list of tools. Additionally, see `./pyproject.toml` for specific configurations for black, isort, and other code formatting and style enforcement tools.

Developers are expected to initialize pre-commit using `make init` and ensure that all code linters, formatters, and style enforcement tools have run successfully before creating pull requests.

**DO NOT INDISCRIMINATELY DISABLE RULES WITH COMMENT DIRECTIVES**

Alternatives Considered
-----------------------
- Relying on manual code reviews for style and formatting.
- Allowing contributors to use their own preferred tools and configurations.

Consequences
------------
- **Positive:**
  - Ensures consistent code style and quality across the project.
  - Reduces manual review effort and catches issues early.
  - Simplifies onboarding for new contributors.
- **Negative:**
  - Requires contributors to set up and use pre-commit locally.
  - May require updates to pre-commit hooks and configurations as tools evolve.

Related ADRs
------------
- [ADR-000: Introduction](000-intro)
