ADR-021: Internationalization
=============================

Status
------
Accepted

Context
-------
Supporting multiple languages improves accessibility and usability for a global user base. Django provides built-in internationalization tools using GNU gettext for translating templates and strings.

Decision
--------
The project uses Django's built-in template tools—GNU gettext()—for internationalization. As of v0.13x, the templates are not internationalized. When working on templates, effort should be made to set up PO files for the 5 most common languages: en, zh-hans, hi, es, fr.

Alternatives Considered
-----------------------
- Using third-party internationalization libraries.
- Limiting the platform to English-only templates.

Consequences
------------
- **Positive:**
  - Leverages Django’s robust internationalization support.
  - Improves accessibility for users in multiple regions.
- **Negative:**
  - Requires ongoing effort to maintain and update translation files.
  - Contributors must be familiar with Django’s i18n workflow.

Related ADRs
------------
- [ADR-000: Introduction](000-intro)
