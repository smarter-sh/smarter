"""Smarter API V1 Manifests Enumerations."""

import logging
from urllib.parse import urlparse

from smarter.apps.account.manifest.models.account.const import (
    MANIFEST_KIND as ACCOUNT_MANIFEST_KIND,
)
from smarter.apps.account.manifest.models.secret.const import (
    MANIFEST_KIND as SECRET_MANIFEST_KIND,
)
from smarter.apps.account.manifest.models.user.const import (
    MANIFEST_KIND as USER_MANIFEST_KIND,
)
from smarter.apps.chatbot.manifest.models.chatbot.const import (
    MANIFEST_KIND as CHATBOT_MANIFEST_KIND,
)
from smarter.apps.plugin.manifest.models.api_connection.const import (
    MANIFEST_KIND as APICONNECTION_MANIFEST_KIND,
)
from smarter.apps.plugin.manifest.models.api_plugin.const import (
    MANIFEST_KIND as APIPLUGIN_MANIFEST_KIND,
)
from smarter.apps.plugin.manifest.models.sql_connection.const import (
    MANIFEST_KIND as SQLCONNECTION_MANIFEST_KIND,
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
from smarter.common.exceptions import SmarterValueError
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.manifest.models.auth_token.const import (
    MANIFEST_KIND as AUTH_TOKEN_MANIFEST_KIND,
)
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.manifest.enum import SmarterEnumAbstract


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.API_LOGGING) and level <= logging.INFO


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class SAMKinds(SmarterEnumAbstract):
    """Smarter manifest kinds enumeration."""

    STATIC_PLUGIN = STATICPLUGIN_MANIFEST_KIND
    API_PLUGIN = APIPLUGIN_MANIFEST_KIND
    SQL_PLUGIN = SQLPLUGIN_MANIFEST_KIND
    API_CONNECTION = APICONNECTION_MANIFEST_KIND
    SQL_CONNECTION = SQLCONNECTION_MANIFEST_KIND
    ACCOUNT = ACCOUNT_MANIFEST_KIND
    AUTH_TOKEN = AUTH_TOKEN_MANIFEST_KIND
    USER = USER_MANIFEST_KIND
    CHAT = CHAT_MANIFEST_KIND
    CHAT_HISTORY = CHAT_HISTORY_MANIFEST_KIND
    CHAT_PLUGIN_USAGE = CHAT_PLUGIN_USAGE_MANIFEST_KIND
    CHAT_TOOL_CALL = CHAT_TOOL_CALL_MANIFEST_KIND
    CHATBOT = CHATBOT_MANIFEST_KIND
    SECRET = SECRET_MANIFEST_KIND

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

    @classmethod
    def all_slugs(cls):
        return cls.singular_slugs() + cls.plural_slugs()

    @classmethod
    def singular_slugs(cls):
        return [slug.lower() for slug in cls.all_values()]

    @classmethod
    def plural_slugs(cls):
        return [f"{slug.lower()}s" for slug in cls.all_values()]

    @classmethod
    def from_url(cls, url) -> str:
        """
        Extract the manifest kind from a URL.
        example: http://localhost:8000/api/v1/cli/example_manifest/Account/
                http://platform.smarter.sh/api/v1/cli/whoami/
        """
        if isinstance(url, bytes):
            url = url.decode("utf-8")
        parsed_url = urlparse(url)
        path = parsed_url.path
        if isinstance(path, bytes):
            path = path.decode("utf-8")
        slugs = path.split("/")
        if not "api" in slugs:
            return None
        if "whoami" in slugs:
            return None
        if "status" in slugs:
            return None
        if "version" in slugs:
            return None
        for slug in slugs:
            this_slug = str(slug).lower()
            if this_slug in cls.all_slugs():
                return this_slug
        logger.warning("SAMKinds.from_url() could not extract manifest kind from URL: %s", url)
