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

        apply_order():
            Return the order in which to apply manifests of several kinds,
            each kind after the kinds that its manifests may name.

        apply_rank(kind):
            Return a kind's position in :meth:`apply_order`.

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

    @classmethod
    def apply_order(cls) -> tuple[str, ...]:
        """
        Return the order in which to apply manifests of several kinds: each kind after the kinds that its manifests may name.

        SAM resources refer to one another **by name**. A SqlPlugin's ``spec.connection`` is the name of a
        SqlConnection, and a SqlConnection's ``password`` is the name of a Secret. A broker resolves each
        name when it applies the manifest, so the resource that is named must already exist. A set of
        manifests, e.g. a project such as `Stackademy <https://github.com/smarter-sh/stackademy>`__, can
        only be applied in an order where every resource comes after the resources that it names. This
        is that order, for every kind. It is part of the definition of SAM: a new kind needs a deliberate
        place in it, and ``test_enum.py`` fails until it has one.

        The order, kind by kind, and why:

        #. **Account**. Every other resource belongs to an account, so the account comes first. It
           names nothing.
        #. **User**. A user is a member of an account, and owns the resources that it applies.
        #. **AuthToken**. An api key's ``spec.username`` names its User. It comes before the LLMClients,
           whose ``spec.apiKey`` may name one.
        #. **Secret**. A Secret holds a password or an api key, and names nothing, but nearly everything
           after it may name a Secret: Providers, Proxies, LLMHosts, Connections, MCPClients,
           Vectorsearches and the search plugins. So it comes before all of them.
        #. **Provider**. An LLM provider names the Secret that holds its api key. LLMClients,
           Guardrails, Proxies and Vectorstores name a Provider, so it comes before them.
        #. **Proxy**. ``spec.provider`` names a Provider, and ``spec.apiKey`` a Secret.
        #. **LLMHostCompute**. A kind of node, and its node group. It names nothing, but an LLMHost's
           ``spec.compute`` names one.
        #. **LLMHost**. A self-hosted model. ``spec.compute`` names an LLMHostCompute, and its
           ``tokenSecret`` and ``apiKeySecret`` name Secrets.
        #. **SqlConnection**. ``password`` and ``proxyPassword`` name Secrets. SqlPlugins name it.
        #. **ApiConnection**. ``apiKey`` and ``proxyPassword`` name Secrets. ApiPlugins name it.
        #. **Guardrail**. ``spec.config.provider`` names the Provider that its semantic, moderation and
           llm_judge strategies call. LLMClients name it in ``spec.guardrails``.
        #. **Vectorstore**. ``spec.provider`` names the Provider of its embeddings, and its database may
           name a Secret.
        #. **Vectorsearch**. ``vectorstore_name`` names a Vectorstore, so it comes after them, and
           ``auth_secret_name`` names a Secret.
        #. **MCPClient**. ``credentials`` names a Secret. LLMClients name it in ``spec.mcpClients``.
        #. **The plugins: StaticPlugin, SqlPlugin, ApiPlugin, SkillPlugin, WebsearchPlugin and
           ImageSearchPlugin**. A SqlPlugin's ``spec.connection`` names a SqlConnection, an ApiPlugin's
           an ApiConnection, and a WebsearchPlugin's and an ImageSearchPlugin's ``apiKey`` a Secret. A
           StaticPlugin and a SkillPlugin name nothing. All of them come after the Connections and
           before the LLMClients, whose ``spec.plugins`` names them.
        #. **CustomDomain**. A domain that serves LLMClients. It names nothing, but an LLMClient's
           ``customDomain`` names its domain, so it comes before them.
        #. **LLMClient**. It names the most kinds: a Provider, and its Plugins, Guardrails, MCPClients,
           CustomDomain and AuthToken. It comes after all of them.
        #. **Prompt**. A chat session, whose ``spec.llmclient`` names the LLMClient that it talks to.
        #. **Orchestrator**. Each of ``spec.config.harnesses`` names an LLMClient, by ``llmClientName``.
        #. **Budget**. Last, because ``spec.resources`` can name nearly any kind of resource: Accounts,
           Users, Connections, LLMClients, LLMHosts, LLMHostComputes, MCPClients, Orchestrators,
           Providers, Proxies, Vectorsearches and every kind of plugin. Applied any earlier, a Budget
           could name a resource that doesn't exist yet.

        Kinds that name nothing in common (e.g. the plugins among themselves) may be applied in any
        order. :meth:`apply_rank` gives each kind's position, and a kind that is not listed, i.e. not a
        SAM kind, is applied last. ``manage.py load_from_github`` sorts a repository's manifests by it:

        .. code-block:: python

            sorted(manifests, key=lambda m: SAMKinds.apply_rank(m["kind"]))

        :returns: The kinds' values, in the order in which to apply them.
        :rtype: tuple[str, ...]
        """
        return (
            cls.ACCOUNT.value,
            cls.USER.value,
            cls.AUTH_TOKEN.value,
            cls.SECRET.value,
            cls.PROVIDER.value,
            cls.PROXY.value,
            cls.LLM_HOST_COMPUTE.value,
            cls.LLM_HOST.value,
            cls.SQL_CONNECTION.value,
            cls.API_CONNECTION.value,
            cls.GUARDRAIL.value,
            cls.VECTORSTORE.value,
            cls.VECTORSEARCH.value,
            cls.MCP_CLIENT.value,
            cls.STATIC_PLUGIN.value,
            cls.SQL_PLUGIN.value,
            cls.API_PLUGIN.value,
            cls.SKILL_PLUGIN.value,
            cls.WEBSEARCH_PLUGIN.value,
            cls.IMAGE_SEARCH_PLUGIN.value,
            cls.CUSTOM_DOMAIN.value,
            cls.LLM_CLIENT.value,
            cls.PROMPT.value,
            cls.ORCHESTRATOR.value,
            cls.BUDGET.value,
        )

    @classmethod
    def apply_rank(cls, kind: Union[str, "SAMKinds"]) -> int:
        """
        Return the position of a kind in :meth:`apply_order`.

        .. code-block:: python

            SAMKinds.apply_rank(SAMKinds.SECRET) < SAMKinds.apply_rank("SqlConnection")  # True
            SAMKinds.apply_rank("NoSuchKind") == len(SAMKinds.apply_order())  # True: applied last

        :param kind: The kind, as a member or its value, in any case.
        :type kind: Union[str, SAMKinds]
        :returns: The kind's position, or the length of :meth:`apply_order` for a kind that isn't a SAM kind,
            so that it is applied last.
        :rtype: int
        """
        value = (kind.value if isinstance(kind, SAMKinds) else str(kind)).lower()
        order = [item.lower() for item in cls.apply_order()]
        return order.index(value) if value in order else len(order)
