"""Smarter API V0 Manifests Enumerations."""

from smarter.apps.plugin.manifest.const import MANIFEST_KIND as PLUGIN_KIND
from smarter.lib.manifest.enum import SmarterEnumAbstract


class SAMKinds(SmarterEnumAbstract):
    """Smarter manifest kinds enumeration."""

    PLUGIN = PLUGIN_KIND
    ACCOUNT = "Account"
    USER = "User"
    CHAT = "Chat"
    CHATBOT = "Chatbot"

    @classmethod
    def all_slugs(cls):
        return cls.singular_slugs() + cls.plural_slugs()

    @classmethod
    def singular_slugs(cls):
        return [slug.lower() for slug in cls.all_values()]

    @classmethod
    def plural_slugs(cls):
        return [f"{slug.lower()}s" for slug in cls.all_values()]
