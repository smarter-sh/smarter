"""Smarter API Connection Manifest - enumerated datatypes."""

from smarter.lib.manifest.enum import SmarterEnumAbstract


###############################################################################
# ApiConnection Spec keys
###############################################################################
class SAMApiConnectionSpecKeys(SmarterEnumAbstract):
    """Smarter API Connection Spec Data keys enumeration."""

    CONNECTION = "connection"


class SAMApiConnectionSpecConnectionKeys(SmarterEnumAbstract):
    """Smarter API Connection Spec Data keys enumeration."""

    BASE_URL = "baseUrl"
    API_KEY = "apiKey"
    AUTH_METHOD = "authMethod"
    TIMEOUT = "timeout"
    PROXY_PROTOCOL = "proxyProtocol"
    PROXY_HOST = "proxyHost"
    PROXY_PORT = "proxyPort"
    PROXY_USERNAME = "proxyUsername"
    PROXY_PASSWORD = "proxyPassword"


class SAMApiConnectionStatusKeys(SmarterEnumAbstract):
    """Smarter API Connection Spec Data keys enumeration."""

    CONNECTION_STRING = "connection_string"
    IS_VALID = "is_valid"


###############################################################################
# SqlConnection Spec keys
###############################################################################
class SAMSqlConnectionSpecKeys(SmarterEnumAbstract):
    """Smarter API Connection Spec Data keys enumeration."""

    CONNECTION = "connection"


class SAMSqlConnectionSpecConnectionKeys(SmarterEnumAbstract):
    """Smarter API Connection Spec Data keys enumeration."""

    DB_ENGINE = "dbEngine"
    AUTHENTICATION_METHOD = "authenticationMethod"
    TIMEOUT = "timeout"
    DESCRIPTION = "description"
    USE_SSL = "useSsl"
    SSL_CERT = "sslCert"
    SSL_KEY = "sslKey"
    SSL_CA = "sslCa"
    HOSTNAME = "hostname"
    PORT = "port"
    DATABASE = "database"
    USERNAME = "username"
    PASSWORD = "password"
    POOL_SIZE = "poolSize"
    MAX_OVERFLOW = "maxOverflow"
    PROXY_PROTOCOL = "proxyProtocol"
    PROXY_HOST = "proxyHost"
    PROXY_PORT = "proxyPort"
    PROXY_USERNAME = "proxyUsername"
    PROXY_PASSWORD = "proxyPassword"
    SSH_KNOWN_HOSTS = "sshKnownHosts"


class SAMSqlConnectionStatusKeys(SmarterEnumAbstract):
    """Smarter API Connection Spec Data keys enumeration."""

    CONNECTION_STRING = "connection_string"
    IS_VALID = "is_valid"
