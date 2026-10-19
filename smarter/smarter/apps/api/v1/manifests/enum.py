"""Smarter API V1 Manifests Enumerations."""

import re
from typing import Union

import inflection

from smarter.apps.account.manifest.models.account.const import (
    MANIFEST_KIND as ACCOUNT_MANIFEST_KIND,
)
from smarter.apps.account.manifest.models.budget.const import (
    MANIFEST_KIND as BUDGET_MANIFEST_KIND,
)
from smarter.apps.account.manifest.models.user.const import (
    MANIFEST_KIND as USER_MANIFEST_KIND,
)
from smarter.apps.connection.manifest.models.api_connection.const import (
    MANIFEST_KIND as APICONNECTION_MANIFEST_KIND,
)
from smarter.apps.connection.manifest.models.sql_connection.const import (
    MANIFEST_KIND as SQLCONNECTION_MANIFEST_KIND,
)
from smarter.apps.guardrail.manifest.models.guardrail.const import (
    MANIFEST_KIND as GUARDRAIL_MANIFEST_KIND,
)
from smarter.apps.llmclient.manifest.models.custom_domain.const import (
    MANIFEST_KIND as CUSTOM_DOMAIN_MANIFEST_KIND,
)
from smarter.apps.llmclient.manifest.models.llmclient.const import (
    MANIFEST_KIND as LLM_CLIENT_MANIFEST_KIND,
)
from smarter.apps.llmhost.manifest.models.llmhost.const import (
    MANIFEST_KIND as LLM_HOST_MANIFEST_KIND,
)
from smarter.apps.llmhost.manifest.models.llmhost_compute.const import (
    MANIFEST_KIND as LLM_HOST_COMPUTE_MANIFEST_KIND,
)
from smarter.apps.llmtool.manifest.models.api_plugin.const import (
    MANIFEST_KIND as APIPLUGIN_MANIFEST_KIND,
)
from smarter.apps.llmtool.manifest.models.image_search_plugin.const import (
    MANIFEST_KIND as IMAGESEARCHPLUGIN_MANIFEST_KIND,
)
from smarter.apps.llmtool.manifest.models.skill_plugin.const import (
    MANIFEST_KIND as SKILLPLUGIN_MANIFEST_KIND,
)
from smarter.apps.llmtool.manifest.models.sql_plugin.const import (
    MANIFEST_KIND as SQLPLUGIN_MANIFEST_KIND,
)
from smarter.apps.llmtool.manifest.models.static_plugin.const import (
    MANIFEST_KIND as STATICPLUGIN_MANIFEST_KIND,
)
from smarter.apps.llmtool.manifest.models.websearch_plugin.const import (
    MANIFEST_KIND as WEBSEARCHPLUGIN_MANIFEST_KIND,
)
from smarter.apps.mcpclient.manifest.models.mcpclient.const import (
    MANIFEST_KIND as MCP_CLIENT_MANIFEST_KIND,
)
from smarter.apps.orchestrator.manifest.models.orchestrator.const import (
    MANIFEST_KIND as ORCHESTRATOR_MANIFEST_KIND,
)
from smarter.apps.prompt.manifest.models.prompt.const import (
    MANIFEST_KIND as PROMPT_MANIFEST_KIND,
)
from smarter.apps.provider.manifest.models.provider.const import (
    MANIFEST_KIND as PROVIDER_MANIFEST_KIND,
)
from smarter.apps.proxy.manifest.models.proxy.const import (
    MANIFEST_KIND as PROXY_MANIFEST_KIND,
)
from smarter.apps.secret.manifest.models.secret.const import (
    MANIFEST_KIND as SECRET_MANIFEST_KIND,
)
from smarter.apps.vectorsearch.manifest.models.vectorsearch.const import (
    MANIFEST_KIND as VECTORSEARCH_MANIFEST_KIND,
)
from smarter.apps.vectorstore.manifest.models.vectorstore.const import (
    MANIFEST_KIND as VECTORSTORE_MANIFEST_KIND,
)
from smarter.common.exceptions import SmarterValueError
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.manifest.models.auth_token.const import (
    MANIFEST_KIND as AUTH_TOKEN_MANIFEST_KIND,
)
from smarter.lib.manifest.enum import SmarterEnumAbstract

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.API_LOGGING])


SAM_KIND_ICON_DEFAULT = "abstract-26"
"""The icon of a kind that has none of its own in :data:`SAM_KIND_ICONS`, e.g. an Extension, which isn't a SAM kind."""

