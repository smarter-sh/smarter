"""Smarter common environment variable utilities."""

import os
from typing import Any, Optional, Union, overload

from pydantic import SecretStr

from smarter.common.conf.const import DEFAULT_MISSING_VALUE
from smarter.common.helpers.console_helpers import SmarterFormattedText
from smarter.common.utils.utils import (
    ENVIRONMENT_VARIABLE_PREFIX,
    bool_environment_variable,
)
from smarter.lib import json, logging
from smarter.lib.typing import SmarterDictType

logger = logging.getSmarterLogger(__name__)
VERBOSE_CONSOLE_OUTPUT = bool_environment_variable("SMARTER_PLATFORM_SETTINGS_OUTPUT", False)

EnvValueType = Union[str, bool, int, float, list[str], SmarterDictType, None]
"""
The types of value that :func:`get_env` returns.

Which one is determined by the type of its ``default``.
"""


def is_missing_value(value: Any) -> bool:
    """
    Return True if a configuration value is missing.

    A value is missing if it is None, empty, or a placeholder, such as ``.env.example``'s
    ``SET-ME-PLEASE`` or ``helm/charts/smarter/values.yaml``'s ``SET-ME-IN-helm/...``. A
    :class:`pydantic.SecretStr` is unwrapped first.

    :param value: The value, e.g. from :func:`get_env`.
    :returns: True if the value is missing.
    """
    if isinstance(value, SecretStr):
        value = value.get_secret_value()
    if value is None:
        return True
    text = str(value).strip()
    return not text or text.upper().startswith("SET-ME")


def read_environment_variable(var_name: str) -> Optional[str]:
    """
    Read an environment variable, with or without Smarter's ``SMARTER_`` prefix.

    The name without the prefix is read first, then the name with it. Surrounding whitespace and
    quotes are stripped.

    :param var_name: The variable's name, without the prefix, e.g. ``DEBUG_MODE``.
    :returns: Its value, or None if neither name is set.
    """
    value = os.environ.get(var_name)
    if not value:
        value = os.environ.get(f"{ENVIRONMENT_VARIABLE_PREFIX}{var_name}")
    if value is None:
        return None
    value = value.strip()
    value = value.strip('"').strip("'")
    return value


def _cast_number(var_name: str, val: str, default: Union[int, float]) -> Union[int, float]:
    """Parse an int, or a float, like ``default``; log the variable's name, never its value, if it can't be."""
    number_type = type(default)
    try:
        return number_type(val)
    except (ValueError, TypeError):
        logger.warning(
            "Environment variable %s cannot be converted to %s. Using its default.",
            var_name,
            number_type.__name__,
        )
        return default


def _cast_dict(var_name: str, val: str, default: SmarterDictType) -> SmarterDictType:
    """Parse a JSON object; log the variable's name, never its value, if it isn't one."""
    try:
        parsed = json.loads(val)
    except json.JSONDecodeError:
        logger.warning("Environment variable %s is not valid JSON. Using its default.", var_name)
        return default
    if not isinstance(parsed, dict):
        logger.warning("Environment variable %s cannot be converted to dict. Using its default.", var_name)
        return default
    return parsed


def cast_environment_value(var_name: str, val: Optional[str], default: EnvValueType) -> EnvValueType:
    """
    Cast an environment variable's value to the type of a default value.

    A string stays a string, and ``true``, ``1``, ``t``, ``y`` or ``yes`` is a True bool. An int or a float
    is parsed, a list is split on commas, and a dict is parsed as JSON. A value that can't be cast is
    logged, without the value, and replaced by the default.

    :param var_name: The variable's name, for the log message.
    :param val: Its value, or None if it is not set.
    :param default: The value whose type it is cast to, and that it is replaced by if it is missing.
    :return: The cast value.
    """
    if val is None:
        return default
    if val == DEFAULT_MISSING_VALUE:
        return default
    if isinstance(default, str):
        return val.strip()
    # bool before int: a bool is an int.
    if isinstance(default, bool):
        return val.lower() in ["true", "1", "t", "y", "yes"]
    if isinstance(default, (int, float)):
        return _cast_number(var_name, val, default)
    if isinstance(default, list):
        items = []
        for item in val.split(","):
            stripped = item.strip()
            if stripped:
                items.append(stripped)
        return items
    if isinstance(default, dict):
        return _cast_dict(var_name, val, default)
    return val


@overload
def get_env(var_name: str, default: bool, is_secret: bool = False, is_required: bool = False) -> bool: ...


@overload
def get_env(var_name: str, default: int, is_secret: bool = False, is_required: bool = False) -> int: ...


@overload
def get_env(var_name: str, default: float, is_secret: bool = False, is_required: bool = False) -> float: ...


@overload
def get_env(var_name: str, default: list[str], is_secret: bool = False, is_required: bool = False) -> list[str]: ...


@overload
def get_env(
    var_name: str, default: SmarterDictType, is_secret: bool = False, is_required: bool = False
) -> SmarterDictType: ...


@overload
def get_env(var_name: str, default: None, is_secret: bool = False, is_required: bool = False) -> Optional[str]: ...


@overload
def get_env(
    var_name: str, default: str = DEFAULT_MISSING_VALUE, is_secret: bool = False, is_required: bool = False
) -> str: ...


def get_env(
    var_name: str, default: EnvValueType = DEFAULT_MISSING_VALUE, is_secret: bool = False, is_required: bool = False
) -> EnvValueType:
    """
    Retrieve a configuration value from the environment, with  prefix fallback and type conversion.

    This function attempts to obtain a configuration value from the environment using the key ``<var_name>``.
    If the environment variable is not set, it returns the provided ``default`` value. The function also performs
    type conversion and validation based on the type of the default value, supporting strings,
    booleans, integers, floats, lists (comma-separated), and dictionaries (JSON-encoded).

    **Behavior:**

    - Checks for the presence of the environment variable ``<var_name>``.
    - If found, attempts to convert the value to the type of ``default``.
    - If not found, or if it holds the ``SET-ME-PLEASE`` placeholder, returns the ``default`` value.
    - Logs a message if the environment variable is missing or if type conversion fails.

    This utility is used throughout the Smarter platform to provide a consistent and robust
    mechanism for loading configuration values from the environment, with sensible type handling and error reporting.

    :param var_name: The base name of the environment variable (without the  prefix).
    :type var_name: str
    :param default: The default value to return if the environment variable is not set. The type of this value determines the expected type and conversion logic.
    :type default: EnvValueType
    :return: The value from the environment (converted to the appropriate type), or the default if it is not set,
        holds the ``SET-ME-PLEASE`` placeholder, or cannot be converted. Only a ``default`` of None returns None.
    :rtype: EnvValueType
    """
    retval = read_environment_variable(var_name)
    if retval is None and is_required:
        logger.warning("Required environment variable %s is missing.", var_name)
        print(f"{SmarterFormattedText.text(__name__)} [WARNING] Required environment variable {var_name} is missing.")
        return default
    else:
        cast_val = cast_environment_value(var_name, retval, default)
        log_value = cast_val if not is_secret else "****"
        if VERBOSE_CONSOLE_OUTPUT:
            msg = f"Environment variable {var_name} found. Overriding Smarter setting from environment variable: {var_name}={repr(log_value)}"
            logger.debug(msg)
            print(f"{SmarterFormattedText.text(__name__)} {msg}")
        return cast_val


__all__ = [
    "EnvValueType",
    "cast_environment_value",
    "get_env",
    "is_missing_value",
    "read_environment_variable",
]
