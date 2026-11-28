"""
Which settings are credentials, and which kinds of pod may hold each one (ADR-038, phase 3).

Every pod used to read one Secret with every credential, though most use few of them. Each credential now says
which kinds of pod (``SERVICE_TYPE``, :attr:`smarter.common.const.SmarterKubernetesPodKinds.all`) use it, with :class:`HeldBy` in its annotation:

.. code-block:: python

    github_token: Annotated[Optional[SecretStr], HeldBy(SmarterKubernetesPodKinds.API, SmarterKubernetesPodKinds.WORKER)] = Field(...)

- Every setting whose type is ``SecretStr`` is a credential, and must say who holds it, even nobody
  (``HeldBy()``): a test fails otherwise. Deriving the credentials from the type, rather than marking each one,
  means that a new ``SecretStr`` setting can't be left out.
- The Helm chart gives each pod only its own credentials, from ``helm/charts/smarter/files/credentials.yaml``,
  which :func:`credential_holders_by_variable` writes (``make chart-credentials``).
- When a pod starts, :meth:`smarter.common.conf.settings.Settings.check_pod_credentials` reports each credential
  it was given but doesn't use (:func:`forbidden_credentials`). The tool worker and the Extension worker, which
  run code that the platform doesn't control (ADR-038, issue #1077), refuse to start instead
  (:meth:`~smarter.common.conf.settings.Settings.check_restricted_worker_credentials`): they hold no credential
  but their own Redis user's password.
"""

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Optional, get_args

from pydantic import AliasChoices, BaseModel, SecretStr
from pydantic.fields import FieldInfo

from smarter.common.conf.env import is_missing_value
from smarter.common.const import SmarterKubernetesPodKinds

ENVIRONMENT_PREFIX = "SMARTER_"
"""The prefix of a setting's environment variable, as ``Settings.model_config``'s ``env_prefix``."""


AWS_POD_KINDS: tuple[str, ...] = (
    SmarterKubernetesPodKinds.API,
    SmarterKubernetesPodKinds.WORKER,
    SmarterKubernetesPodKinds.WORKER_INFRASTRUCTURE,
    SmarterKubernetesPodKinds.JOB_INIT,
    SmarterKubernetesPodKinds.BASTION,
)
"""The kinds of pod that call AWS: S3, SES, Route53, ACM and EKS.

On Kubernetes, their IAM role does, with no key.
"""


@dataclass(frozen=True)
class HeldBy:
    """
    Marks a credential with the kinds of pod that may hold it.

    :param pods: The kinds of pod, from :attr:`smarter.common.const.SmarterKubernetesPodKinds.all`. None: no pod uses the credential, e.g. a setting
        that nothing reads yet.
    """

    pods: frozenset[str]

    def __init__(self, *pods: str):
        object.__setattr__(self, "pods", frozenset(pods))


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


def credential_holders(field: FieldInfo) -> Optional[frozenset[str]]:
    """
    Return the kinds of pod that may hold a credential, from the :class:`HeldBy` in its annotation.

    :param field: The setting's field.
    :returns: The kinds of pod, or None if the credential doesn't say.
    """
    for marker in field.metadata:
        if isinstance(marker, HeldBy):
            return marker.pods
    return None


def may_hold(field: FieldInfo, pod_kind: str) -> bool:
    """
    Return whether a kind of pod may hold a credential.

    A credential that doesn't say may be held by none.

    :param field: The setting's field.
    :param pod_kind: The kind of pod, e.g. ``worker``.
    :returns: True if it may.
    """
    holders = credential_holders(field)
    if holders is None:
        return False
    return pod_kind in holders


def restricted_workers_may_hold(field: FieldInfo) -> bool:
    """
    Return whether the tool worker and the Extension worker may hold a credential: their own Redis user's password.

    :param field: The setting's field.
    :returns: True if both may.
    """
    tools_may = may_hold(field, SmarterKubernetesPodKinds.WORKER_TOOLS)
    extensions_may = may_hold(field, SmarterKubernetesPodKinds.WORKER_EXTENSIONS)
    return tools_may and extensions_may


def environment_variables(name: str, field: FieldInfo) -> list[str]:
    """
    Return the environment variables that a setting is read from: its ``validation_alias``, or ``SMARTER_<NAME>``.

    :param name: The setting's name, e.g. ``subsystem_smtp_password``.
    :param field: The setting's field.
    :returns: The variables' names, e.g. ``["SMARTER_SUBSYSTEM_SMTP_PASSWORD"]``.
    """
    alias = field.validation_alias
    if isinstance(alias, str):
        return [alias]
    if isinstance(alias, AliasChoices):
        names = [choice for choice in alias.choices if isinstance(choice, str)]
        return names
    variable = f"{ENVIRONMENT_PREFIX}{name.upper()}"
    return [variable]


