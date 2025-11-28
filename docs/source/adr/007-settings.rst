ADR-007: Settings
=================

Status
------
Accepted

Context
-------
Settings are managed by `smarter.common.conf.Settings`, which is implemented using Pydantic. Smarter's `Settings` class is a singleton designed to marshal configuration data from the session OS environment, validate this data, enforce business rules where applicable, and then make this data available as properties of a singleton instance.

Decision
--------
All configuration for the platform must be handled through the `Settings` singleton. This ensures consistent validation, enforcement of business rules, and centralized access to configuration data.

Alternatives Considered
-----------------------
- Managing settings through multiple configuration files or environment variables without a central class.
- Using alternative configuration management libraries.

Consequences
------------
- **Positive:**
  - Centralizes and standardizes configuration management.
  - Ensures validation and enforcement of business rules.
  - Simplifies access to configuration throughout the codebase.
- **Negative:**
  - Requires contributors to use the singleton pattern for all configuration access.
  - May introduce limitations if more dynamic configuration is needed in the future.

Related ADRs
------------
- [ADR-000: Introduction](000-intro)
