"""
The settings of one group of ``smarter_settings``, by the names of their environment variables.

Smarter's settings are named after their group: the ``platform_*`` fields of ``smarter_settings``
are the ``SMARTER_PLATFORM_*`` environment variables, the ``subsystem_*`` fields the
``SMARTER_SUBSYSTEM_*`` ones, the ``app_*`` fields the ``SMARTER_APP_*`` ones. The prefix is
:data:`smarter.common.utils.utils.ENVIRONMENT_VARIABLE_PREFIX`, the variables' naming scheme, which
branding doesn't change.

:func:`get_environment_settings` returns a group's settings with values that are safe to log, and
:func:`log_environment_settings` logs them. Neither ever shows a whole secret, nor PII: a secret
shows only its last four characters, which is enough to tell which key is in use.
"""

import os
from collections.abc import Mapping
from typing import Any, Optional, Protocol

from pydantic import BaseModel, SecretStr

from .utils import ENVIRONMENT_VARIABLE_PREFIX, mask_email, mask_identifier

ENVIRONMENT_VARIABLE_LOG_INDENT = " " * 2
"""What :func:`log_environment_variables` puts in front of each variable, after the logger's prefix."""

SECRET_VISIBLE_CHARACTERS = 4
"""How many of a secret's last characters the log shows, e.g. ``****IAUA``, as a chat's prompt configuration does."""


class SmarterDebugLogger(Protocol):  # pylint: disable=too-few-public-methods
    """A logger, or a wrapper of one such as Smarter's ``WaffleSwitchedLoggerWrapper``: anything with ``debug``."""

    def debug(self, msg: Any, *args: Any, **kwargs: Any) -> Any:
        """Log ``msg % args`` at DEBUG."""


def environment_setting_log_value(field_name: str, value: object) -> str:
    """
    Return how one setting is shown in the log: never a whole secret, nor PII.

    A ``SecretStr`` shows only its last :data:`SECRET_VISIBLE_CHARACTERS` characters, e.g.
    ``****IAUA``, which tells an operator which key is in use without revealing it, or ``not set``.
    A secret no longer than that is masked entirely. An email address is masked, and so is a person's name
    (a field that ends in ``primary_contact``). A list's compiled patterns are their patterns.
    Anything else is its ``str()``.

    :param field_name: The field's name, e.g. ``platform_root_domain``.
    :param value: The field's value.
    :returns: The text to log.
    """
    # imported here: smarter.common.conf imports this package.
    from smarter.common.conf.env import (  # pylint: disable=import-outside-toplevel
        is_missing_value,
    )

    if isinstance(value, SecretStr):
        if is_missing_value(value):
            return "not set"
        masked = mask_identifier(value.get_secret_value(), visible=SECRET_VISIBLE_CHARACTERS)
        return masked
    if value is None:
        return "None"
    if "email" in field_name:
        return mask_email(str(value))
    if field_name.endswith("primary_contact"):
        return mask_identifier(str(value), visible=2)
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(getattr(item, "pattern", str(item)) for item in value) + "]"
    return str(value)


def get_environment_settings(settings: BaseModel, group: str) -> dict[str, str]:
    """
    Return one group's settings, by environment variable, with values that are safe to log.

    **Example:**

    >>> get_environment_settings(smarter_settings, "PLATFORM")["SMARTER_PLATFORM_ROOT_DOMAIN"]
    'example.com'

    :param settings: The settings, e.g. ``smarter_settings``.
    :param group: The group, e.g. ``PLATFORM``, ``SUBSYSTEM`` or ``APP``: the fields whose names
        begin with ``<group>_`` in lower case.
    :returns: Each field's environment variable, e.g. ``SMARTER_PLATFORM_ROOT_DOMAIN``, and its value,
        from :func:`environment_setting_log_value`, sorted by name.
    """
    prefix = f"{ENVIRONMENT_VARIABLE_PREFIX}{group.upper()}"
    field_prefix = f"{group.lower()}_"
    retval: dict[str, str] = {}
    for field_name in sorted(type(settings).model_fields):
        if not field_name.startswith(field_prefix):
            continue
        variable = f"{prefix}_{field_name.removeprefix(field_prefix).upper()}"
        retval[variable] = environment_setting_log_value(field_name, getattr(settings, field_name))
    return retval


