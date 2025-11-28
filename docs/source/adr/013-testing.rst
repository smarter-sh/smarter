ADR-013: Testing
================

Status
------
Accepted

Context
-------
Consistent and maintainable unit testing is essential for code quality and reliability. Using a common base class for tests ensures shared setup, teardown, and utility methods, while mixins allow for reusable test behaviors across different test cases.

Decision
--------
All unit tests should subclass `SmarterTestBase` from `smarter.lib.unittest.base_classes`. Where applicable, tests should also leverage `TestAccountMixin` from `smarter.apps.account.tests.mixins` to provide account-related test utilities.

Alternatives Considered
-----------------------
- Allowing tests to subclass arbitrary or custom base classes.
- Duplicating setup and utility logic across test files.

Consequences
------------
- **Positive:**
  - Promotes consistency and reuse in test code.
  - Reduces duplication and boilerplate in test setup.
  - Simplifies onboarding for new contributors.
- **Negative:**
  - Requires contributors to learn and use the shared base classes and mixins.
  - May require refactoring of existing tests to conform.

Related ADRs
------------
- [ADR-000: Introduction](000-intro)
