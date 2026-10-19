"""
Record locators, and the web console pages that they lead to.

A record locator identifies one row of a Smarter resource, e.g. ``llmclient-rMTAwMDAxMwx``: the
lower-cased name of its Django model class, a hyphen, and the row's hashed id. A manifest returns it
as ``status.recordLocator``. See
:attr:`smarter.lib.django.models.timestamped_model.TimestampedModel.record_locator`.

Most web console pages of a resource are addressed by the same hashed id, so that a record locator
is enough to build the url of the resource's page, without a database query:

.. code-block:: python

    from smarter.lib.manifest.record_locator import console_url

    console_url("llmclient-rMTAwMDAxMwx")
    # '/workbench/llm-clients/rMTAwMDAxMwx/prompt/'

The exceptions are an api key (:class:`smarter.lib.drf.models.SmarterAuthToken`), whose record
locator ends with its ``key_id``, and an Extension, whose page is addressed by its slug, which is
read from the database.
"""

from typing import Callable, Optional

from django.conf import settings
from django.urls import NoReverseMatch

from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib import logging
from smarter.lib.django.shortcuts import reverse

logger = logging.getLogger(__name__)
logger_prefix = formatted_text(__name__)

ConsolePath = Callable[[str], Optional[str]]
"""Builds the path of a resource's web console page from the part of its record locator after the prefix."""


def record_locator_prefix(model_class: type) -> str:
    """
    The prefix of a model's record locators: the lower-cased name of its class, e.g. ``llmclient``.

    :param model_class: The Django model class, e.g. :class:`smarter.apps.llmclient.models.LLMClient`.
    :type model_class: type
    :returns: The prefix, without the hyphen.
    :rtype: str
    """
    return model_class.__name__.lower()


def parse_record_locator(record_locator: str) -> tuple[str, str]:
    """
    Split a record locator into its prefix and the rest, usually a hashed id.

    .. code-block:: python

        parse_record_locator("llmclient-rMTAwMDAxMwx")
        # ('llmclient', 'rMTAwMDAxMwx')

    The prefix is everything before the first hyphen, because a model's class name has none, and
    the rest may have some, e.g. the ``key_id`` of an api key.

    :param record_locator: The record locator.
    :type record_locator: str
    :returns: The prefix and the rest.
    :rtype: tuple[str, str]
    :raises ValueError: If the record locator has no prefix, or nothing after it.
    """
    prefix, _, rest = (record_locator or "").partition("-")
    if not prefix or not rest:
        raise ValueError(f"Not a record locator: {record_locator!r}")
    return prefix, rest


def by_hashed_id(namespace: str, name: str) -> ConsolePath:
    """
    A :data:`ConsolePath` for a page whose url has the resource's ``hashed_id``.

    :param namespace: The url namespace, e.g. ``GuardrailReverseNames.namespace``.
    :type namespace: str
    :param name: The url name, e.g. ``GuardrailReverseNames.detailview``.
    :type name: str
    :returns: The function.
    :rtype: ConsolePath
    """

    def path(hashed_id: str) -> Optional[str]:
        return reverse(f"{namespace}:{name}", kwargs={"hashed_id": hashed_id}, urlconf=settings.ROOT_URLCONF)

    return path


