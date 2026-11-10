"""
Provide :func:`getSmarterLogger`, which returns a logger with optional Waffle switch control.

This function allows for dynamic control over logging output based on the state of specified
Waffle switches or a custom condition.
"""

from logging import Logger, getLogger
from typing import Callable, Optional, Union

from smarter.lib.django.waffle import switch_is_active

from .waffle_switched_logger import WaffleSwitchedLoggerWrapper


def getSmarterLogger(
    name: Optional[str] = None,
    any_switches: Optional[list[str]] = None,
    all_switches: Optional[list[str]] = None,
    condition_func: Optional[Callable[[int], bool]] = None,
) -> Union[Logger, WaffleSwitchedLoggerWrapper]:
    """
    Return a logger from Python's logging module, with optional Waffle switch control.

    If any of ``any_switches``, ``all_switches`` or ``condition_func`` is provided, the
    logger only emits debug and info logs if at least one of the specified conditions is met.
    Warnings and above are always emitted (see
    :attr:`~smarter.lib.logging.waffle_switched_logger.WaffleSwitchedLoggerWrapper.REQUIRED_LOG_LEVEL`).

    :param name: The name of the logger to retrieve. If None, the root logger is returned.
    :param any_switches: An optional list of Waffle switch names to control logging output.
       Any switch in this list being active will enable logging output.
    :param all_switches: An optional list of Waffle switch names to control logging output.
       All switches in this list must be active to enable logging output.
    :param condition_func: An optional callable, called with the log level, that returns a boolean
       to control logging output. If provided, logging will only occur if this function returns True.
    :returns: A logger instance that may be wrapped with Waffle switch control.
    """

    def eval_any_switches() -> bool:
        """Evaluate if any of the specified Waffle switches are active."""
        if not isinstance(any_switches, list):
            return False
        if len(any_switches) == 0:
            return False
        any_active = any(switch_is_active(switch) for switch in any_switches)
        return any_active

    def eval_all_switches() -> bool:
        """Evaluate if all specified Waffle switches are active."""
        if not isinstance(all_switches, list):
            return False
        if len(all_switches) == 0:
            return False
        all_active = all(switch_is_active(switch) for switch in all_switches)
        return all_active

    def eval_switches(level: int) -> bool:
        """Evaluate the combined conditions of any_switches, all_switches, and the optional condition_func."""
        any_switches_result = eval_any_switches()
        if any_switches_result:
            return any_switches_result
        all_switches_result = eval_all_switches()
        if all_switches_result:
            return all_switches_result
        if condition_func is None:
            return False
        condition_result = condition_func(level)
        return condition_result

    def switches_are_provided() -> bool:
        """Determine if any switch conditions or a condition function have been provided."""
        if isinstance(any_switches, list) and len(any_switches) > 0:
            return True
        if isinstance(all_switches, list) and len(all_switches) > 0:
            return True
        return condition_func is not None

    logger = getLogger(name)

    if switches_are_provided():
        return WaffleSwitchedLoggerWrapper(logger, eval_switches)
    return logger
