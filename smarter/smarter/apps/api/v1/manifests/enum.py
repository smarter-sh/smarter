"""Smarter API V1 Manifests Enumerations."""

import smarter.lib.logging as logging
from smarter.apps.account.manifest.models.account.const import (
    MANIFEST_KIND as ACCOUNT_MANIFEST_KIND,
)
from smarter.apps.account.manifest.models.user.const import (
    MANIFEST_KIND as USER_MANIFEST_KIND,
)
from smarter.apps.chatbot.manifest.models.chatbot.const import (
    MANIFEST_KIND as CHATBOT_MANIFEST_KIND,
)
from smarter.apps.connection.manifest.models.api_connection.const import (
    MANIFEST_KIND as APICONNECTION_MANIFEST_KIND,
)
from smarter.apps.connection.manifest.models.sql_connection.const import (
    MANIFEST_KIND as SQLCONNECTION_MANIFEST_KIND,
)
from smarter.apps.plugin.manifest.models.api_plugin.const import (
    MANIFEST_KIND as APIPLUGIN_MANIFEST_KIND,
)
from smarter.apps.plugin.manifest.models.sql_plugin.const import (
    MANIFEST_KIND as SQLPLUGIN_MANIFEST_KIND,
)
from smarter.apps.plugin.manifest.models.static_plugin.const import (
    MANIFEST_KIND as STATICPLUGIN_MANIFEST_KIND,
)
from smarter.apps.prompt.manifest.models.chat.const import (
    MANIFEST_KIND as CHAT_MANIFEST_KIND,
)
from smarter.apps.prompt.manifest.models.chat_history.const import (
    MANIFEST_KIND as CHAT_HISTORY_MANIFEST_KIND,
)
from smarter.apps.prompt.manifest.models.chat_plugin_usage.const import (
    MANIFEST_KIND as CHAT_PLUGIN_USAGE_MANIFEST_KIND,
)
from smarter.apps.prompt.manifest.models.chat_tool_call.const import (
    MANIFEST_KIND as CHAT_TOOL_CALL_MANIFEST_KIND,
)
from smarter.apps.provider.manifest.models.provider.const import (
    MANIFEST_KIND as PROVIDER_MANIFEST_KIND,
)
from smarter.apps.secret.manifest.models.secret.const import (
    MANIFEST_KIND as SECRET_MANIFEST_KIND,
)
from smarter.apps.vectorstore.manifest.models.vectorstore.const import (
    MANIFEST_KIND as VECTORSTORE_MANIFEST_KIND,
)
from smarter.common.exceptions import SmarterValueError
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.manifest.models.auth_token.const import (
    MANIFEST_KIND as AUTH_TOKEN_MANIFEST_KIND,
)
from smarter.lib.manifest.enum import SmarterEnumAbstract

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.API_LOGGING])


class SAMKinds(SmarterEnumAbstract):
    """
    Smarter manifest kinds enumeration. This is the comprehensive list of all
    manifest kinds supported by the Smarter platform.

    Each manifest kind corresponds to a specific resource type within the
    Smarter ecosystem, such as plugins, connections, account resources, chat
    resources, and provider resources.

    Attributes:
        STATIC_PLUGIN: Represents a static plugin manifest kind.
        API_PLUGIN: Represents an API plugin manifest kind.
        SQL_PLUGIN: Represents an SQL plugin manifest kind.
        API_CONNECTION: Represents an API connection manifest kind.
        SQL_CONNECTION: Represents an SQL connection manifest kind.
        ACCOUNT: Represents an account manifest kind.
        AUTH_TOKEN: Represents an authentication token manifest kind.
        USER: Represents a user manifest kind.
        SECRET: Represents a secret manifest kind.
        CHAT: Represents a chat manifest kind.
        CHAT_HISTORY: Represents a chat history manifest kind.
        CHAT_PLUGIN_USAGE: Represents a chat plugin usage manifest kind.
        CHAT_TOOL_CALL: Represents a chat tool call manifest kind.
        CHATBOT: Represents a chatbot manifest kind.
        PROVIDER: Represents a provider manifest kind.

    Methods:
        str_to_kind(cls, kind_str: str) -> "SAMKinds":
            Convert a string to a SAMKinds enumeration value.
        all_plugins(cls) -> list:
            Return a list of all plugin manifest kinds.
        all_connections(cls) -> list:
            Return a list of all connection manifest kinds.
        all_slugs(cls) -> list:
            Return a list of all manifest kind slugs (singular and plural).
        singular_slugs(cls) -> list:
            Return a list of singular manifest kind slugs.
        plural_slugs(cls) -> list:
            Return a list of plural manifest kind slugs.
        from_url(cls, url) -> str:
            Extract the manifest kind from a URL.
    """

    # plugins
    STATIC_PLUGIN = STATICPLUGIN_MANIFEST_KIND
    API_PLUGIN = APIPLUGIN_MANIFEST_KIND
    SQL_PLUGIN = SQLPLUGIN_MANIFEST_KIND

    # connections
    API_CONNECTION = APICONNECTION_MANIFEST_KIND
    SQL_CONNECTION = SQLCONNECTION_MANIFEST_KIND

    # account resources
    ACCOUNT = ACCOUNT_MANIFEST_KIND
    AUTH_TOKEN = AUTH_TOKEN_MANIFEST_KIND
    USER = USER_MANIFEST_KIND
    SECRET = SECRET_MANIFEST_KIND

    # chat resources
    CHAT = CHAT_MANIFEST_KIND
    CHAT_HISTORY = CHAT_HISTORY_MANIFEST_KIND
    CHAT_PLUGIN_USAGE = CHAT_PLUGIN_USAGE_MANIFEST_KIND
    CHAT_TOOL_CALL = CHAT_TOOL_CALL_MANIFEST_KIND
    CHATBOT = CHATBOT_MANIFEST_KIND

    # provider resources
    PROVIDER = PROVIDER_MANIFEST_KIND

    # vectorstore resources
    VECTORSTORE = VECTORSTORE_MANIFEST_KIND

    @classmethod
    def str_to_kind(cls, kind_str: str) -> "SAMKinds":
        """
        Convert a string to a SAMKinds enumeration value.
        """
        if isinstance(kind_str, bytes):
            kind_str = kind_str.decode("utf-8")

        # Try case-insensitive key lookup
        for _, member in cls.__members__.items():
            if member.value.lower() == kind_str.lower():
                return member

        raise SmarterValueError(f"Invalid SAMKinds value: {kind_str}.")

    @classmethod
    def all_plugins(cls):
        return [cls.STATIC_PLUGIN, cls.API_PLUGIN, cls.SQL_PLUGIN]

    @classmethod
    def all_connections(cls):
        return [cls.API_CONNECTION, cls.SQL_CONNECTION]
