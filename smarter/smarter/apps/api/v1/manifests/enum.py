"""Smarter API V0 Manifests Enumerations."""

from smarter.apps.plugin.manifest.models.plugin.const import (
    MANIFEST_KIND as PLUGIN_KIND,
)
from smarter.apps.plugin.manifest.models.sql_connection.const import (
    MANIFEST_KIND as SQL_CONNECTION_KIND,
)
from smarter.lib.manifest.enum import SmarterEnumAbstract


class SAMKinds(SmarterEnumAbstract):
    """Smarter manifest kinds enumeration."""

    PLUGIN = PLUGIN_KIND
    ACCOUNT = "Account"
    USER = "User"
    CHAT = "Chat"
    CHATBOT = "Chatbot"
    SQL_CONNECTION = SQL_CONNECTION_KIND

    @classmethod
    def all_slugs(cls):
        return cls.singular_slugs() + cls.plural_slugs()

    @classmethod
    def singular_slugs(cls):
        return [slug.lower() for slug in cls.all_values()]

    @classmethod
    def plural_slugs(cls):
        return [f"{slug.lower()}s" for slug in cls.all_values()]
