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
