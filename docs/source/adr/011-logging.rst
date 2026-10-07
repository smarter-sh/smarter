ADR-011: Logging
================

Status
------
Accepted

Context
-------
Effective logging is essential for debugging, monitoring, and maintaining the platform. Traditional logging based solely on log levels can be too coarse-grained, making it difficult to control log output for specific modules or features at runtime. The Smarter platform requires more granular control over logging, including the ability to enable or disable logging dynamically for specific modules or functions.

Decision
--------
Modules should implement a logging pattern that provides granular control over where log data is generated, beyond simply defining a log level. This pattern enables fine-tuning of logging levels by function or module at runtime using waffle switches. The recommended implementation is:

.. code-block:: python

    def should_log(level):
        """Check if logging should be done based on the waffle switch."""
        return waffle.switch_is_active(SmarterWaffleSwitches.PLUGIN_LOGGING) and level >= smarter_settings.log_level

    base_logger = logging.getLogger(__name__)
    logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)

Alternatives Considered
-----------------------
- Relying solely on standard Python logging levels.
- Using environment variables or configuration files to control logging granularity.

Consequences
------------
- **Positive:**
  - Enables dynamic, fine-grained control over logging output at runtime.
  - Allows logging to be toggled for specific modules or features using waffle switches.
  - Reduces log noise and improves signal-to-noise ratio for debugging and monitoring.
- **Negative:**
  - Introduces additional complexity in logging configuration and management.
  - Requires contributors to adopt and understand the new logging pattern.

Related ADRs
------------
- [ADR-000: Introduction](000-intro)
