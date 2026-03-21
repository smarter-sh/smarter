"""
Smarter common environment variable utilities.
"""

import logging
import os
from typing import Any, Optional

from smarter.common.helpers.console_helpers import formatted_text
from smarter.common.utils import bool_environment_variable
from smarter.lib import json

logger = logging.getLogger(__name__)
DEFAULT_MISSING_VALUE = "SET-ME-PLEASE"
VERBOSE_CONSOLE_OUTPUT = bool_environment_variable("SMARTER_SETTINGS_OUTPUT", False)


def get_env(var_name, default: Any = DEFAULT_MISSING_VALUE, is_secret: bool = False, is_required: bool = False) -> Any:
    """
    Retrieve a configuration value from the environment, with  prefix fallback and type conversion.

    This function attempts to obtain a configuration value from the environment using the key ``<var_name>``.
    If the environment variable is not set, it returns the provided ``default`` value. The function also performs
    type conversion and validation based on the type of the default value, supporting strings,
    booleans, integers, floats, lists (comma-separated), and dictionaries (JSON-encoded).

    **Behavior:**

    - Checks for the presence of the environment variable ``<var_name>``.
    - If found, attempts to convert the value to the type of ``default``.
    - If not found, returns the ``default`` value.
    - Logs a message if the environment variable is missing or if type conversion fails.

    This utility is used throughout the Smarter platform to provide a consistent and robust
    mechanism for loading configuration values from the environment, with sensible type handling and error reporting.

    :param var_name: The base name of the environment variable (without the  prefix).
    :type var_name: str
    :param default: The default value to return if the environment variable is not set. The type of this value determines the expected type and conversion logic.
    :type default: Any
    :return: The value from the environment (converted to the appropriate type), or the default if not set or conversion fails.
    :rtype: Any
    """
    # pylint: disable=W0621
    logger_prefix = formatted_text(__name__ + ".get_env()")

    def cast_value(val: Optional[str], default: Any) -> Any:
        """
        Cast the environment variable value to the type of the default value.

        :param val: The environment variable value as a string.
        :param default: The default value to determine the target type.
        :return: The casted value.
        """
        if val is None:
            return default
        if isinstance(default, str):
            return val.strip() if val is not None else default
        if isinstance(default, bool):
            return str(val).lower() in ["true", "1", "t", "y", "yes"] if val is not None else default
        if isinstance(default, int):
            try:
                return int(val) if val is not None else default
            except (ValueError, TypeError):
                logger.warning(
                    "%s Environment variable %s value '%s' cannot be converted to int. Using default %s.",
                    logger_prefix,
                    var_name,
                    val,
                    default,
                )
                return default
        if isinstance(default, float):
            try:
                return float(val) if val is not None else default
            except (ValueError, TypeError):
                logger.warning(
                    "%s Environment variable %s value '%s' cannot be converted to float. Using default %s.",
                    logger_prefix,
                    var_name,
                    val,
                    default,
                )
                return default
        if isinstance(default, list):
            if isinstance(val, str):
                return [item.strip() for item in val.split(",") if item.strip()] if val is not None else default
            elif isinstance(val, list):
                return val if val is not None else default
            else:
                logger.warning(
                    "%s Environment variable %s value '%s' cannot be converted to list. Using default %s.",
                    logger_prefix,
                    var_name,
                    val,
                    default,
                )
                return default
        if isinstance(default, dict):
            try:
                if isinstance(val, str):
                    return json.loads(val) if val is not None else default
                elif isinstance(val, dict):
                    return val if val is not None else default
                else:
                    logger.warning(
                        "%s Environment variable %s value '%s' cannot be converted to dict. Using default %s.",
                        logger_prefix,
                        var_name,
                        val,
                        default,
                    )
                    return default
            except json.JSONDecodeError:
                logger.warning(
                    "%s Environment variable %s value '%s' is not valid JSON. Using default %s.",
                    logger_prefix,
                    var_name,
                    val,
                    default,
                )
                return default
        return val

    retval = os.environ.get(var_name) or os.environ.get(f"SMARTER_{var_name}")
    # Strip surrounding quotes if present
    retval = str(retval).strip() if retval is not None else None
    # Strip surrounding quotes if present
    retval = str(retval).strip('"').strip("'") if retval is not None else None
    if retval is None and is_required:
        msg = f"{logger_prefix} [WARNING] Required environment variable {var_name} is missing."
        logger.warning(msg)
        print(msg)
        return default
    else:
        cast_val = cast_value(retval, default)  # type: ignore
        log_value = cast_val if not is_secret else "****"
        if VERBOSE_CONSOLE_OUTPUT:
            msg = f"{logger_prefix} Environment variable {var_name} found. Overriding Smarter setting from environment variable: {var_name}={repr(log_value)}"
            logger.debug(msg)
            print(msg)
        return cast_val
