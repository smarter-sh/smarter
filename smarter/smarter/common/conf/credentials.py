"""
Which settings are credentials, and which of them the two restricted workers may hold.

The tool worker and the Extension worker run code that the platform doesn't control: requests that the LLM
chooses, and Extensions' code (ADR-038, issue #1077). They must hold no credential but their own Redis user's
password, so that such code finds nothing worth taking. The Helm chart gives them only that
(``smarter.toolWorkerEnv``), and :meth:`smarter.common.conf.settings.Settings.check_restricted_worker_credentials`
refuses to start one that was given more, e.g. by a deployment that passed it the platform's whole environment.

- Every setting whose type is ``SecretStr`` is a credential.
- A credential that the restricted workers may hold says so with :class:`RestrictedWorkerCredential`, in its
  annotation:

  .. code-block:: python

      subsystem_redis_password: Annotated[Optional[SecretStr], RestrictedWorkerCredential()] = Field(...)

Deriving the credentials from the type, rather than marking each one, means that a new ``SecretStr`` setting is
covered without anyone remembering to mark it.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import get_args

from pydantic import AliasChoices, BaseModel, SecretStr
from pydantic.fields import FieldInfo

from smarter.common.conf.env import is_missing_value

ENVIRONMENT_PREFIX = "SMARTER_"
"""The prefix of a setting's environment variable, as ``Settings.model_config``'s ``env_prefix``."""


@dataclass(frozen=True)
class RestrictedWorkerCredential:
    """Marks a credential that the tool worker and the Extension worker may hold: their own Redis user's password."""


def is_credential(field: FieldInfo) -> bool:
    """
    Return whether a setting is a credential: its type is ``SecretStr``, or ``Optional[SecretStr]``.

    :param field: The setting's field.
    :returns: True for a credential.
    """
    annotation = field.annotation
    if annotation is SecretStr:
        return True
    retval = SecretStr in get_args(annotation)
    return retval


def restricted_workers_may_hold(field: FieldInfo) -> bool:
    """
    Return whether the restricted workers may hold a credential: its annotation carries :class:`RestrictedWorkerCredential`.

    :param field: The setting's field.
    :returns: True if they may.
    """
    for marker in field.metadata:
        if isinstance(marker, RestrictedWorkerCredential):
            return True
    return False


def environment_variables(name: str, field: FieldInfo) -> list[str]:
    """
    Return the environment variables that a setting is read from: its ``validation_alias``, or ``SMARTER_<NAME>``.

    :param name: The setting's name, e.g. ``app_provider_openai_api_key``.
    :param field: The setting's field.
    :returns: The variables' names, e.g. ``["SMARTER_APP_PROVIDER_OPENAI_API_KEY"]``.
    """
    alias = field.validation_alias
    if isinstance(alias, str):
        return [alias]
    if isinstance(alias, AliasChoices):
        names = [choice for choice in alias.choices if isinstance(choice, str)]
        return names
    variable = f"{ENVIRONMENT_PREFIX}{name.upper()}"
    return [variable]


def forbidden_credentials(settings: BaseModel, environ: Mapping[str, str]) -> list[str]:
    """
    Return the names of the credentials that a restricted worker was given, and must not hold.

    A credential counts only if the process's environment sets one of its variables to a value. A value that the
    settings derive themselves, e.g. a generated Fernet key or the local environment's default database
    password, is not one that the worker was given, and doesn't count. Names only: never a value.

    :param settings: The settings.
    :param environ: The process's environment, e.g. ``os.environ``.
    :returns: The settings' names, sorted, or an empty list.
    """
    retval: list[str] = []
    for name, field in type(settings).model_fields.items():
        if not is_credential(field):
            continue
        if restricted_workers_may_hold(field):
            continue
        given = False
        for variable in environment_variables(name, field):
            text = environ.get(variable, "")
            if text.strip() and not is_missing_value(text):
                given = True
        if not given:
            continue
        retval.append(name)
    retval.sort()
    return retval


__all__ = [
    "ENVIRONMENT_PREFIX",
    "RestrictedWorkerCredential",
    "environment_variables",
    "forbidden_credentials",
    "is_credential",
    "restricted_workers_may_hold",
]
