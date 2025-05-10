"""Smarter API PLugin Manifest - enumerated datatypes."""

from smarter.lib.manifest.enum import SmarterEnumAbstract


###############################################################################
# Enums for describing possible manifest key values
###############################################################################
class SAMPluginCommonMetadataClassValues(SmarterEnumAbstract):
    """Smarter API Plugin Metadata Class keys enumeration."""

    # a plugin that returns a static json response contained inside the plugin manifest
    STATIC = "static"

    # a plugin that returns a dynamic json response by
    # executing an http request to a remote server that returns a json response
    API = "api"

    # a plugin that returns a dynamic json response by executing a sql query
    # to a database that returns a mysql readable object response
    SQL = "sql"


class SAMPluginCommonSpecSelectorKeyDirectiveValues(SmarterEnumAbstract):
    """Smarter API Plugin Spec Selector keys enumeration."""

    # Smarter handler applied key word search
    SEARCHTERMS = "searchTerms"

    # Plugin is always selected, for every prompt request
    ALWAYS = "always"

    # Plugin is included in a list of plugins shown to an LLM prompt
    # in which we ask it to select suitable plugins to use for the prompt
    LLM = "llm"


###############################################################################
# Enums for manifest keys in error handlers and other on-screen messages
###############################################################################
class SAMPluginCommonMetadataKeys(SmarterEnumAbstract):
    """Smarter API Plugin Metadata keys enumeration."""

    PLUGIN_CLASS = "pluginClass"


class SAMPluginCommonMetadataClass(SmarterEnumAbstract):
    """Smarter API Plugin Metadata Class keys enumeration."""

    STATIC_DATA = "staticData"
    API_DATA = "apiData"
    SQL_DATA = "sqlData"


class SAMPluginSpecKeys(SmarterEnumAbstract):
    """Smarter API Plugin Spec keys enumeration."""

    SELECTOR = "selector"
    PROMPT = "prompt"
    DATA = "data"


class SAMPluginCommonSpecSelectorKeys(SmarterEnumAbstract):
    """Smarter API Plugin Spec Selector keys enumeration."""

    DIRECTIVE = "directive"
    SEARCHTERMS = "searchTerms"


class SAMPluginCommonSpecPromptKeys(SmarterEnumAbstract):
    """Smarter API Plugin Spec Prompt keys enumeration."""

    PROVIDER = "provider"
    SYSTEMROLE = "systemRole"
    MODEL = "model"
    TEMPERATURE = "temperature"
    MAXTOKENS = "maxTokens"


class SAMStaticPluginSpecDataKeys(SmarterEnumAbstract):
    """Smarter API Plugin Spec Data keys enumeration."""

    DESCRIPTION = "description"
    STATIC_DATA = "staticData"


###############################################################################
# ApiConnection Spec keys
###############################################################################
class SAMApiConnectionSpecKeys(SmarterEnumAbstract):
    """Smarter API Plugin Spec Data keys enumeration."""

    CONNECTION = "connection"


class SAMApiConnectionSpecConnectionKeys(SmarterEnumAbstract):
    """Smarter API Plugin Spec Data keys enumeration."""

    BASE_URL = "base_url"
    API_KEY = "api_key"
    AUTH_METHOD = "auth_method"
    TIMEOUT = "timeout"
    PROXY_PROTOCOL = "proxy_protocol"
    PROXY_HOST = "proxy_host"
    PROXY_PORT = "proxy_port"
    PROXY_USERNAME = "proxy_username"
    PROXY_PASSWORD = "proxy_password"


class SAMApiConnectionStatusKeys(SmarterEnumAbstract):
    """Smarter API Plugin Spec Data keys enumeration."""

    CONNECTION_STRING = "connection_string"
    IS_VALID = "is_valid"


###############################################################################
# SqlConnection Spec keys
###############################################################################
class SAMSqlConnectionSpecKeys(SmarterEnumAbstract):
    """Smarter API Plugin Spec Data keys enumeration."""

    CONNECTION = "connection"


class SAMSqlConnectionSpecConnectionKeys(SmarterEnumAbstract):
    """Smarter API Plugin Spec Data keys enumeration."""

    DB_ENGINE = "db_engine"
    AUTHENTICATION_METHOD = "authentication_method"
    TIMEOUT = "timeout"
    ACCOUNT = "account"
    DESCRIPTION = "description"
    USE_SSL = "use_ssl"
    SSL_CERT = "ssl_cert"
    SSL_KEY = "ssl_key"
    SSL_CA = "ssl_ca"
    HOSTNAME = "hostname"
    PORT = "port"
    DATABASE = "database"
    USERNAME = "username"
    PASSWORD = "password"
    POOL_SIZE = "pool_size"
    MAX_OVERFLOW = "max_overflow"
    PROXY_PROTOCOL = "proxy_protocol"
    PROXY_HOST = "proxy_host"
    PROXY_PORT = "proxy_port"
    PROXY_USERNAME = "proxy_username"
    PROXY_PASSWORD = "proxy_password"
    SSH_KNOWN_HOSTS = "ssh_known_hosts"


class SAMSqlConnectionStatusKeys(SmarterEnumAbstract):
    """Smarter API Plugin Spec Data keys enumeration."""

    CONNECTION_STRING = "connection_string"
    IS_VALID = "is_valid"
