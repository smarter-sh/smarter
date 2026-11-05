"""
Conditional logger wrapper for the Smarter application.

This module provides a logger wrapper, :class:`WaffleSwitchedLoggerWrapper`, that enables conditional logging
based on a user-supplied function. This allows for dynamic control of logging behavior at runtime, such as
toggling detailed logging with a feature flag (e.g., Django Waffle switches).

**Classes:**

- :class:`WaffleSwitchedLoggerWrapper`: a logger wrapper that only emits log messages if a condition
  function returns True for the given log level.

**Example:**

To use the conditional logger wrapper with a Django Waffle switch::

    import logging
    from smarter.lib.django import waffle
    from smarter.lib.django.waffle import SmarterWaffleSwitches
    from smarter.lib.logging.waffle_switched_logger import WaffleSwitchedLoggerWrapper

    def should_log_detailed(level):
        return waffle.switch_is_active(SmarterWaffleSwitches.PROMPT_LOGGING)

    base_logger = logging.getLogger(__name__)
    logger = WaffleSwitchedLoggerWrapper(base_logger, should_log_detailed)
    logger.debug("This is a debug message.")

The logger will only emit messages if the condition function returns True for the log level, or if the log level
is WARNING or higher (forced by REQUIRED_LOG_LEVEL).
"""

from typing import Any, Callable, Optional

from django.core.exceptions import SynchronousOnlyOperation

from smarter.lib import logging


