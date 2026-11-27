"""
Utility functions for settings.

The field validators of the Settings use these, so that the same rule is written once.
"""

import re
from typing import Any, Optional, Pattern, Union

from pydantic import BaseModel, field_validator

from smarter.common.conf.const import THE_EMPTY_SET
from smarter.common.conf.env import is_missing_value
from smarter.common.exceptions import SmarterConfigurationError


def field_default(model: Union[type[BaseModel], BaseModel], field_name: str) -> Any:
    """
    Return a settings field's default, as its declaration states it.

    The validators use it for a value that is empty, e.g. ``""`` passed to the constructor, so that a
    default is written once, on its field.

    :param model: The settings class, or the class of one group of its fields. An instance of one is
        read as its class: the validators' ``cls`` is typed as an instance.
    :param field_name: The field, e.g. ``debug_mode``.
    :returns: Its default, whose type is the field's. A default that a factory makes is made.
    """
    if isinstance(model, BaseModel):
        model_class = type(model)
    else:
        model_class = model
    field = model_class.model_fields[field_name]
    default = field.get_default(call_default_factory=True)
    return default


def has_field(model: Union[type[BaseModel], BaseModel], field_name: str) -> bool:
    """
    Return True if a settings class declares a field.

    A group of fields' model validator can need a field of another group, e.g. ``environment``. The group's
    class is also validated on its own, without that field, so the validator checks for it first.

    :param model: The settings class, or the class of one group of its fields. An instance of one is
        read as its class, as in :func:`field_default`.
    :param field_name: The field, e.g. ``environment``.
    :returns: Whether the class declares it.
    """
    if isinstance(model, BaseModel):
        model_class = type(model)
    else:
        model_class = model
    fields = model_class.model_fields
    return field_name in fields


def is_unset(data: object, field_name: str) -> bool:
    """
    Return True if the values to validate leave a field out, or set it to an empty value.

    :param data: The values that a ``mode="before"`` model validator receives.
    :param field_name: The field.
    :returns: True if the field will get its default.
    """
    if not isinstance(data, dict):
        return False
    value = data.get(field_name)
    if value is None:
        return True
    if isinstance(value, str) and value in THE_EMPTY_SET:
        return True
    return False


def input_value(model: Union[type[BaseModel], BaseModel], data: object, field_name: str) -> Any:
    """
    Return the value that a field will be validated from: the one given, or else its default.

    :param model: The settings class, or the class of one group of its fields.
    :param data: The values that a ``mode="before"`` model validator receives.
    :param field_name: The field.
    :returns: Its value, not yet validated, which may be of any type the field accepts.
    """
    if is_unset(data, field_name):
        return field_default(model, field_name)
    assert isinstance(data, dict)
    return data[field_name]


def with_derived_default(data: object, field_name: str, value: object) -> object:
    """
    Return the values to validate, with a derived default for a field that they leave unset.

    A default that depends on another field, e.g. an address at the platform's domain, can't be written
    on its field. A ``mode="before"`` model validator computes it instead, and passes it here.

    :param data: The values that a ``mode="before"`` model validator receives.
    :param field_name: The field.
    :param value: Its derived default.
    :returns: A copy of the values with the field set, or the values themselves if they set it.
    """
    if not is_unset(data, field_name):
        return data
    assert isinstance(data, dict)
    derived = dict(data)
    derived[field_name] = value
    return derived


def comma_separated(v: Any) -> Any:
    """
    Split a comma-separated string into a list, e.g. ``"a, b,"`` into ``["a", "b"]``.

    A list setting's environment variable is a comma-separated string. Any other value is returned
    as it is, for its validator to judge.

    :param v: The value of a list setting.
    :returns: The list of the string's items, without whitespace or empty items, or the value itself,
        which may be of any type: the validator that calls it judges it.
    """
    if not isinstance(v, str):
        return v
    items = []
    for item in v.split(","):
        stripped = item.strip()
        if stripped:
            items.append(stripped)
    return items


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
    "comma_separated",
    "field_default",
    "input_value",
    "is_unset",
    "with_derived_default",
    "parse_int_setting",
    "validate_throttle_rate",
]
