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
from smarter.apps.chat.manifest.models.chat.const import (
    MANIFEST_KIND as CHAT_MANIFEST_KIND,
)
from smarter.apps.chat.manifest.models.chat_history.const import (
    MANIFEST_KIND as CHAT_HISTORY_MANIFEST_KIND,
)
from smarter.apps.chat.manifest.models.chat_plugin_usage.const import (
    MANIFEST_KIND as CHAT_PLUGIN_USAGE_MANIFEST_KIND,
)
from smarter.apps.chat.manifest.models.chat_tool_call.const import (
    MANIFEST_KIND as CHAT_TOOL_CALL_MANIFEST_KIND,
)
from smarter.apps.chatbot.manifest.models.chatbot.const import (
    MANIFEST_KIND as CHATBOT_MANIFEST_KIND,
)
from smarter.apps.plugin.manifest.models.plugin.const import (
    MANIFEST_KIND as PLUGIN_MANIFEST_KIND,
)
from smarter.apps.plugin.manifest.models.sql_connection.const import (
    MANIFEST_KIND as SQLCONNECTION_MANIFEST_KIND,
)
from smarter.lib.drf.manifest.models.auth_token.const import (
    MANIFEST_KIND as AUTH_TOKEN_MANIFEST_KIND,
)
from smarter.lib.manifest.enum import SmarterEnumAbstract


logger = logging.getLogger(__name__)


class SAMKinds(SmarterEnumAbstract):
    """Smarter manifest kinds enumeration."""

    PLUGIN = PLUGIN_MANIFEST_KIND
    ACCOUNT = ACCOUNT_MANIFEST_KIND
    APIKEY = AUTH_TOKEN_MANIFEST_KIND
    USER = USER_MANIFEST_KIND
    CHAT = CHAT_MANIFEST_KIND
    CHAT_HISTORY = CHAT_HISTORY_MANIFEST_KIND
    CHAT_PLUGIN_USAGE = CHAT_PLUGIN_USAGE_MANIFEST_KIND
    CHAT_TOOL_CALL = CHAT_TOOL_CALL_MANIFEST_KIND
    CHATBOT = CHATBOT_MANIFEST_KIND
    SQLCONNECTION = SQLCONNECTION_MANIFEST_KIND
    # APICONNECTION = "PluginDataApiConnection"
    SECRET = SECRET_MANIFEST_KIND

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
        parsed_url = urlparse(url)
        if parsed_url:
            slugs = parsed_url.path.split("/")
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
