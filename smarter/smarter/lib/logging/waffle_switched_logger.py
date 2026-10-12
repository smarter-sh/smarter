"""
Smarter.lib.logging.waffle_switched_logger
==========================================

Conditional logger wrapper for the Smarter application.

This module provides a logger wrapper, :class:`WaffleSwitchedLoggerWrapper`, that enables conditional logging
based on a user-supplied function. This allows for dynamic control of logging behavior at runtime, such as
toggling detailed logging with a feature flag (e.g., Django Waffle switches).

Classes
-------
WaffleSwitchedLoggerWrapper
    A logger wrapper that only emits log messages if a condition function returns True for the given log level.

Examples
--------
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

    Usage:
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
    """

    # log entries will be forced at this level and above
    REQUIRED_LOG_LEVEL = logging.WARNING

    def __init__(self, logger: logging.Logger, condition_func: Optional[Callable] = None):
        self._logger = logger
        self._condition_func = condition_func

    def should_log(self, level: int = logging.DEBUG) -> bool:
        """Check if we should log based on custom conditions."""
        if not self._logger.isEnabledFor(level):
            return False

        if self._condition_func:
            try:
                return self._condition_func(level)
            except SynchronousOnlyOperation:
                return False

        return True

    def debug(self, msg: Any, *args, **kwargs):
        if self.should_log(logging.DEBUG) or logging.DEBUG >= self.REQUIRED_LOG_LEVEL:
            self._logger.debug(msg, *args, **kwargs)

    def info(self, msg: Any, *args, **kwargs):
        if self.should_log(logging.INFO) or logging.INFO >= self.REQUIRED_LOG_LEVEL:
            self._logger.info(msg, *args, **kwargs)

    def warning(self, msg: Any, *args, **kwargs):
        if self.should_log(logging.WARNING) or logging.WARNING >= self.REQUIRED_LOG_LEVEL:
            self._logger.warning(msg, *args, **kwargs)

    def error(self, msg: Any, *args, **kwargs):
        if self.should_log(logging.ERROR) or logging.ERROR >= self.REQUIRED_LOG_LEVEL:
            self._logger.error(msg, *args, **kwargs)

    def critical(self, msg: Any, *args, **kwargs):
        if self.should_log(logging.CRITICAL) or logging.CRITICAL >= self.REQUIRED_LOG_LEVEL:
            self._logger.critical(msg, *args, **kwargs)

    def exception(self, msg: Any, *args, exc_info=True, **kwargs):
        if self.should_log(logging.ERROR) or logging.ERROR >= self.REQUIRED_LOG_LEVEL:
            self._logger.exception(msg, *args, exc_info=exc_info, **kwargs)

    def log(self, level: int, msg: Any, *args, **kwargs):
        if self.should_log(level) or level >= self.REQUIRED_LOG_LEVEL:
            self._logger.log(level, msg, *args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        """
        Delegate everything that the wrapper does not define, e.g. ``isEnabledFor()``,.

        ``name`` or ``handlers``, to the wrapped logger, so the wrapper can stand in for it.

        The logging methods are defined above, so that the condition always applies to them.

        :param name: The attribute name.
        :type name: str
        :return: The wrapped logger's attribute.
        :raises AttributeError: If neither the wrapper nor the wrapped logger has the attribute.
        """
        if name == "_logger":
            # not yet set, e.g. during copy or unpickling. avoid infinite recursion.
            raise AttributeError(name)
        return getattr(self._logger, name)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} logger={self._logger.name}>"

    def set_condition(self, condition_func: Callable):
        """Update the condition function."""
        self._condition_func = condition_func

    def getEffectiveLevel(self) -> int:
        """Get the effective logging level of the underlying logger."""
        return self._logger.getEffectiveLevel()


__all__ = [
    "WaffleSwitchedLoggerWrapper",
]
