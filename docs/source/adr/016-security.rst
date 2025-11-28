ADR-016: Security
=================

Status
------
Accepted

Context
-------
Security is a critical concern for any web platform. Django provides robust, well-maintained security features out of the box. Custom security implementations can introduce risk and maintenance overhead if not handled carefully.

Decision
--------
This project attempts to defer security features to Django. In the rare exceptions where this is insufficient, customizations should be implemented in `smarter.lib.django.middleware`—see existing examples for CSRF, CORS, brute-force attacks, and attempts to access sensitive files.

Pull requests implementing security modifications should also include updates to all existing references to native Django features.

Our implementation of middleware features should always be consistent: we will consistently use Django's core features, or we will consistently use our own modification of those features.

Alternatives Considered
-----------------------
- Implementing custom security features throughout the codebase.
- Relying solely on third-party security packages.

Consequences
------------
- **Positive:**
  - Leverages Django’s proven security features.
  - Centralizes custom security logic for easier maintenance and review.
  - Reduces risk of inconsistent or incomplete security implementations.
  - Promotes consistency in middleware implementation across the codebase.
- **Negative:**
  - Requires contributors to be familiar with Django’s security model and project-specific middleware.
  - May require additional effort to update references when customizing security features.

Related ADRs
------------
- [ADR-000: Introduction](000-intro)
