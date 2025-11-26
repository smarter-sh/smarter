ADR-012: Error Handling
=======================

Status
------
Accepted

Context
-------
Consistent error handling is critical for maintainability, debugging, and user experience. Using a unified exception hierarchy ensures that all exceptions are handled in a predictable and centralized manner.

Decision
--------
Exceptions should exclusively be subclassed from `smarter.common.exceptions`, without exception.

Alternatives Considered
-----------------------
- Allowing exceptions to be subclassed from Python’s built-in exceptions or other libraries.
- Using ad-hoc exception classes in different modules.

Consequences
------------
- **Positive:**
  - Ensures consistency and predictability in error handling.
  - Simplifies debugging and logging.
  - Centralizes exception management for easier maintenance.
- **Negative:**
  - Requires all contributors to follow the exception subclassing rule.
  - May require refactoring of existing exception handling code.

Related ADRs
------------
- [ADR-000: Introduction](000-intro)
