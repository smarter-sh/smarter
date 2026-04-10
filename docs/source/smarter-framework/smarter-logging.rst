Smarter Logging
=================

Smarter logging provides granular control over logging output at run-time using
Waffle switches. This allows developers to enable or disable logging for specific
components without changing the code or redeploying the application.

Usage
------------

.. code-block:: python

    from smarter.lib.django import waffle
    from smarter.lib.django.waffle import SmarterWaffleSwitches
    from smarter.lib.logging import WaffleSwitchedLoggerWrapper

    def should_log(level):
        """Check if logging should be done based on the waffle switch."""
        return waffle.switch_is_active(SmarterWaffleSwitches.ACCOUNT_LOGGING) and level >= smarter_settings.log_level

    base_logger = logging.getLogger(__name__)
    logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)

    logger.debug("This is a debug message.")
    logger.info("This is an info message.")
    logger.warning("This is a warning message.")
    logger.error("This is an error message.")
    logger.critical("This is a critical message.")

Style Guide
----------------

Smarter uses text-formatted Python dot-notated paths to identify the origin of
log messages. For example, a log message from the `smarter.common.utils` module
would be prefixed with `smarter.common.utils`. This provides the equivalent
of a run-time trace of the code that generated the log message, which greatly
improves the usefulness of log messages for debugging and monitoring purposes.

Log messages should answer the following questions:

- What happened?
- Where did it happen?
- When did it happen?
- What data was passed?
- Was it successful?
- What data was returned?

Other recommendations:

- Do not format the function name.
- Be mindful of the log level you choose for each message.
- Be aware of the effects of class inheritance when programmatically generating formatted paths.
- Use the WaffleSwitchedLoggerWrapper to control logging output.

.. raw:: html

   <img src="https://cdn.smarter.sh/images/smarter-logging-style.png"
        style="width: 100%; height: auto; display: block; margin: 0 0 1.5em 0; border-radius: 0;"
        alt="Smarter Logging Style"/>

Waffle Switches
----------------

.. raw:: html

   <img src="https://cdn.smarter.sh/images/waffle-switches.png"
        style="width: 100%; height: auto; display: block; margin: 0 0 1.5em 0; border-radius: 0;"
        alt="Smarter Waffle Switches"/>


WaffleSwitchedLoggerWrapper Class Reference
--------------------------------------------

.. autoclass:: smarter.lib.logging.WaffleSwitchedLoggerWrapper
   :members:
   :undoc-members:
   :show-inheritance:
