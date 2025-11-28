ADR-026: Keen Bootstrap
=======================

Status
------
Accepted

Context
-------
A consistent and professional UI theme is important for usability and branding. The project has standardized on the Keen premium Bootstrap theme for the web console UI.

Decision
--------
The web console UI is created using the Keen premium Bootstrap theme, v3.0.6. Do not create pull requests that use a different theme or UI framework.

Alternatives Considered
-----------------------
- Using other Bootstrap themes.
- Allowing multiple or custom UI themes.

Consequences
------------
- **Positive:**
  - Ensures a consistent and professional appearance for the web console.
  - Simplifies maintenance and onboarding for UI development.
- **Negative:**
  - Limits flexibility for contributors who may prefer other themes or frameworks.

Related ADRs
------------
- [ADR-000: Introduction](000-intro)
