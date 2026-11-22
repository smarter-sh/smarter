"""
Overrides: Django settings that the deployment passes to the process, which overwrite Smarter's.

Smarter's settings modules compute every Django setting from ``smarter_settings``. The deployment
can overwrite any of them at startup, without a change to Smarter's code. Nobody who uses the
platform can: an override exists only in the process's environment, or in a file mounted into the
container, both of which the deployment controls.

How execution gets here on Kubernetes, where the Helm chart deploys Smarter:

1. The chart's ``smarter.env`` (``templates/_helpers.tpl``) builds the platform's environment from
   ``env`` in its values. It always adds ``DJANGO_CELERY_BROKER_URL``, the chart's own Redis, unless
   the values set one. The values' ``env`` sets ``DJANGO_AUTHENTICATION_BACKENDS`` by default. So every
   pod that the chart deploys overrides at least those two settings, with no change by anyone.
2. ``templates/secret-env.yaml`` writes that environment into the Secret ``<appName>-env``, and every
   Deployment and Job reads it with ``envFrom``. Each ``DJANGO_*`` variable in it is in the process's
   environment, ``os.environ``.
3. The container starts its process, and Django imports the settings module
   ``smarter.settings.<environment>``, e.g. :mod:`smarter.settings.prod`. The app server's uvicorn
   loads ``smarter.asgi``, and ``manage.py`` runs, each of which sets ``DJANGO_SETTINGS_MODULE`` from
   ``smarter_settings.environment``. A Celery worker or beat takes the ``DJANGO_SETTINGS_MODULE``
   that ``smarter.env`` put in the Secret.
4. That module imports :mod:`smarter.settings.base` (and :mod:`smarter.settings.base_aws`), assigns
   its own settings, then, on its last lines, calls :func:`apply_overrides` with its ``globals()``,
   which overwrites each setting named by a ``DJANGO_*`` variable.

Locally, Docker Compose passes ``.env`` to every container (``env_file``), so a ``DJANGO_*`` line in
``.env`` reaches step 4 the same way. Docker Compose also mounts ``overrides/`` from the repository's
root, which holds the only other source of overrides: **the overrides file**, a YAML mapping of
setting names to values, at ``SMARTER_OVERRIDES_FILE`` (default :data:`DEFAULT_OVERRIDES_FILE`).
Nested settings, such as ``LOGGING`` or ``CACHES``, are written as YAML. The Helm chart mounts no file.

Each environment's module calls :func:`apply_overrides` after its last assignment of a setting, so
nothing in Smarter's settings can set a value after it, and before it logs its settings, so that the
log shows the values that Django runs with. The order, from lowest to highest priority:

1. :mod:`smarter.settings.base`
2. :mod:`smarter.settings.base_aws`, in the AWS environments
3. the environment's module, e.g. :mod:`smarter.settings.prod`
4. the overrides file
5. ``DJANGO_*`` environment variables

An override replaces the whole setting of that name: a dictionary is not merged with Smarter's.
Settings that Smarter computes from other settings were computed before this runs, so they keep the
values they were computed from, except those in :data:`DERIVED_SETTINGS`, which follow the setting
they are computed from. An overridden ``CACHES`` has to name its ``sessions`` cache too.

The log names each overridden setting and where its override came from, and never its value, which may
be a password.
"""

import ast
import json
import os
import re
from collections.abc import Mapping, MutableMapping
from pathlib import Path
from typing import Optional

import yaml
from django.conf import global_settings

from smarter.lib import logging

logger = logging.getSmarterLogger(__name__)

OVERRIDES_FILE_VARIABLE = "SMARTER_OVERRIDES_FILE"
"""The environment variable that names the overrides file."""

DEFAULT_OVERRIDES_FILE = "/home/smarter_user/overrides/settings.yaml"
"""
Where the overrides file is when ``SMARTER_OVERRIDES_FILE`` is unset: in the containers'.

home, where Docker Compose mounts ``overrides/`` locally.
"""

ENVIRONMENT_PREFIX = "DJANGO_"
"""The prefix of an environment variable that overrides the Django setting named by the rest of its name."""

