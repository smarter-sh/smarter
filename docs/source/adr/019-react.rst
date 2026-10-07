ADR-019: React
==============


Status
------
Accepted

Context
-------
JavaScript front-end frameworks can add complexity to build, deployment, and maintenance. Django’s built-in templating tools provide a simpler and more maintainable approach for most UI needs.

Decision
--------
This project will not accept pull requests that include native ReactJS source code or build-deploy code. Moreover, we want to minimize our use of JavaScript front-end frameworks to the Prompt Engineer Workbench UI. Other than this one part of the platform, we will attempt to limit our UI code to Django's built-in templating tools.

Alternatives Considered
-----------------------
- Allowing ReactJS or other JS frameworks throughout the platform.
- Using Django templates exclusively for all UI.

Consequences
------------
- **Positive:**
  - Reduces build and deployment complexity.
  - Simplifies maintenance and onboarding.
  - Promotes consistency in UI implementation.
- **Negative:**
  - Limits flexibility for advanced UI features outside the Prompt Engineer Workbench.
  - May restrict use of modern JS frameworks for future features.

Related ADRs
------------
- [ADR-000: Introduction](000-intro)
