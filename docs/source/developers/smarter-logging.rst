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
