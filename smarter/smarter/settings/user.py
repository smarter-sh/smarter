"""
User-defined Django settings, which supersede every value in :mod:`smarter.settings`.

An operator who runs Smarter sets Django settings of their own in two places, without changing
Smarter's code:

1. **The user settings file**, a YAML mapping of setting names to values, at
   ``SMARTER_USER_SETTINGS_FILE`` (default :data:`DEFAULT_USER_SETTINGS_FILE`). Locally it is
   ``user-settings/settings.yaml`` in the repository's root, which Docker Compose mounts. The Helm
   chart writes it from ``djangoSettings`` in its values. Nested settings, such as ``LOGGING`` or
   ``CACHES``, are written as YAML.
2. **Environment variables named** ``DJANGO_<SETTING>``, e.g. ``DJANGO_SESSION_COOKIE_AGE=3600``.

Every environment's settings module (``local``, ``alpha``, ``beta``, ``next``, ``prod``) calls
:func:`apply_user_settings` after its last assignment of a setting, so nothing in Smarter's settings can
set a value after it, and before it logs its settings, so that the log shows the values that Django runs
with. The order, from lowest to highest priority:

1. :mod:`smarter.settings.base`
2. :mod:`smarter.settings.base_aws`, in the AWS environments
3. the environment's module, e.g. :mod:`smarter.settings.prod`
4. the user settings file
5. ``DJANGO_*`` environment variables

A user setting replaces the whole setting of that name: a dictionary is not merged with Smarter's.
Settings that Smarter computes from other settings were computed before this runs, so they keep the
values they were computed from.

The log names each setting that is set here, and never its value, which may be a password.
"""

import ast
import json
import logging
import os
import re
from collections.abc import Mapping, MutableMapping
from pathlib import Path
from typing import Optional

import yaml
from django.conf import global_settings

from smarter.lib.logging.waffle_switched_logger import WaffleSwitchedLoggerWrapper

logger = WaffleSwitchedLoggerWrapper(logging.getLogger(__name__))

USER_SETTINGS_FILE_VARIABLE = "SMARTER_USER_SETTINGS_FILE"
"""The environment variable that names the user settings file."""

DEFAULT_USER_SETTINGS_FILE = "/home/smarter_user/user-settings/settings.yaml"
"""Where the user settings file is when ``SMARTER_USER_SETTINGS_FILE`` is unset: in the containers' home."""

ENVIRONMENT_PREFIX = "DJANGO_"
"""The prefix of an environment variable that sets the Django setting named by the rest of its name."""

IGNORED_ENVIRONMENT_VARIABLES = ("DJANGO_SETTINGS_MODULE",)
"""``DJANGO_*`` variables that are Django's own, not settings."""

SETTING_NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")
"""A Django setting's name: upper case letters, digits and underscores, starting with a letter."""

ASCII_CONTROL_CHARACTERS = re.compile(r"[\x00-\x1F\x7F]")
"""Characters that a copy and paste can leave in an environment variable's value."""

TRUE_STRINGS = ("1", "true", "yes", "on")
"""The values of an environment variable that mean True, for a setting whose value is a bool."""


class SmarterUserSettingsError(Exception):
    """The user settings file, or a ``DJANGO_*`` environment variable, can't be applied."""


def user_settings_file_path(environ: Mapping[str, str]) -> Path:
    """
    Return the path of the user settings file.

    It is read from the environment, not from ``smarter_settings``, so that it is known before any
    setting is: ``smarter_settings.user_settings_file`` reads the same variable.

    :param environ: The process's environment.
    :returns: ``SMARTER_USER_SETTINGS_FILE`` or ``USER_SETTINGS_FILE``, else :data:`DEFAULT_USER_SETTINGS_FILE`.
    """
    unprefixed_name = USER_SETTINGS_FILE_VARIABLE.removeprefix("SMARTER_")
    path = environ.get(unprefixed_name)
    if not path:
        path = environ.get(USER_SETTINGS_FILE_VARIABLE)
    if not path:
        path = DEFAULT_USER_SETTINGS_FILE
    return Path(path)


