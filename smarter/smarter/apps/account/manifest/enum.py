"""Smarter API PLugin Manifest - enumerated datatypes."""

from smarter.common.enum import SmarterEnumAbstract


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


class SAMSecretMetadataKeys(SmarterEnumAbstract):
    """Smarter API Secret Metadata keys enumeration."""

    NAME = "name"
    DESCRIPTION = "description"
    VERSION = "version"
    TAGS = "tags"
    ANNOTATIONS = "annotations"
    USERNAME = "username"
    ACCOUNT_NUMBER = "accountNumber"


class SAMSecretStatusKeys(SmarterEnumAbstract):
    """Smarter API Secret Metadata keys enumeration."""

    USERNAME = "username"
    ACCOUNT_NUMBER = "accountNumber"
    CREATED = "created"
    UPDATED = "updated"
    LAST_ACCESSED = "last_accessed"