IGNORED_ENVIRONMENT_VARIABLES = ("DJANGO_SETTINGS_MODULE", "DJANGO_SECRET_KEY")
"""
``DJANGO_*`` variables that this module doesn't apply.

``DJANGO_SETTINGS_MODULE`` is Django's own, not a setting. ``DJANGO_SECRET_KEY`` is read by
``smarter_settings.django_secret_key``, which rejects a placeholder, and ``smarter.settings.base`` sets
``SECRET_KEY`` from it. Applied here as well, a placeholder would replace the random key that
``base`` generates for one.
"""

DERIVED_SETTINGS = {"CELERY_REDBEAT_REDIS_URL": "CELERY_BROKER_URL"}
"""
Settings that Smarter computes from another setting, by name, and the setting each is computed from.

They were computed before the overrides are applied. When the deployment overrides the setting that one
is computed from, and not the derived setting itself, the derived setting is recomputed from the
override, e.g. ``DJANGO_CELERY_BROKER_URL`` moves RedBeat's Redis too.
"""

SETTING_NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")
"""A Django setting's name: upper case letters, digits and underscores, starting with a letter."""

ASCII_CONTROL_CHARACTERS = re.compile(r"[\x00-\x1F\x7F]")
"""Characters that a copy and paste can leave in an environment variable's value."""

TRUE_STRINGS = ("1", "true", "yes", "on")
"""The values of an environment variable that mean True, for a setting whose value is a bool."""


class SmarterOverridesError(Exception):
    """The overrides file, or a ``DJANGO_*`` environment variable, can't be applied."""


def overrides_file_path(environ: Mapping[str, str]) -> Path:
    """
    Return the path of the overrides file.

    It is read from the environment, not from ``smarter_settings``, so that it is known before any
    setting is: ``smarter_settings.overrides_file`` reads the same variable.

    :param environ: The process's environment.
    :returns: ``SMARTER_OVERRIDES_FILE`` or ``OVERRIDES_FILE``, else :data:`DEFAULT_OVERRIDES_FILE`.
    """
    unprefixed_name = OVERRIDES_FILE_VARIABLE.removeprefix("SMARTER_")
    path = environ.get(unprefixed_name)
    if not path:
        path = environ.get(OVERRIDES_FILE_VARIABLE)
    if not path:
        path = DEFAULT_OVERRIDES_FILE
    return Path(path)


def check_setting_name(name: object, source: str) -> str:
    """
    Return a setting's name, if it is one.

    :param name: The name, a key of the file's mapping, or what follows ``DJANGO_``.
    :param source: Where the name comes from, for the error.
    :returns: The name.
    :raises SmarterOverridesError: If it isn't an upper case setting name.
    """
    if not isinstance(name, str):
        raise SmarterOverridesError(f"{source}: the setting name {name!r} is not a string.")
    if not SETTING_NAME.match(name):
        raise SmarterOverridesError(
            f"{source}: {name!r} is not a Django setting name, which is upper case, e.g. SESSION_COOKIE_AGE."
        )
    return name


def overrides_from_file(path: Path) -> dict[str, object]:
    """
    Return the overrides in the overrides file.

    :param path: The file's path.
    :returns: The overridden settings' values by name, or an empty dict when there is no file, or it is empty.
    :raises SmarterOverridesError: If the file isn't YAML, isn't a mapping, or has a key that isn't
        a setting name.
    """
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8")
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise SmarterOverridesError(f"{path} is not valid YAML: {e}") from e
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise SmarterOverridesError(f"{path} must be a mapping of setting names to values.")

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
    :raises SmarterOverridesError: If the text isn't a value of the setting's type.
    """
    if isinstance(current, bool):
        lowered = text.lower()
        return lowered in TRUE_STRINGS
    if isinstance(current, (int, float)):
        number_type = type(current)
        try:
            return number_type(text)
        except ValueError as e:
            raise SmarterOverridesError(f"{text!r} is not a {number_type.__name__}.") from e
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
    :raises SmarterOverridesError: If it writes neither.
    """
    parsed = literal_value(text)
    if not isinstance(parsed, dict):
        raise SmarterOverridesError("the value is not a JSON object or a Python dict.")
    return parsed


def current_value(name: str, current_settings: Mapping[str, object]) -> object:
    """
    Return a setting's value before an environment variable overrides it, which gives the variable its type.

    :param name: The setting's name.
    :param current_settings: The settings module's namespace.
    :returns: Smarter's value, else Django's default, e.g. ``[]`` for ``SILENCED_SYSTEM_CHECKS``, else None.
    """
    if name in current_settings:
        return current_settings[name]
    default = getattr(global_settings, name, None)
    return default