def check_setting_name(name: object, source: str) -> str:
    """
    Return a setting's name, if it is one.

    :param name: The name, a key of the file's mapping, or what follows ``DJANGO_``.
    :param source: Where the name comes from, for the error.
    :returns: The name.
    :raises SmarterUserSettingsError: If it isn't an upper case setting name.
    """
    if not isinstance(name, str):
        raise SmarterUserSettingsError(f"{source}: the setting name {name!r} is not a string.")
    if not SETTING_NAME.match(name):
        raise SmarterUserSettingsError(
            f"{source}: {name!r} is not a Django setting name, which is upper case, e.g. SESSION_COOKIE_AGE."
        )
    return name


def settings_from_file(path: Path) -> dict[str, object]:
    """
    Return the settings in the user settings file.

    :param path: The file's path.
    :returns: The settings by name, or an empty dict when there is no file, or it is empty.
    :raises SmarterUserSettingsError: If the file isn't YAML, isn't a mapping, or has a key that isn't
        a setting name.
    """
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8")
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise SmarterUserSettingsError(f"{path} is not valid YAML: {e}") from e
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise SmarterUserSettingsError(f"{path} must be a mapping of setting names to values.")

    retval: dict[str, object] = {}
    for key, value in data.items():
        name = check_setting_name(key, str(path))
        retval[name] = value
    return retval


def literal_value(text: str) -> object:
    """
    Return the value that an environment variable's text writes.

    :param text: The text.
    :returns: The JSON value it is (``true``, ``5``, ``["a"]``, ``{"a": 1}``), else the Python literal
        it is (``True``, ``("a", "b")``), else the text itself, as a string.
    """
    try:
        return json.loads(text)
    except ValueError:
        pass
    try:
        return ast.literal_eval(text)
    except (ValueError, SyntaxError, MemoryError, RecursionError):
        pass
    return text


def value_like(text: str, current: object) -> object:
    """
    Return an environment variable's value, of the type of the setting's current value.

    :param text: The variable's text.
    :param current: The setting's value before this variable.
    :returns: For a bool, True for ``1``, ``true``, ``yes`` or ``on``, else False. For an int or float, the
        number. For a list or tuple, a JSON or Python list, else the comma-separated items. For a dict, a
        JSON object or Python dict. For a string, the text. For anything else, or no current value,
        :func:`literal_value`.
    :raises SmarterUserSettingsError: If the text isn't a value of the setting's type.
    """
    if isinstance(current, bool):
        lowered = text.lower()
        return lowered in TRUE_STRINGS
    if isinstance(current, (int, float)):
        number_type = type(current)
        try:
            return number_type(text)
        except ValueError as e:
            raise SmarterUserSettingsError(f"{text!r} is not a {number_type.__name__}.") from e
    if isinstance(current, str):
        return text
    if isinstance(current, (list, tuple)):
        return sequence_value(text, type(current))
    if isinstance(current, dict):
        return dict_value(text)
    return literal_value(text)


def sequence_value(text: str, sequence_type: type) -> object:
    """
    Return an environment variable's value, for a setting whose value is a list or a tuple.

    :param text: The variable's text.
    :param sequence_type: ``list`` or ``tuple``, the type of the setting's value.
    :returns: A JSON or Python list or tuple, else the comma-separated items, as ``sequence_type``.
    """
    parsed = literal_value(text)
    if isinstance(parsed, (list, tuple)):
        return sequence_type(parsed)
    items = []
    for item in text.split(","):
        stripped = item.strip()
        if stripped:
            items.append(stripped)
    return sequence_type(items)


def dict_value(text: str) -> dict:
    """
    Return an environment variable's value, for a setting whose value is a dictionary.

    :param text: The variable's text.
    :returns: The JSON object, or the Python dict, that it writes.
    :raises SmarterUserSettingsError: If it writes neither.
    """
    parsed = literal_value(text)
    if not isinstance(parsed, dict):
        raise SmarterUserSettingsError("the value is not a JSON object or a Python dict.")
    return parsed


