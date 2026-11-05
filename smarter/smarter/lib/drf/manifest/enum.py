"""Enumerated datatypes of the SmarterAuthToken manifest."""

from smarter.lib.manifest.enum import SmarterEnumAbstract


###############################################################################
# Enums for manifest keys in error handlers and other on-screen messages
###############################################################################
class SAMSmarterAuthTokenSpecKeys(SmarterEnumAbstract):
    """The keys of a SmarterAuthToken manifest's ``spec``."""

    CONFIG = "config"
