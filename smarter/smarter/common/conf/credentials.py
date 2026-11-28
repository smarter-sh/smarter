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
from smarter.common.enum import SmarterEnumAbstract

ENVIRONMENT_PREFIX = "SMARTER_"
"""The prefix of a setting's environment variable, as ``Settings.model_config``'s ``env_prefix``."""


class SecretBootstrapVariable(SmarterEnumAbstract):
    """
    The environment variables from which the init Job creates Smarter Secrets, and that nothing else reads.

    Temporary. These are three apps' names (provider, llmtool, vectorstore), listed here, in the settings' layer,
    only because they reach the init Job as environment variables, and the settings' checks, which run before any
    app is loaded, must keep them out of every other pod and out of the log. The keys are to reach the init Job as a
    Kubernetes Secret instead, keyed by the Smarter Secrets' own names, and this class then goes.

    ``initialize_providers``, ``initialize_llmtool_api_keys`` and ``initialize_vectorstore_providers``, which
    ``initialize_platform`` runs, read each one (with ``get_env``, as ``SMARTER_<value>`` or ``<value>``) and store it
    as the Smarter Secret that its member names. From then on, every service reads the Secret, never the variable,
    and no setting exists for it: a credential with a Smarter Secret has one source. So the init Job (``job-init``)
    alone holds them, and :func:`forbidden_credentials` reports them in any other pod. A test keeps the members equal
    to the variables that those commands read.
    """

    LLMTOOL_BRAVE_SEARCH = "APP_LLMTOOL_BRAVE_SEARCH_API_KEY"
    """``initialize_llmtool_api_keys`` stores it as the Secret ``brave_search_api_key``."""

    LLMTOOL_TAVILY = "APP_LLMTOOL_TAVILY_API_KEY"
    """``initialize_llmtool_api_keys`` stores it as the Secret ``tavily_api_key``."""

    PROVIDER_ANTHROPIC = "APP_PROVIDER_ANTHROPIC_API_KEY"
    """``initialize_providers`` stores it as the Secret ``anthropic_api_key``."""

    PROVIDER_COHERE = "APP_PROVIDER_COHERE_API_KEY"
    """``initialize_providers`` stores it as the Secret ``cohere_api_key``."""

    PROVIDER_FIREWORKS = "APP_PROVIDER_FIREWORKS_API_KEY"
    """``initialize_providers`` stores it as the Secret ``fireworks_api_key``."""

    PROVIDER_GEMINI = "APP_PROVIDER_GEMINI_API_KEY"
    """``initialize_providers`` stores it as the Secret ``gemini_api_key``."""

    PROVIDER_GOOGLE_MAPS = "APP_PROVIDER_GOOGLE_MAPS_API_KEY"
    """``initialize_providers`` stores it as the Secret ``google_maps_api_key``."""

    PROVIDER_GOOGLE_SERVICE_ACCOUNT = "APP_PROVIDER_GOOGLE_SERVICE_ACCOUNT_B64"
    """``initialize_providers`` stores it as the Secret ``google_service_account``."""

    PROVIDER_LLAMA = "APP_PROVIDER_LLAMA_API_KEY"
    """``initialize_providers`` stores it as the Secret ``llama_api_key``."""

    PROVIDER_MISTRAL = "APP_PROVIDER_MISTRAL_API_KEY"
    """``initialize_providers`` stores it as the Secret ``mistral_api_key``."""

    PROVIDER_OPENAI = "APP_PROVIDER_OPENAI_API_KEY"
    """``initialize_providers`` stores it as the Secret ``openai_api_key``."""

    PROVIDER_TOGETHERAI = "APP_PROVIDER_TOGETHERAI_API_KEY"
    """``initialize_providers`` stores it as the Secret ``togetherai_api_key``."""

    VECTORSTORE_PINECONE = "APP_VECTORSTORE_PINECONE_API_KEY"
    """``initialize_vectorstore_providers`` stores it as the Secret ``pinecone_api_key``."""

    VECTORSTORE_QDRANT_CLOUD = "APP_VECTORSTORE_QDRANT_CLOUD_API_KEY"
    """``initialize_vectorstore_providers`` stores it as the Secret ``qdrant_cloud_api_key``."""


