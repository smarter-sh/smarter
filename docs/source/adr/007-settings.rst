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

Sensitive values
~~~~~~~~~~~~~~~~
A password, api key, token, private key or url that embeds one is a credential, and its setting follows
these rules:

1. **It is a** ``SecretStr`` (``Optional[SecretStr]`` when it may be absent). Pydantic masks it in
   ``repr()``, in a dump of the settings and in a validation error, so the settings can be logged and shown
   without it. Code calls ``get_secret_value()`` where the value is used, and nowhere else: never to log it
   (:doc:`ADR-016 <016-security>`, rule 6), and never to pass it as an argument of a cached function, whose
   arguments are its cache key (:doc:`ADR-018 <018-caching>`).
2. **It is its own setting.** A credential is never derived from a setting that isn't secret, and its
   default is ``None`` or a ``SET-ME`` placeholder, never a working value: this repository is public. Where
   the platform can't run without it, the process refuses to start outside the local environment, as
   ``require_django_secret_key()`` does.
3. **Django's own settings are built from it.** A ``DJANGO_*`` override (``smarter.settings.overrides``)
   sets a Django setting as a plain value, so a credential that Smarter's code reads is a Smarter setting
   first, and the Django setting that needs it, such as a database's or a broker's url, is built from that.

As of 0.48.8, 71 settings are ``SecretStr``, and the only credential-like ``str`` is the extension
registry's public key, which is not a secret. The one credential that breaks the rules is Redis's
password: there is no setting for it, and ``smarter.settings.base_aws`` uses
``platform_shared_resource_identifier`` (``smarter`` by default) in its place
(:doc:`ADR-030 <030-task-queues>`, rule 5). Nothing tests the rules yet: a test that every field whose name
says it is a credential is a ``SecretStr``, with the public key as its one exception, would keep them.

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
  - A credential must be unwrapped with ``get_secret_value()`` where it is used.

Related ADRs
------------
- :doc:`ADR-000: Introduction <000-intro>`
- :doc:`ADR-016: Security <016-security>`
- :doc:`ADR-018: Caching <018-caching>`
- :doc:`ADR-030: Operational and Infrastructure Task Queues <030-task-queues>`