SAM_KIND_ICONS: dict[str, str] = {
    # plugins
    STATICPLUGIN_MANIFEST_KIND: "document",
    APIPLUGIN_MANIFEST_KIND: "code",
    SKILLPLUGIN_MANIFEST_KIND: "wrench",
    SQLPLUGIN_MANIFEST_KIND: "file-sheet",
    WEBSEARCHPLUGIN_MANIFEST_KIND: "magnifier",
    IMAGESEARCHPLUGIN_MANIFEST_KIND: "picture",
    # connections
    APICONNECTION_MANIFEST_KIND: "router",
    SQLCONNECTION_MANIFEST_KIND: "data",
    # account resources
    ACCOUNT_MANIFEST_KIND: "bank",
    AUTH_TOKEN_MANIFEST_KIND: "key",
    BUDGET_MANIFEST_KIND: "wallet",
    USER_MANIFEST_KIND: "profile-circle",
    SECRET_MANIFEST_KIND: "lock-2",
    GUARDRAIL_MANIFEST_KIND: "shield-tick",
    # prompt resources
    PROMPT_MANIFEST_KIND: "message-text-2",
    LLM_CLIENT_MANIFEST_KIND: "artificial-intelligence",
    CUSTOM_DOMAIN_MANIFEST_KIND: "share",
    LLM_HOST_MANIFEST_KIND: "technology-4",
    LLM_HOST_COMPUTE_MANIFEST_KIND: "cube-3",
    MCP_CLIENT_MANIFEST_KIND: "switch",
    ORCHESTRATOR_MANIFEST_KIND: "category",
    # provider, proxy and vectorstore resources
    PROVIDER_MANIFEST_KIND: "cloud",
    PROXY_MANIFEST_KIND: "exit-right-corner",
    VECTORSEARCH_MANIFEST_KIND: "filter-search",
    VECTORSTORE_MANIFEST_KIND: "cube-2",
}
"""
The icon of each SAM kind in the web console: the name of a `Keen Icons <https://keenthemes.com/keenicons>`__.

icon, without its ``ki-`` prefix, which the console's global stylesheet provides, e.g. ``<i class="ki-outline
ki-lock-2"></i>`` for a Secret. Each kind has its own. See :meth:`SAMKinds.icon`.
"""


