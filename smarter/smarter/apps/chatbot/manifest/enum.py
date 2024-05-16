"""Smarter API PLugin Manifest - enumerated datatypes."""

from smarter.lib.manifest.enum import SmarterEnumAbstract


###############################################################################
# Enums for manifest keys in error handlers and other on-screen messages
###############################################################################
class SAMChatbotSpecKeys(SmarterEnumAbstract):
    """Smarter API Plugin Spec keys enumeration."""

    PLUGINS = "plugins"
