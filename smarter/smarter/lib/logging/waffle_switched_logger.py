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

Every message the wrapper emits starts with the formatted dotted name of the function or method that
logged it, e.g. ``smarter.apps.llmtool.models.plugin_data_api.PluginDataApi.execute_request()``, so call
sites write only their own text::

    logger.error("API request failed: %s", e)
"""

# The standard library's logging, not smarter.lib.logging: this module is imported while the
# smarter.lib.logging package is still initializing, so importing the package here would be circular.
import logging
import sys
from typing import Any, Callable, Optional

from django.core.exceptions import SynchronousOnlyOperation

from .utils import formatted_caller_name, prefixed_message

CALLER_DEPTH = 2
"""The frames between the caller and :meth:`WaffleSwitchedLoggerWrapper._log`: the public logging method, then the caller."""


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

    def __init__(
        self,
        logger: "logging.Logger | WaffleSwitchedLoggerWrapper",
        condition_func: Optional[Callable[[int], bool]] = None,
    ):
        if isinstance(logger, WaffleSwitchedLoggerWrapper):
            # wrap the logger itself, so that a message isn't prefixed twice, nor gated by both conditions.
            logger = logger._logger  # pylint: disable=protected-access
        self._logger: logging.Logger = logger
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

    def _log(self, level: int, msg: Any, args: tuple, kwargs: dict, prefix_format: Optional[str] = None) -> None:
        """
        Emit a record, starting with the caller's name, if the condition allows it.

        Only the public logging methods call this, so the caller is :data:`CALLER_DEPTH` frames up,
        plus however many frames a ``stacklevel`` argument skips. The wrapped logger is given the
        same ``stacklevel``, adjusted for the wrapper's own two frames, so a record's ``funcName``
        and ``lineno`` are the caller's.

        :param level: The logging level, e.g. ``logging.INFO``.
        :param msg: The message, with %-style placeholders.
        :param args: The message's arguments.
        :param kwargs: Passed to the wrapped logger, e.g. ``exc_info`` or ``extra``.
        :param prefix_format: An ANSI format code for the caller's name, e.g.
            ``SmarterFormattedText.BOLD_DARK_BLUE``, or None for the usual prefix color.
        """
        if level < self.REQUIRED_LOG_LEVEL and not self.should_log(level):
            return
        if not self._logger.isEnabledFor(level):
            return
        stacklevel = kwargs.pop("stacklevel", 1)
        try:
            caller = sys._getframe(CALLER_DEPTH + stacklevel - 1)  # pylint: disable=protected-access
            prefix = formatted_caller_name(caller, prefix_format)
            msg = prefixed_message(prefix, msg, has_args=bool(args))
        except (ValueError, AttributeError):
            # the stack is shallower than stacklevel says. log the message as it is.
            pass
        self._logger.log(level, msg, *args, stacklevel=stacklevel + CALLER_DEPTH, **kwargs)

    def debug(self, msg: Any, *args, prefix_format: Optional[str] = None, **kwargs):
        """
        Log at DEBUG if the condition allows it, or the level is at least ``REQUIRED_LOG_LEVEL``.

        :param msg: The message, with %-style placeholders. The caller's name is added in front of it.
        :param args: The message's arguments.
        :param prefix_format: An ANSI format code for the caller's name, e.g.
            ``SmarterFormattedText.BOLD_DARK_BLUE``. The usual prefix color by default.
        :param kwargs: Passed to the wrapped logger.
        """
        self._log(logging.DEBUG, msg, args, kwargs, prefix_format)

    def info(self, msg: Any, *args, prefix_format: Optional[str] = None, **kwargs):
        """
        Log at INFO if the condition allows it, or the level is at least ``REQUIRED_LOG_LEVEL``.

        :param msg: The message, with %-style placeholders. The caller's name is added in front of it.
        :param args: The message's arguments.
        :param prefix_format: An ANSI format code for the caller's name, e.g.
            ``SmarterFormattedText.BOLD_DARK_BLUE``. The usual prefix color by default.
        :param kwargs: Passed to the wrapped logger.
        """
        self._log(logging.INFO, msg, args, kwargs, prefix_format)

    def warning(self, msg: Any, *args, prefix_format: Optional[str] = None, **kwargs):
        """
        Log at WARNING if the condition allows it, or the level is at least ``REQUIRED_LOG_LEVEL``.

        :param msg: The message, with %-style placeholders. The caller's name is added in front of it.
        :param args: The message's arguments.
        :param prefix_format: An ANSI format code for the caller's name, e.g.
            ``SmarterFormattedText.BOLD_DARK_BLUE``. The usual prefix color by default.
        :param kwargs: Passed to the wrapped logger.
        """
        self._log(logging.WARNING, msg, args, kwargs, prefix_format)

    def error(self, msg: Any, *args, prefix_format: Optional[str] = None, **kwargs):
        """
        Log at ERROR if the condition allows it, or the level is at least ``REQUIRED_LOG_LEVEL``.

        :param msg: The message, with %-style placeholders. The caller's name is added in front of it.
        :param args: The message's arguments.
        :param prefix_format: An ANSI format code for the caller's name, e.g.
            ``SmarterFormattedText.BOLD_DARK_BLUE``. The usual prefix color by default.
        :param kwargs: Passed to the wrapped logger.
        """
        self._log(logging.ERROR, msg, args, kwargs, prefix_format)

    def critical(self, msg: Any, *args, prefix_format: Optional[str] = None, **kwargs):
        """
        Log at CRITICAL if the condition allows it, or the level is at least ``REQUIRED_LOG_LEVEL``.

        :param msg: The message, with %-style placeholders. The caller's name is added in front of it.
        :param args: The message's arguments.
        :param prefix_format: An ANSI format code for the caller's name, e.g.
            ``SmarterFormattedText.BOLD_DARK_BLUE``. The usual prefix color by default.
        :param kwargs: Passed to the wrapped logger.
        """
        self._log(logging.CRITICAL, msg, args, kwargs, prefix_format)

    def exception(self, msg: Any, *args, exc_info=True, prefix_format: Optional[str] = None, **kwargs):
        """
        Log at ERROR, with the stack trace, if the condition allows it, or ERROR is at least ``REQUIRED_LOG_LEVEL``.

        :param msg: The message, with %-style placeholders. The caller's name is added in front of it.
        :param args: The message's arguments.
        :param exc_info: Whether to log the current exception's stack trace.
        :param prefix_format: An ANSI format code for the caller's name, e.g.
            ``SmarterFormattedText.BOLD_DARK_BLUE``. The usual prefix color by default.
        :param kwargs: Passed to the wrapped logger.
        """
        kwargs["exc_info"] = exc_info
        self._log(logging.ERROR, msg, args, kwargs, prefix_format)

    def log(self, level: int, msg: Any, *args, prefix_format: Optional[str] = None, **kwargs):
        """
        Log at ``level`` if the condition allows it, or the level is at least ``REQUIRED_LOG_LEVEL``.

        :param level: The logging level, e.g. ``logging.INFO``.
        :param msg: The message, with %-style placeholders. The caller's name is added in front of it.
        :param args: The message's arguments.
        :param prefix_format: An ANSI format code for the caller's name, e.g.
            ``SmarterFormattedText.BOLD_DARK_BLUE``. The usual prefix color by default.
        :param kwargs: Passed to the wrapped logger.
        """
        self._log(level, msg, args, kwargs, prefix_format)

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
