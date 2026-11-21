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

The Content Security Policy is one of Django's core features: ``django.middleware.csp.ContentSecurityPolicyMiddleware``, configured by ``SECURE_CSP_REPORT_ONLY`` in ``smarter.settings.base``. Browsers block nothing until the policy moves to ``SECURE_CSP``. They post what it would block to its ``report-uri``, ``/csp-report/`` on the platform's host (``smarter.lib.django.csp``), which logs each distinct violation once an hour at WARNING, naming the page by its url's name and the blocked resource by its origin, so that a token or signed url in a report never reaches the log. Inline scripts carry the request's nonce: ``nonce="{{ csp_nonce }}"`` in a Django template, and ``with_csp_nonce()`` on the web console's page, which isn't a template. No page uses an inline event handler (``onload=``), which a nonce can't allow.

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