def current_value(name: str, current_settings: Mapping[str, object]) -> object:
    """
    Return a setting's value before an environment variable sets it, which gives the variable its type.

    :param name: The setting's name.
    :param current_settings: The settings module's namespace.
    :returns: Smarter's value, else Django's default, e.g. ``[]`` for ``SILENCED_SYSTEM_CHECKS``, else None.
    """
    if name in current_settings:
        return current_settings[name]
    default = getattr(global_settings, name, None)
    return default


def settings_from_environment(environ: Mapping[str, str], current_settings: Mapping[str, object]) -> dict[str, object]:
    """
    Return the settings that ``DJANGO_*`` environment variables set.

    :param environ: The process's environment.
    :param current_settings: The settings before these variables, which give each value its type, with
        Django's defaults (:func:`current_value`).
    :returns: The settings by name.
    :raises SmarterUserSettingsError: If a variable's name or value can't be a setting.
    """
    retval: dict[str, object] = {}
    for variable in sorted(environ):
        if not variable.startswith(ENVIRONMENT_PREFIX):
            continue
        if variable in IGNORED_ENVIRONMENT_VARIABLES:
            continue
        unprefixed = variable.removeprefix(ENVIRONMENT_PREFIX)
        name = unprefixed.upper()
        check_setting_name(name, f"the environment variable {variable}")
        raw_text = environ[variable]
        text = ASCII_CONTROL_CHARACTERS.sub("", raw_text).strip()
        current = current_value(name, current_settings)
        try:
            value = value_like(text, current)
        except SmarterUserSettingsError as e:
            raise SmarterUserSettingsError(f"the environment variable {variable}: {e}") from e
        retval[name] = value
    return retval


def is_known_setting(name: str, settings: Mapping[str, object]) -> bool:
    """
    Return whether a setting exists before the user's settings: Django's, a package's, or Smarter's.

    :param name: The setting's name.
    :param settings: The settings module's namespace.
    :returns: True if Smarter's settings or Django's defaults define it.
    """
    if name in settings:
        return True
    return hasattr(global_settings, name)


def apply_user_settings(
    settings: MutableMapping[str, object],
    environ: Optional[Mapping[str, str]] = None,
) -> list[str]:
    """
    Set the user settings file's settings, then the ``DJANGO_*`` environment variables', in ``settings``.

    Each environment's settings module calls it with ``globals()``, after its last assignment of a
    setting and before :func:`smarter.settings.base.log_settings_diagnostics`.

    :param settings: The settings module's namespace, changed in place.
    :param environ: The process's environment; ``os.environ`` by default.
    :returns: The names of the settings set, sorted.
    :raises SmarterUserSettingsError: If the file or a variable can't be applied. Django doesn't start.
    """
    if environ is None:
        environ = os.environ
    path = user_settings_file_path(environ)
    file_settings = settings_from_file(path)
    if file_settings:
        logger.info("Applying %s setting(s) from %s: %s", len(file_settings), path, ", ".join(sorted(file_settings)))

    unknown_names = []
    for name, value in file_settings.items():
        if not is_known_setting(name, settings):
            unknown_names.append(name)
        settings[name] = value

    environment_settings = settings_from_environment(environ, settings)
    if environment_settings:
        names = ", ".join(sorted(environment_settings))
        logger.info("Applying %s setting(s) from DJANGO_* environment variables: %s", len(environment_settings), names)
    for name, value in environment_settings.items():
        if not is_known_setting(name, settings):
            unknown_names.append(name)
        settings[name] = value

    for name in sorted(set(unknown_names)):
        logger.warning(
            "%s is not a Django or Smarter setting. It is set anyway, for an installed package that reads it; "
            "check its spelling if none does.",
            name,
        )

    applied = set(file_settings) | set(environment_settings)
    retval = sorted(applied)
    return retval