def is_given(environ: Mapping[str, str], variables: list[str]) -> bool:
    """
    Return whether the environment sets one of a credential's variables to a value, not empty and not a placeholder.

    :param environ: The process's environment.
    :param variables: The credential's variables.
    :returns: True if one has a value.
    """
    for variable in variables:
        text = environ.get(variable, "")
        if text.strip() and not is_missing_value(text):
            return True
    return False


def forbidden_credentials(
    settings: BaseModel, environ: Mapping[str, str], pod_kind: str = SmarterKubernetesPodKinds.WORKER_TOOLS
) -> list[str]:
    """
    Return the names of the credentials that a kind of pod was given, but doesn't use.

    A credential counts only if the process's environment sets one of its variables to a value. A value that the
    settings derive themselves, e.g. a generated Fernet key or the local environment's default database
    password, is not one that the worker was given, and doesn't count. Names only: never a value.

    :param settings: The settings.
    :param environ: The process's environment, e.g. ``os.environ``.
    :param pod_kind: The kind of pod, e.g. ``worker``. The tool worker's by default.
    :returns: The settings' names, sorted, or an empty list.
    """
    retval: list[str] = []
    for name, field in type(settings).model_fields.items():
        if not is_credential(field):
            continue
        if may_hold(field, pod_kind):
            continue
        if is_given(environ, environment_variables(name, field)):
            retval.append(name)
    retval.sort()
    return retval


def credential_holders_by_variable(settings_class: type[BaseModel]) -> dict[str, list[str]]:
    """
    Map each credential's environment variables to the kinds of pod that may hold it: what the Helm chart reads.

    ``make chart-credentials`` writes it to ``helm/charts/smarter/files/credentials.json``, and a test fails when
    that file is out of date. The chart gives each pod's Secret only the variables that name its kind.

    :param settings_class: The settings' class, :class:`smarter.common.conf.settings.Settings`.
    :returns: Each variable, sorted, and its pod kinds, sorted. A credential that no pod holds maps to an empty list.
    """
    retval: dict[str, list[str]] = {}
    for name, field in settings_class.model_fields.items():
        if not is_credential(field):
            continue
        holders = credential_holders(field) or frozenset()
        pods = sorted(holders)
        for variable in environment_variables(name, field):
            retval[variable] = pods
    sorted_retval = dict(sorted(retval.items()))
    return sorted_retval


CHART_CREDENTIALS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "credentials.json")
"""
The committed map of each credential's environment variables to the kinds of pod that hold it.

``manage.py export_chart_credentials`` writes it, and ``make chart-credentials`` copies it to the Helm chart, as
``helm/charts/smarter/files/credentials.json``, which the chart reads to build each pod's Secret. A test fails
when it doesn't match the settings, and the chart's tests when the chart's copy doesn't match it.
"""


def render_chart_credentials(settings_class: type[BaseModel]) -> str:
    """
    Return the text of :data:`CHART_CREDENTIALS_PATH`: :func:`credential_holders_by_variable`, as JSON.

    :param settings_class: The settings' class, :class:`smarter.common.conf.settings.Settings`.
    :returns: The JSON, indented, with a trailing newline, so that a change is a readable diff.
    """
    holders = credential_holders_by_variable(settings_class)
    text = json.dumps(holders, indent=2) + "\n"
    return text


def write_chart_credentials(settings_class: type[BaseModel], path: str = CHART_CREDENTIALS_PATH) -> str:
    """
    Write :func:`render_chart_credentials` to a file.

    :param settings_class: The settings' class.
    :param path: The file, :data:`CHART_CREDENTIALS_PATH` by default.
    :returns: The file's path.
    """
    text = render_chart_credentials(settings_class)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


__all__ = [
    "AWS_POD_KINDS",
    "CHART_CREDENTIALS_PATH",
    "ENVIRONMENT_PREFIX",
    "HeldBy",
    "credential_holders",
    "credential_holders_by_variable",
    "environment_variables",
    "forbidden_credentials",
    "is_given",
    "is_credential",
    "may_hold",
    "render_chart_credentials",
    "restricted_workers_may_hold",
    "write_chart_credentials",
]