def log_environment_settings(logger: SmarterDebugLogger, settings: BaseModel, group: str) -> None:
    """
    Log one group's settings at DEBUG, one line per environment variable, between two rules.

    :param logger: The logger, the caller's, so that the lines name the caller.
    :param settings: The settings, e.g. ``smarter_settings``.
    :param group: The group, e.g. ``PLATFORM``.
    """
    # stacklevel=2: each line names the caller, e.g. smarter.settings.prod, not this function.
    logger.debug("*" * 80, stacklevel=2)
    for variable, value in get_environment_settings(settings, group).items():
        logger.debug("%s: %s", variable, value, stacklevel=2)
    logger.debug("*" * 80, stacklevel=2)


SECRET_NAME_SUFFIXES = ("_KEY", "_SECRET", "_PASSWORD", "_TOKEN", "_B64")
"""The endings of an environment variable's name that say its value is a secret, e.g. ``..._API_KEY``."""


def looks_like_a_secret(variable: str) -> bool:
    """
    Return whether an environment variable's name says that its value is a secret.

    A rule on the name, rather than a list of variables, so that it knows no app's variables, and covers one
    that nobody listed.

    :param variable: The variable's name, e.g. ``SMARTER_APP_PROVIDER_OPENAI_API_KEY``.
    :returns: True if its name ends with one of :data:`SECRET_NAME_SUFFIXES`.
    """
    name = variable.upper()
    retval = name.endswith(SECRET_NAME_SUFFIXES)
    return retval


def get_environment_variables(
    settings: BaseModel, group: str, environ: Optional[Mapping[str, str]] = None
) -> dict[str, str]:
    """
    Return the environment variables of one group, e.g. ``APP_LLMCLIENT``, with values that are safe to log.

    It scans the environment for ``SMARTER_<group>_*``, and ``<group>_*``, which
    :func:`smarter.common.conf.env.get_env` reads too. A variable that a field of ``settings`` reads
    shows the field's value, which is what the platform runs with, and a ``SecretStr`` only its last
    four characters; any other variable shows its own value, unless its name says it is a secret
    (:func:`looks_like_a_secret`), e.g. a key that an operator still sets as a variable though its only source is a
    Smarter Secret: that is masked the same way.

    **Example:**

    >>> get_environment_variables(smarter_settings, "APP_LLMCLIENT")
    {'SMARTER_APP_LLMCLIENT_ENABLE': 'True', 'SMARTER_APP_LLMCLIENT_TASKS_DEFAULT_TTL': '600'}

    :param settings: The settings, e.g. ``smarter_settings``.
    :param group: The group, e.g. ``APP_LLMCLIENT``, in either case.
    :param environ: The environment; ``os.environ`` by default.
    :returns: Each variable that is set, and its value, sorted by name.
    """
    if environ is None:
        environ = os.environ
    group_prefix = f"{group.upper()}_"
    fields = type(settings).model_fields
    retval: dict[str, str] = {}
    for variable in sorted(environ):
        name = variable.removeprefix(ENVIRONMENT_VARIABLE_PREFIX)
        if not name.startswith(group_prefix):
            continue
        field_name = name.lower()
        if field_name in fields:
            retval[variable] = environment_setting_log_value(field_name, getattr(settings, field_name))
        elif looks_like_a_secret(variable):
            retval[variable] = environment_setting_log_value(field_name, SecretStr(environ[variable]))
        else:
            retval[variable] = environ[variable]
    return retval


def log_environment_variables(logger: SmarterDebugLogger, settings: BaseModel, group: str) -> None:
    """
    Log one group's environment variables at DEBUG, one line each, from :func:`get_environment_variables`.

    Each line is indented by :data:`ENVIRONMENT_VARIABLE_LOG_INDENT`, so that the variables read as
    children of the line that the caller logs before them, e.g. an app's ``LLMClient app is READY``.

    :param logger: The logger, the caller's, so that the lines name the caller.
    :param settings: The settings, e.g. ``smarter_settings``.
    :param group: The group, e.g. ``APP_LLMCLIENT``.
    """
    for variable, value in get_environment_variables(settings, group).items():
        logger.debug("%s - %s: %s", ENVIRONMENT_VARIABLE_LOG_INDENT, variable, value, stacklevel=2)
