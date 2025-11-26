ADR-017: Database
=================

Status
------
Accepted

Context
-------
Supporting multiple database backends can increase complexity and maintenance overhead. Django provides built-in support for several SQL databases, ensuring stability and compatibility.

Decision
--------
We limit support for SQL databases to those directly supported by Django. Moreover, we want to avoid adding code that is specific to a single database vendor's feature. We prefer MySQL, and this is our default database.

Alternatives Considered
-----------------------
- Supporting additional databases through third-party packages.
- Implementing vendor-specific features or optimizations.

Consequences
------------
- **Positive:**
  - Simplifies maintenance and reduces compatibility issues.
  - Ensures stability by relying on Django’s supported databases.
  - Promotes portability across different environments.
  - Provides a consistent default (MySQL) for deployments.
- **Negative:**
  - Limits the use of features unique to specific database vendors.
  - May restrict database choices for some deployments.

Related ADRs
------------
- [ADR-000: Introduction](000-intro)