class SAMKinds(SmarterEnumAbstract):
    """
    Enumeration of all Smarter Application Manifest (SAM) resource kinds.

    ``SAMKinds`` defines the complete set of manifest kinds recognized by the
    Smarter platform. Each value identifies the type of resource described by
    a Smarter Application Manifest (SAM), allowing manifests to be validated,
    discovered, and routed to the appropriate resource handler.

    Manifest kinds are organized into several functional categories:

    - **Plugins** provide executable capabilities, such as Static, API,
      Skill, and SQL plugins.
    - **Connections** define connectivity to external services and databases.
    - **Account resources** manage users, accounts, authentication tokens,
      secrets, and guardrails.
    - **Prompt resources** configure language model infrastructure, including
      prompts, LLM clients, LLM hosts, and MCP clients.
    - **Provider resources** describe AI model providers.
    - **Proxy resources** define proxy services.
    - **Vectorstore resources** configure vector database integrations.

    This enumeration is used throughout the platform for manifest parsing,
    resource validation, URL resolution, CLI commands, and API dispatch.

    Attributes:
        STATIC_PLUGIN: Static plugin manifest.
        API_PLUGIN: API plugin manifest.
        SKILL_PLUGIN: Skill plugin manifest.
        SQL_PLUGIN: SQL plugin manifest.
        WEBSEARCH_PLUGIN: Websearch plugin manifest. Experimental.
        IMAGE_SEARCH_PLUGIN: Image search plugin manifest. Experimental.
        API_CONNECTION: API connection manifest.
        SQL_CONNECTION: SQL connection manifest.
        ACCOUNT: Account manifest.
        AUTH_TOKEN: Authentication token manifest.
        BUDGET: Budget manifest: spending limits enforced on the resources it lists.
        USER: User manifest.
        SECRET: Secret manifest.
        CUSTOM_DOMAIN: Custom domain manifest: a domain that serves LLMClients.
        GUARDRAIL: Guardrail manifest.
        PROMPT: Prompt manifest.
        LLM_CLIENT: LLM client manifest.
        LLM_HOST: LLM host manifest.
        LLM_HOST_COMPUTE: LLM host compute manifest: a kind of node, and node group.
        MCP_CLIENT: MCP client manifest.
        PROVIDER: AI provider manifest.
        PROXY: Proxy manifest.
        VECTORSTORE: Vector store manifest.

    Class Methods:
        str_to_kind(kind_str):
            Convert a manifest kind string into the corresponding
            :class:`SAMKinds` enumeration value.

        icon(kind):
            Return the kind's icon in the web console.

        all_plugins():
            Return the supported plugin manifest kinds.

        all_connections():
            Return the supported connection manifest kinds.

        all_slugs():
            Return all supported manifest kind URL slugs, including both
            singular and plural forms.

        singular_slugs():
            Return the singular manifest kind URL slugs.

        plural_slugs():
            Return the plural manifest kind URL slugs.

        from_url(url):
            Determine the manifest kind represented by a resource URL.
    """

    # plugins
    STATIC_PLUGIN = STATICPLUGIN_MANIFEST_KIND
    API_PLUGIN = APIPLUGIN_MANIFEST_KIND
    SKILL_PLUGIN = SKILLPLUGIN_MANIFEST_KIND
    SQL_PLUGIN = SQLPLUGIN_MANIFEST_KIND
    WEBSEARCH_PLUGIN = WEBSEARCHPLUGIN_MANIFEST_KIND
    IMAGE_SEARCH_PLUGIN = IMAGESEARCHPLUGIN_MANIFEST_KIND

    # connections
    API_CONNECTION = APICONNECTION_MANIFEST_KIND
    SQL_CONNECTION = SQLCONNECTION_MANIFEST_KIND

    # account resources
    ACCOUNT = ACCOUNT_MANIFEST_KIND
    AUTH_TOKEN = AUTH_TOKEN_MANIFEST_KIND
    BUDGET = BUDGET_MANIFEST_KIND
    USER = USER_MANIFEST_KIND
    SECRET = SECRET_MANIFEST_KIND

    GUARDRAIL = GUARDRAIL_MANIFEST_KIND

    # prompt resources
    PROMPT = PROMPT_MANIFEST_KIND
    LLM_CLIENT = LLM_CLIENT_MANIFEST_KIND
    CUSTOM_DOMAIN = CUSTOM_DOMAIN_MANIFEST_KIND
    LLM_HOST = LLM_HOST_MANIFEST_KIND
    LLM_HOST_COMPUTE = LLM_HOST_COMPUTE_MANIFEST_KIND
    MCP_CLIENT = MCP_CLIENT_MANIFEST_KIND
    ORCHESTRATOR = ORCHESTRATOR_MANIFEST_KIND

    # provider resources
    PROVIDER = PROVIDER_MANIFEST_KIND

    # proxy resources
    PROXY = PROXY_MANIFEST_KIND

    # vectorstore resources
    VECTORSEARCH = VECTORSEARCH_MANIFEST_KIND
    VECTORSTORE = VECTORSTORE_MANIFEST_KIND

    @classmethod
    def plural(cls, kind: str) -> str:
        """
        Returns the plural of the kind, pluralizing only its final.

        CamelCase token.

        example:

        SAMKinds.plural(SAMKinds.API_CONNECTION)  # "ApiConnection" -> "ApiConnections"
        """
        kind = SAMKinds.str_to_kind(kind)
        tokens = re.findall(r"[A-Z][a-z0-9]*|[a-z0-9]+", kind)
        if not tokens:
            return inflection.pluralize(kind)

        tokens[-1] = inflection.pluralize(tokens[-1])
        return "".join(tokens)

    @classmethod
    def str_to_kind(cls, kind_str: str) -> str:
        """Convert a string to a SAMKinds enumeration value."""
        if isinstance(kind_str, bytes):
            kind_str = kind_str.decode("utf-8")
        if not isinstance(kind_str, str):
            return None

        # Try case-insensitive key lookup
        for _, member in cls.__members__.items():
            if hasattr(member, "value") and isinstance(member.value, str) and member.value.lower() == kind_str.lower():
                return str(member)

        raise SmarterValueError(f"Invalid SAMKinds value: {kind_str}.")

    @classmethod
    def icon(cls, kind: Union[str, "SAMKinds"]) -> str:
        """
        Return the web console's icon of a kind of resource, e.g. for the cards of an LLMClient's architecture.

        The icon is a `Keen Icons <https://keenthemes.com/keenicons>`__ name, without its ``ki-`` prefix, which
        the web console's global stylesheet provides.

        .. code-block:: python

            SAMKinds.icon(SAMKinds.SECRET)  # "lock-2", i.e. <i class="ki-outline ki-lock-2"></i>
            SAMKinds.icon("sqlplugin")  # "file-sheet"
            SAMKinds.icon("Extension")  # "abstract-26", the default: an Extension isn't a SAM kind

        :param kind: The kind, as a member or its value, in any case.
        :type kind: Union[str, SAMKinds]
        :returns: The icon's name, or :data:`SAM_KIND_ICON_DEFAULT` for a kind that isn't a SAM kind.
        :rtype: str
        """
        value = kind.value if isinstance(kind, SAMKinds) else str(kind)
        icons = {key.lower(): icon for key, icon in SAM_KIND_ICONS.items()}
        return icons.get(value.lower(), SAM_KIND_ICON_DEFAULT)

    @classmethod
    def all_plugins(cls):
        return [
            cls.STATIC_PLUGIN,
            cls.API_PLUGIN,
            cls.SKILL_PLUGIN,
            cls.SQL_PLUGIN,
            cls.WEBSEARCH_PLUGIN,
            cls.IMAGE_SEARCH_PLUGIN,
        ]

    @classmethod
    def all_connections(cls):
        return [cls.API_CONNECTION, cls.SQL_CONNECTION]