def overrides_from_environment(environ: Mapping[str, str], current_settings: Mapping[str, object]) -> dict[str, object]:
    """
    Return the overrides in the process's ``DJANGO_*`` environment variables.

    :param environ: The process's environment.
    :param current_settings: The settings before these variables, which give each value its type, with
        Django's defaults (:func:`current_value`).
    :returns: The overridden settings' values by name.
    :raises SmarterOverridesError: If a variable's name or value can't be a setting.
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
        except SmarterOverridesError as e:
            raise SmarterOverridesError(f"the environment variable {variable}: {e}") from e
        retval[name] = value
    return retval


def is_known_setting(name: str, settings: Mapping[str, object]) -> bool:
    """
    Return whether a setting exists before it is overridden: Django's, a package's, or Smarter's.

    :param name: The setting's name.
    :param settings: The settings module's namespace.
    :returns: True if Smarter's settings or Django's defaults define it.
    """
    if name in settings:
        return True
    return hasattr(global_settings, name)


def apply_overrides(
    settings: MutableMapping[str, object],
    environ: Optional[Mapping[str, str]] = None,
) -> list[str]:
    """
    Overwrite Smarter's Django settings in ``settings`` with the deployment's overrides.

    The overrides file's are applied first, then the ``DJANGO_*`` environment variables', which
    the Helm chart's ``env`` sets on Kubernetes and ``.env`` sets locally. Each environment's settings
    module calls it with ``globals()``, after its last assignment of a setting and before
    :func:`smarter.settings.base.log_settings_diagnostics`.

    :param settings: The settings module's namespace, changed in place.
    :param environ: The process's environment; ``os.environ`` by default.
    :returns: The names of the settings overridden, and of the settings recomputed from them, sorted.
    :raises SmarterOverridesError: If the file or a variable can't be applied. Django doesn't start.
    """
    if environ is None:
        environ = os.environ
    sources_before = {source: settings.get(source) for source in DERIVED_SETTINGS.values()}
    path = overrides_file_path(environ)
    file_overrides = overrides_from_file(path)
    if file_overrides:
        names = ", ".join(sorted(file_overrides))
        logger.info("Overriding %s Django setting(s) from the file %s: %s", len(file_overrides), path, names)

    unknown_names = []
    for name, value in file_overrides.items():
        if not is_known_setting(name, settings):
            unknown_names.append(name)
        settings[name] = value

    environment_overrides = overrides_from_environment(environ, settings)
    if environment_overrides:
        names = ", ".join(sorted(environment_overrides))
        logger.info(
            "Overriding %s Django setting(s) from the deployment's DJANGO_* environment variables: %s",
            len(environment_overrides),
            names,
        )
    for name, value in environment_overrides.items():
        if not is_known_setting(name, settings):
            unknown_names.append(name)
        settings[name] = value

    for name in sorted(set(unknown_names)):
        logger.warning(
            "%s is not a Django or Smarter setting. It is overridden anyway, for an installed package that "
            "reads it; check its spelling if none does.",
            name,
        )

    overridden = set(file_overrides) | set(environment_overrides)
    overridden |= recompute_derived_settings(settings, overridden, sources_before)
    retval = sorted(overridden)
    return retval


def recompute_derived_settings(
    settings: MutableMapping[str, object],
    overridden: set[str],
    sources_before: Mapping[str, object],
) -> set[str]:
    """
    Recompute each of :data:`DERIVED_SETTINGS` from the overridden setting that it is computed from.

    A derived setting is left alone when it was overridden itself, when its source wasn't overridden, or
    when a settings module had already given it a value of its own, i.e. not its source's.

    :param settings: The settings module's namespace, changed in place.
    :param overridden: The names of the settings that the overrides file and variables set.
    :param sources_before: Each source setting's value before the overrides.
    :returns: The names of the derived settings that were recomputed.
    """
    retval: set[str] = set()
    for derived, source in DERIVED_SETTINGS.items():
        if derived in overridden or source not in overridden:
            continue
        if settings.get(derived) != sources_before.get(source):
            continue
        settings[derived] = settings[source]
        retval.add(derived)
        logger.info("Recomputed %s from the overridden %s", derived, source)
    return retval