def console_paths() -> dict[str, ConsolePath]:
    """
    The web console page of each kind of resource that has one, by record locator prefix.

    The views are imported here, not at module level, because the url modules import the apps' views,
    which import the manifest brokers, which import this module.

    :returns: A :data:`ConsolePath` for each record locator prefix.
    :rtype: dict[str, ConsolePath]
    """
    # pylint: disable=import-outside-toplevel
    from smarter.apps.account.models import Budget
    from smarter.apps.account.views.budget.urls import BudgetReverseNames
    from smarter.apps.connection.models import ApiConnection, SqlConnection
    from smarter.apps.connection.urls import ConnectionReverseNames
    from smarter.apps.guardrail.models import Guardrail
    from smarter.apps.guardrail.urls import GuardrailReverseNames
    from smarter.apps.llmclient.models import LLMClient, LLMClientCustomDomain
    from smarter.apps.llmclient.urls import LLMClientReverseNames
    from smarter.apps.llmhost.models import LLMHost, LLMHostCompute
    from smarter.apps.llmhost.urls import LLMHostReverseNames
    from smarter.apps.llmtool.extension.views import detail_url as extension_detail_url
    from smarter.apps.llmtool.models import Extension, PluginMeta
    from smarter.apps.llmtool.urls import PluginReverseNames
    from smarter.apps.mcpclient.models import MCPClient
    from smarter.apps.mcpclient.urls import MCPClientReverseNames
    from smarter.apps.orchestrator.models import Orchestrator
    from smarter.apps.orchestrator.urls import OrchestratorReverseNames
    from smarter.apps.prompt.urls import PromptReverseNames
    from smarter.apps.provider.models import Provider
    from smarter.apps.provider.urls import ProviderReverseNames
    from smarter.apps.proxy.models import Proxy
    from smarter.apps.proxy.urls import ProxyReverseNames
    from smarter.apps.secret.models import Secret
    from smarter.apps.secret.urls import SecretReverseNames
    from smarter.apps.vectorsearch.models import Vectorsearch
    from smarter.apps.vectorsearch.urls import VectorsearchReverseNames
    from smarter.apps.vectorstore.models import VectorstoreMeta
    from smarter.apps.vectorstore.urls import VectorstoreReverseNames
    from smarter.lib.drf.models import SmarterAuthToken
    from smarter.lib.drf.urls import AuthTokenReverseNames

    def auth_token_path(key_id: str) -> Optional[str]:
        return reverse(
            f"{AuthTokenReverseNames.namespace}:{AuthTokenReverseNames.detailview}",
            kwargs={"authtoken_id": key_id},
            urlconf=settings.ROOT_URLCONF,
        )

    def extension_path(hashed_id: str) -> Optional[str]:
        extension_id = Extension.id_from_hashed_id(hashed_id)
        slug = Extension.objects.filter(pk=extension_id).values_list("slug", flat=True).first()
        return extension_detail_url(slug) if slug else None

    pages: dict[type, ConsolePath] = {
        ApiConnection: by_hashed_id(ConnectionReverseNames.namespace, ConnectionReverseNames.api_detailview),
        Budget: by_hashed_id(BudgetReverseNames.namespace, BudgetReverseNames.detailview),
        Extension: extension_path,
        Guardrail: by_hashed_id(GuardrailReverseNames.namespace, GuardrailReverseNames.detailview),
        LLMClient: by_hashed_id(PromptReverseNames.namespace, PromptReverseNames.chat_by_hashed_id),
        LLMClientCustomDomain: by_hashed_id(
            LLMClientReverseNames.namespace, LLMClientReverseNames.custom_domain_detailview
        ),
        LLMHost: by_hashed_id(LLMHostReverseNames.namespace, LLMHostReverseNames.detailview),
        LLMHostCompute: by_hashed_id(LLMHostReverseNames.namespace, LLMHostReverseNames.compute_detailview),
        MCPClient: by_hashed_id(MCPClientReverseNames.namespace, MCPClientReverseNames.detailview),
        Orchestrator: by_hashed_id(OrchestratorReverseNames.namespace, OrchestratorReverseNames.detailview),
        PluginMeta: by_hashed_id(PluginReverseNames.namespace, PluginReverseNames.detailview),
        Provider: by_hashed_id(ProviderReverseNames.namespace, ProviderReverseNames.detailview),
        Proxy: by_hashed_id(ProxyReverseNames.namespace, ProxyReverseNames.detailview),
        Secret: by_hashed_id(SecretReverseNames.namespace, SecretReverseNames.detailview),
        SmarterAuthToken: auth_token_path,
        SqlConnection: by_hashed_id(ConnectionReverseNames.namespace, ConnectionReverseNames.sql_detailview),
        Vectorsearch: by_hashed_id(VectorsearchReverseNames.namespace, VectorsearchReverseNames.detailview),
        VectorstoreMeta: by_hashed_id(VectorstoreReverseNames.namespace, VectorstoreReverseNames.detailview),
    }
    return {record_locator_prefix(model_class): path for model_class, path in pages.items()}


def console_url(record_locator: Optional[str]) -> Optional[str]:
    """
    The path of a resource's page in the web console, from its record locator.

    It is a path, not an absolute url, because the web console's own pages use it. A kind of resource
    that has no page, e.g. a Prompt, or a page that this platform does not serve, e.g. the Proxy pages
    while proxies are turned off, has none.

    .. code-block:: python

        console_url("guardrail-rNQx")
        # '/guardrail/guardrails/rNQx/'

    :param record_locator: The resource's record locator, e.g. ``llmclient-rMTAwMDAxMwx``.
    :type record_locator: Optional[str]
    :returns: The path, or None.
    :rtype: Optional[str]
    """
    if not record_locator:
        return None
    try:
        prefix, rest = parse_record_locator(record_locator)
    except ValueError as e:
        logger.warning("%s.console_url() %s", logger_prefix, e)
        return None
    path = console_paths().get(prefix)
    if path is None:
        return None
    try:
        return path(rest)
    except NoReverseMatch as e:
        logger.debug("%s.console_url() no web console page for %s: %s", logger_prefix, record_locator, e)
        return None


__all__ = [
    "ConsolePath",
    "by_hashed_id",
    "console_paths",
    "console_url",
    "parse_record_locator",
    "record_locator_prefix",
]