class WaffleSwitchedLoggerWrapper:
    """
    A wrapper around a standard logger that adds conditional logic.

    **Usage:**

    .. code-block:: python

        import logging

        from smarter.lib.django import waffle
        from smarter.lib.django.waffle import SmarterWaffleSwitches
        from smarter.lib.logging import WaffleSwitchedLoggerWrapper

        def should_log_detailed(level):
            return waffle.switch_is_active(SmarterWaffleSwitches.PROMPT_LOGGING)

        base_logger = logging.getLogger(__name__)
        logger = WaffleSwitchedLoggerWrapper(base_logger, should_log_detailed)

        logger.debug("This is a debug message.")

    :param logger: The logger to wrap.
    :param condition_func: Called with a log level; the message is logged only if it returns True.
        None means always log, at the levels that the wrapped logger is enabled for.
    """

    #: Log entries are always emitted at this level and above, whatever the condition says.
    REQUIRED_LOG_LEVEL = logging.WARNING

    def __init__(self, logger: logging.Logger, condition_func: Optional[Callable[[int], bool]] = None):
        self._logger = logger
        self._condition_func = condition_func

    def should_log(self, level: int = logging.DEBUG) -> bool:
        """
        Check if we should log based on custom conditions.

        :param level: The log level, e.g. ``logging.INFO``.
        :returns: False if the wrapped logger isn't enabled for ``level``, else the condition's
            answer (False if it needs a synchronous database call from async code), or True
            if there is no condition.
        """
        if not self._logger.isEnabledFor(level):
            return False

        if self._condition_func:
            try:
                return self._condition_func(level)
            except SynchronousOnlyOperation:
                return False

        return True

    def debug(self, msg: Any, *args, **kwargs):
        """
        Log at DEBUG if the condition allows it, or the level is at least ``REQUIRED_LOG_LEVEL``.

        :param msg: The message, with %-style placeholders.
        :param args: The message's arguments.
        :param kwargs: Passed to the wrapped logger.
        """
        if logging.DEBUG >= self.REQUIRED_LOG_LEVEL or self.should_log(logging.DEBUG):
            self._logger.debug(msg, *args, **kwargs)

    def info(self, msg: Any, *args, **kwargs):
        """
        Log at INFO if the condition allows it, or the level is at least ``REQUIRED_LOG_LEVEL``.

        :param msg: The message, with %-style placeholders.
        :param args: The message's arguments.
        :param kwargs: Passed to the wrapped logger.
        """
        if logging.INFO >= self.REQUIRED_LOG_LEVEL or self.should_log(logging.INFO):
            self._logger.info(msg, *args, **kwargs)

    def warning(self, msg: Any, *args, **kwargs):
        """
        Log at WARNING if the condition allows it, or the level is at least ``REQUIRED_LOG_LEVEL``.

        :param msg: The message, with %-style placeholders.
        :param args: The message's arguments.
        :param kwargs: Passed to the wrapped logger.
        """
        if logging.WARNING >= self.REQUIRED_LOG_LEVEL or self.should_log(logging.WARNING):
            self._logger.warning(msg, *args, **kwargs)

    def error(self, msg: Any, *args, **kwargs):
        """
        Log at ERROR if the condition allows it, or the level is at least ``REQUIRED_LOG_LEVEL``.

        :param msg: The message, with %-style placeholders.
        :param args: The message's arguments.
        :param kwargs: Passed to the wrapped logger.
        """
        if logging.ERROR >= self.REQUIRED_LOG_LEVEL or self.should_log(logging.ERROR):
            self._logger.error(msg, *args, **kwargs)

    def critical(self, msg: Any, *args, **kwargs):
        """
        Log at CRITICAL if the condition allows it, or the level is at least ``REQUIRED_LOG_LEVEL``.

        :param msg: The message, with %-style placeholders.
        :param args: The message's arguments.
        :param kwargs: Passed to the wrapped logger.
        """
        if logging.CRITICAL >= self.REQUIRED_LOG_LEVEL or self.should_log(logging.CRITICAL):
            self._logger.critical(msg, *args, **kwargs)

    def exception(self, msg: Any, *args, exc_info=True, **kwargs):
        """
        Log at ERROR, with the stack trace, if the condition allows it, or ERROR is at least ``REQUIRED_LOG_LEVEL``.

        :param msg: The message, with %-style placeholders.
        :param args: The message's arguments.
        :param exc_info: Whether to log the current exception's stack trace.
        :param kwargs: Passed to the wrapped logger.
        """
        if logging.ERROR >= self.REQUIRED_LOG_LEVEL or self.should_log(logging.ERROR):
            self._logger.exception(msg, *args, exc_info=exc_info, **kwargs)

    def log(self, level: int, msg: Any, *args, **kwargs):
        """
        Log at ``level`` if the condition allows it, or the level is at least ``REQUIRED_LOG_LEVEL``.

        :param level: The logging level, e.g. ``logging.INFO``.
        :param msg: The message, with %-style placeholders.
        :param args: The message's arguments.
        :param kwargs: Passed to the wrapped logger.
        """
        if level >= self.REQUIRED_LOG_LEVEL or self.should_log(level):
            self._logger.log(level, msg, *args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        """
        Delegate everything that the wrapper does not define to the wrapped logger.

        For example ``isEnabledFor()``, ``name`` or ``handlers``, so that the wrapper can stand in
        for the logger. The logging methods are defined above, so that the condition always
        applies to them.

        :param name: The attribute name.
        :returns: The wrapped logger's attribute.
        :raises AttributeError: If neither the wrapper nor the wrapped logger has the attribute.
        """
        if name == "_logger":
            # not yet set, e.g. during copy or unpickling. avoid infinite recursion.
            raise AttributeError(name)
        return getattr(self._logger, name)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} logger={self._logger.name}>"

    def set_condition(self, condition_func: Callable[[int], bool]) -> None:
        """
        Update the condition function.

        :param condition_func: Called with a log level; the message is logged only if it returns True.
        """
        self._condition_func = condition_func

    def getEffectiveLevel(self) -> int:
        """
        Get the effective logging level of the underlying logger.

        :returns: The wrapped logger's effective level, e.g. ``logging.INFO``.
        """
        return self._logger.getEffectiveLevel()


__all__ = [
    "WaffleSwitchedLoggerWrapper",
]
