Smarter Logging Style Guide
=============================

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
