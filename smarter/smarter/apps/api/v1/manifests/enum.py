"""Smarter API V1 Manifests Enumerations."""

import re

import inflection

from smarter.apps.account.manifest.models.account.const import (
    MANIFEST_KIND as ACCOUNT_MANIFEST_KIND,
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
from smarter.apps.llmclient.manifest.models.llmclient.const import (
    MANIFEST_KIND as LLM_CLIENT_MANIFEST_KIND,
)
from smarter.apps.llmhost.manifest.models.llmhost.const import (
    MANIFEST_KIND as LLM_HOST_MANIFEST_KIND,
)
from smarter.apps.mcpclient.manifest.models.mcpclient.const import (
    MANIFEST_KIND as MCP_CLIENT_MANIFEST_KIND,
)
from smarter.apps.orchestrator.manifest.models.orchestrator.const import (
    MANIFEST_KIND as ORCHESTRATOR_MANIFEST_KIND,
)
from smarter.apps.plugin.manifest.models.api_plugin.const import (
    MANIFEST_KIND as APIPLUGIN_MANIFEST_KIND,
)
from smarter.apps.plugin.manifest.models.skill_plugin.const import (
    MANIFEST_KIND as SKILLPLUGIN_MANIFEST_KIND,
)
from smarter.apps.plugin.manifest.models.sql_plugin.const import (
    MANIFEST_KIND as SQLPLUGIN_MANIFEST_KIND,
)
from smarter.apps.plugin.manifest.models.static_plugin.const import (
    MANIFEST_KIND as STATICPLUGIN_MANIFEST_KIND,
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
        API_CONNECTION: API connection manifest.
        SQL_CONNECTION: SQL connection manifest.
        ACCOUNT: Account manifest.
        AUTH_TOKEN: Authentication token manifest.
        USER: User manifest.
        SECRET: Secret manifest.
        GUARDRAIL: Guardrail manifest.
        PROMPT: Prompt manifest.
        LLM_CLIENT: LLM client manifest.
        LLM_HOST: LLM host manifest.
        MCP_CLIENT: MCP client manifest.
        PROVIDER: AI provider manifest.
        PROXY: Proxy manifest.
        VECTORSTORE: Vector store manifest.

    Class Methods:
        str_to_kind(kind_str):
            Convert a manifest kind string into the corresponding
            :class:`SAMKinds` enumeration value.

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

    # connections
    API_CONNECTION = APICONNECTION_MANIFEST_KIND
    SQL_CONNECTION = SQLCONNECTION_MANIFEST_KIND

    # account resources
    ACCOUNT = ACCOUNT_MANIFEST_KIND
    AUTH_TOKEN = AUTH_TOKEN_MANIFEST_KIND
    USER = USER_MANIFEST_KIND
    SECRET = SECRET_MANIFEST_KIND

    GUARDRAIL = GUARDRAIL_MANIFEST_KIND

    # prompt resources
    PROMPT = PROMPT_MANIFEST_KIND
    LLM_CLIENT = LLM_CLIENT_MANIFEST_KIND
    LLM_HOST = LLM_HOST_MANIFEST_KIND
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
    def all_plugins(cls):
        return [cls.STATIC_PLUGIN, cls.API_PLUGIN, cls.SQL_PLUGIN]

    @classmethod
    def all_connections(cls):
        return [cls.API_CONNECTION, cls.SQL_CONNECTION]