def bootstrap_variable_names(name: str) -> list[str]:
    """
    Return the environment variables that a bootstrap variable is read from, as ``get_env`` reads it.

    :param name: The variable, without the prefix, e.g. ``APP_PROVIDER_OPENAI_API_KEY``.
    :returns: ``SMARTER_<name>``, which the Helm chart sets, then ``<name>``.
    """
    names = [f"{ENVIRONMENT_PREFIX}{name}", name]
    return names


def is_bootstrap_variable(variable: str) -> bool:
    """
    Return whether an environment variable is one of :class:`SecretBootstrapVariable`, with or without its prefix.

    :param variable: The variable, e.g. ``SMARTER_APP_PROVIDER_OPENAI_API_KEY``.
    :returns: True if it is.
    """
    name = variable.removeprefix(ENVIRONMENT_PREFIX)
    retval = name in SecretBootstrapVariable.all()
    return retval


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

    That includes :class:`SecretBootstrapVariable`, named by their variable, in every pod but the init Job.

    A credential counts only if the process's environment sets one of its variables to a value. A value that the
    settings derive themselves, e.g. a generated Fernet key or the local environment's default database
    password, is not one that the worker was given, and doesn't count. Names only: never a value.

    :param settings: The settings.
    :param environ: The process's environment, e.g. ``os.environ``.
    :param pod_kind: The kind of pod, e.g. ``worker``. The tool worker's by default.
    :returns: The settings' names, and the bootstrap variables' names, sorted, or an empty list.
    """
    retval: list[str] = []
    for name, field in type(settings).model_fields.items():
        if not is_credential(field):
            continue
        if may_hold(field, pod_kind):
            continue
        if is_given(environ, environment_variables(name, field)):
            retval.append(name)
    if pod_kind != SmarterKubernetesPodKinds.JOB_INIT:
        for bootstrap_name in SecretBootstrapVariable.all():
            for variable in bootstrap_variable_names(bootstrap_name):
                if is_given(environ, [variable]):
                    retval.append(variable)
    retval.sort()
    return retval


def credential_holders_by_variable(settings_class: type[BaseModel]) -> dict[str, list[str]]:
    """
    Map each credential's environment variables to the kinds of pod that may hold it: what the Helm chart reads.

    ``make chart-credentials`` writes it to ``helm/charts/smarter/files/credentials.json``, and a test fails when
    that file is out of date. The chart gives each pod's Secret only the variables that name its kind.

    :param settings_class: The settings' class, :class:`smarter.common.conf.settings.Settings`.
    :returns: Each variable, sorted, and its pod kinds, sorted. A credential that no pod holds maps to an empty list.
        Each of :class:`SecretBootstrapVariable` maps to the init Job alone.
    """
    retval: dict[str, list[str]] = {}
    for name, field in settings_class.model_fields.items():
        if not is_credential(field):
            continue
        holders = credential_holders(field) or frozenset()
        pods = sorted(holders)
        for variable in environment_variables(name, field):
            retval[variable] = pods
    for bootstrap_name in SecretBootstrapVariable.all():
        variable = f"{ENVIRONMENT_PREFIX}{bootstrap_name}"
        retval[variable] = [SmarterKubernetesPodKinds.JOB_INIT]
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
    "SecretBootstrapVariable",
    "HeldBy",
    "bootstrap_variable_names",
    "credential_holders",
    "credential_holders_by_variable",
    "environment_variables",
    "forbidden_credentials",
    "is_bootstrap_variable",
    "is_given",
    "is_credential",
    "may_hold",
    "render_chart_credentials",
    "restricted_workers_may_hold",
    "write_chart_credentials",
]
