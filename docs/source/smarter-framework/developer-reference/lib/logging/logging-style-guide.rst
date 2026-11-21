Smarter Logging Style Guide
=============================

Smarter uses text-formatted Python dot-notated paths to identify the origin of
log messages. For example, a log message from the ``mask_string()`` function of
the ``smarter.common.utils.utils`` module is prefixed with
``smarter.common.utils.utils.mask_string()``. This provides the equivalent
of a run-time trace of the code that generated the log message, which greatly
improves the usefulness of log messages for debugging and monitoring purposes.

The logger writes this prefix, not the code that logs. A module logs through
``logging.getSmarterLogger(__name__)``, which returns a
:class:`~smarter.lib.logging.waffle_switched_logger.WaffleSwitchedLoggerWrapper`.
Each of its logging methods reads the caller's frame with
:func:`~smarter.lib.logging.utils.caller_name` and puts the formatted name in
front of the message, so a call site writes only its own text:

.. code-block:: python

    from smarter.lib import logging

    logger = logging.getSmarterLogger(__name__)


    class PluginDataApi:

        def execute_request(self):
            try:
                ...
            except RequestException as e:
                logger.error("API request failed: %s", e)

    # smarter.apps.llmtool.models.plugin_data_api.PluginDataApi.execute_request() API request failed: ...

A method is named after the class that runs it, so a base class's method that a
subclass runs logs the subclass's name. A record keeps the caller's
``funcName`` and ``lineno``.

Log messages should answer the following questions:

- What happened?
- Where did it happen?
- When did it happen?
- What data was passed?
- Was it successful?
- What data was returned?

Other recommendations:

- Never write the origin yourself, e.g. a module prefix, a class name or a
  hard-coded function name: the logger already wrote it, and a hard-coded name
  goes stale when the function is renamed.
- Be mindful of the log level you choose for each message.
- Use the WaffleSwitchedLoggerWrapper's Waffle switches to control logging output.

.. raw:: html

   <img src="https://cdn.smarter.sh/images/smarter-logging-style.png"
        style="width: 100%; height: auto; display: block; margin: 0 0 1.5em 0; border-radius: 0;"
        alt="Smarter Logging Style"/>
