"""
Utility functions for settings.

The field validators of the Settings use these, so that the same rule is written once.
"""

import re
from typing import Optional, Pattern

from pydantic import field_validator

from smarter.common.conf.const import THE_EMPTY_SET
from smarter.common.conf.env import is_missing_value
from smarter.common.exceptions import SmarterConfigurationError


def before_field_validator(*args, **kwargs):
    """Wrapper for pydantic field_validator with mode='before'."""
    kwargs["mode"] = "before"
    return field_validator(*args, **kwargs)


#: A Django REST Framework throttle rate: requests per second, minute, hour or day.
THROTTLE_RATE_PATTERN: Pattern = re.compile(r"^\d+/(s|sec|second|m|min|minute|h|hour|d|day)$")

#: The values that disable a throttle.
THROTTLE_RATE_DISABLED = ("none", "off", "disabled")


def validate_throttle_rate(field_name: str, v: Optional[str], default: Optional[str]) -> Optional[str]:
    """
    Validate a Django REST Framework throttle rate.

    :param field_name: The name of the field, for the error message.
    :param v: The rate, e.g. ``120/minute``, or one of ``THROTTLE_RATE_DISABLED``.
    :param default: The rate to use if the value is empty.
    :returns: The rate, or None if the throttle is disabled.
    :raises SmarterConfigurationError: If the value is not a rate.
    """
    if isinstance(v, str) and v.strip().lower() in THROTTLE_RATE_DISABLED:
        return None
    if v is None or str(v).strip() in THE_EMPTY_SET:
        return default
    if not isinstance(v, str):
        raise SmarterConfigurationError(f"{field_name} of type {type(v)} is not a str: {v}")
    value = v.strip().lower()
    if not THROTTLE_RATE_PATTERN.match(value):
        raise SmarterConfigurationError(
            f"{field_name} {v} is not a throttle rate, e.g. 120/minute, or one of {THROTTLE_RATE_DISABLED}."
        )
    return value


def parse_int_setting(
    field_name: str,
    v: object,
    default: object,
    minimum: Optional[int] = None,
    maximum: Optional[int] = None,
) -> int:
    """
    Parse an integer setting, e.g. ``"300"`` from an environment variable.

    An empty value, or the placeholder of a missing one, is replaced by ``default``, which is
    parsed and checked like any other value.

    :param field_name: The name of the field, for the error message.
    :param v: The value to parse: an int, or a string of one.
    :param default: The value to use if ``v`` is empty.
    :param minimum: The smallest value allowed, or None for no lower bound.
    :param maximum: The largest value allowed, or None for no upper bound.
    :returns: The value, as an int.
    :raises SmarterConfigurationError: If the value isn't an integer, or is out of bounds.
    """
    if v is None or v in THE_EMPTY_SET or is_missing_value(v):
        v = default
    if isinstance(v, bool):
        raise SmarterConfigurationError(f"{field_name} {v} is a bool, not an integer.")
    if isinstance(v, int):
        value = v
    elif isinstance(v, str):
        try:
            value = int(v)
        except ValueError as e:
            raise SmarterConfigurationError(f"could not validate {field_name}: {v} is not an integer.") from e
    else:
        raise SmarterConfigurationError(f"{field_name} of type {type(v)} is not an integer: {v}")
    if minimum is not None and value < minimum:
        raise SmarterConfigurationError(f"{field_name} {value} must be at least {minimum}.")
    if maximum is not None and value > maximum:
        raise SmarterConfigurationError(f"{field_name} {value} must be at most {maximum}.")
    return value


__all__ = [
    "THROTTLE_RATE_DISABLED",
    "THROTTLE_RATE_PATTERN",
    "before_field_validator",
    "parse_int_setting",
    "validate_throttle_rate",
]
