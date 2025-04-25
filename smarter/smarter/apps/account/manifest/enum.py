"""Smarter API PLugin Manifest - enumerated datatypes."""

from smarter.common.enum import SmarterEnumAbstract
from smarter.lib.manifest.enum import SAMMetadataKeys, SmarterEnumAbstract


###############################################################################
# Enums for manifest keys in error handlers and other on-screen messages
###############################################################################
class SAMAccountSpecKeys(SmarterEnumAbstract):
    """Smarter API Plugin Spec keys enumeration."""

    CONFIG = "config"


class SAMUserSpecKeys(SmarterEnumAbstract):
    """Smarter API User Spec keys enumeration."""

    CONFIG = "config"


class SAMSecretSpecKeys(SmarterEnumAbstract):
    """Smarter API Secret Spec keys enumeration."""

    CONFIG = "config"
    VALUE = "value"
    DESCRIPTION = "description"
    EXPIRATION_DATE = "expiration_date"


class SAMSecretMetadataKeys(SAMMetadataKeys):
    """Smarter API Secret Metadata keys enumeration."""

    USERNAME = "username"
    ACCOUNT_NUMBER = "account_number"


class SAMSecretStatusKeys(SmarterEnumAbstract):
    """Smarter API Secret Metadata keys enumeration."""

    USERNAME = "username"
    ACCOUNT_NUMBER = "account_number"
    CREATED = "created_at"
    UPDATED = "updated_at"
    LAST_ACCESSED = "last_accessed"
