"""
A logger that can be controlled with a condition function.
This allows for more flexible logging behavior based on runtime conditions.
"""

import logging
from typing import Any, Callable, Optional


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
    REQUIRED_LOG_LEVEL = 30

    def __init__(self, logger: logging.Logger, condition_func: Optional[Callable] = None):
        self._logger = logger
        self._condition_func = condition_func

    def _should_log(self, level: int = logging.DEBUG) -> bool:
        """Check if we should log based on custom conditions."""
        if not self._logger.isEnabledFor(level):
            return False

        if self._condition_func:
            return self._condition_func(level)

        return True

    def debug(self, msg: Any, *args, **kwargs):
        if self._should_log(logging.DEBUG) or logging.DEBUG >= self.REQUIRED_LOG_LEVEL:
            self._logger.debug(msg, *args, **kwargs)

    def info(self, msg: Any, *args, **kwargs):
        if self._should_log(logging.INFO) or logging.INFO >= self.REQUIRED_LOG_LEVEL:
            self._logger.info(msg, *args, **kwargs)

    def warning(self, msg: Any, *args, **kwargs):
        if self._should_log(logging.WARNING) or logging.WARNING >= self.REQUIRED_LOG_LEVEL:
            self._logger.warning(msg, *args, **kwargs)

    def error(self, msg: Any, *args, **kwargs):
        if self._should_log(logging.ERROR) or logging.ERROR >= self.REQUIRED_LOG_LEVEL:
            self._logger.error(msg, *args, **kwargs)

    def critical(self, msg: Any, *args, **kwargs):
        if self._should_log(logging.CRITICAL) or logging.CRITICAL >= self.REQUIRED_LOG_LEVEL:
            self._logger.critical(msg, *args, **kwargs)

    def set_condition(self, condition_func: Callable):
        """Update the condition function."""
        self._condition_func = condition_func
