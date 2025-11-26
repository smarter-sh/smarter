ADR-023: API Versioning
=======================

Status
------
Accepted

Context
-------
Consistent API versioning is essential for clarity, compatibility, and communication with users and integrators. Aligning API versions with the repository’s semantic versioning ensures transparency and reduces confusion.

Decision
--------
API version should be synced to the repo semantic version, exclusively and without exception.

Alternatives Considered
-----------------------
- Managing API versioning independently from the repository version.
- Using ad-hoc or manual versioning schemes.

Consequences
------------
- **Positive:**
  - Ensures consistency between API and repository versions.
  - Simplifies version management and communication.
  - Reduces risk of versioning confusion for users and integrators.
- **Negative:**
  - Requires strict discipline to maintain version alignment.
  - May limit flexibility for decoupling API and repo versioning in the future.

Related ADRs
------------
- [ADR-000: Introduction](000-intro)
