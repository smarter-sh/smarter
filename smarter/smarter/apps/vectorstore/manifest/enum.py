"""Smarter API Vectorstore Manifest - enumerated datatypes."""

from smarter.common.enum import SmarterEnumAbstract


###############################################################################
# Enums for manifest keys in error handlers and other on-screen messages
###############################################################################
class VectorstoreModelEnum(SmarterEnumAbstract):
    """Smarter Vectorstore Model enumeration."""


class SAMVectorstoreSpecKeys(SmarterEnumAbstract):
    """Smarter API Vectorstore Manifest Specification Keys enumeration."""

    BACKEND = "backend"
    HOST = "host"
    PORT = "port"
    AUTH_CONFIG = "auth_config"
    PASSWORD = "password"
    CONFIG = "config"
    IS_ACTIVE = "is_active"
    STATUS = "status"
    PROVIDER = "provider"
    PROVIDER_MODEL = "provider_model"
