ADR-022: Feature Flags
======================

Status
------
Accepted

Context
-------
Feature flags are essential for enabling, disabling, and managing features at runtime without redeploying code. Waffle switches provide a robust and flexible mechanism for feature flag management in Django projects.

Decision
--------
This project uses Waffle switches extensively. New Waffle switches should be added to `SmarterWaffleSwitches` in `from smarter.lib.django.waffle import SmarterWaffleSwitches`.

Alternatives Considered
-----------------------
- Managing feature flags through environment variables or custom solutions.
- Using other feature flag libraries.

Consequences
------------
- **Positive:**
  - Centralizes feature flag management for consistency and maintainability.
  - Makes it easy to audit and update available switches.
  - Leverages Django Waffle’s robust feature set.
- **Negative:**
  - Requires contributors to update a central class for new switches.
  - Adds a dependency on the Waffle library.

Related ADRs
------------
- [ADR-000: Introduction](000-intro)
