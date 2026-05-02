"""
getSmarterLogger() - A utility function to retrieve a logger instance with
optional Waffle switch control. This function allows for dynamic control over
logging output based on the state of specified Waffle switches or a custom
condition.
"""

from logging import Logger, getLogger
from typing import Callable, Optional, Union

from smarter.lib.django.waffle import switch_is_active

from .waffle_switched_logger import WaffleSwitchedLoggerWrapper


def getSmarterLogger(
    name=None,
    any_switches: Optional[list[str]] = None,
    all_switches: Optional[list[str]] = None,
    condition_func: Optional[Callable] = None,
) -> Union[Logger, WaffleSwitchedLoggerWrapper]:
    """
    Python's logging module enhanced with optional Waffle switch control. If
    any of `any_switches`, `all_switches` or `condition_func` is provided, the
    logger will only emit logs if at least one of the specified conditions is met.

    :param name: The name of the logger to retrieve. If None, the root logger is returned.
    :param any_switches: An optional list of Waffle switch names to control logging output.
       Any switch in this list being active will enable logging output.
    :param all_switches: An optional list of Waffle switch names to control logging output.
       All switches in this list must be active to enable logging output.
    :param condition_func: An optional callable that returns a boolean to control logging output.
       If provided, logging will only occur if this function returns True.
    :return: A logger instance that may be wrapped with Waffle switch control.
    :rtype: Logger or WaffleSwitchedLoggerWrapper
    """

    def eval_any_switches() -> bool:
        """
        Evaluate if any of the specified Waffle switches are active.
        """
        return (
            isinstance(any_switches, list)
            and len(any_switches) > 0
            and any(switch_is_active(switch) for switch in any_switches)
        )

    def eval_all_switches() -> bool:
        """
        Evaluate if all specified Waffle switches are active.
        """
        return (
            isinstance(all_switches, list)
            and len(all_switches) > 0
            and all(switch_is_active(switch) for switch in all_switches)
        )

    def eval_switches(level) -> bool:
        """
        Evaluate the combined conditions of any_switches, all_switches, and the optional condition_func.
        """
        return (
            eval_any_switches()
            or eval_all_switches()
            or (condition_func(level) if condition_func is not None else False)
        )

    def switches_are_provided() -> bool:
        """
        Determine if any switch conditions or a condition function have been provided.
        """
        return (isinstance(any_switches, list) and len(any_switches) > 0) or (
            isinstance(all_switches, list) and len(all_switches) > 0 or condition_func is not None
        )

    logger = getLogger(name)

    if switches_are_provided():
        logger = WaffleSwitchedLoggerWrapper(logger, eval_switches)
    return logger
