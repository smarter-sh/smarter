"""Smarter API V0 PLugin Manifest - enumerated datatypes."""

from smarter.lib.manifest.enum import SmarterEnumAbstract


###############################################################################
# Enums for describing possible manifest key values
###############################################################################
class SAMPluginMetadataClassValues(SmarterEnumAbstract):
    """Smarter API V0 Plugin Metadata Class keys enumeration."""

    # a plugin that returns a static json response contained inside the plugin manifest
    STATIC = "static"

    # a plugin that returns a dynamic json response by
    # executing an http request to a remote server that returns a json response
    API = "api"

    # a plugin that returns a dynamic json response by executing a sql query
    # to a database that returns a mysql readable object response
    SQL = "sql"


class SAMPluginSpecSelectorKeyDirectiveValues(SmarterEnumAbstract):
    """Smarter API V0 Plugin Spec Selector keys enumeration."""

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
class SAMPluginMetadataKeys(SmarterEnumAbstract):
    """Smarter API V0 Plugin Metadata keys enumeration."""

    PLUGIN_CLASS = "pluginClass"


class SAMPluginMetadataClass(SmarterEnumAbstract):
    """Smarter API V0 Plugin Metadata Class keys enumeration."""

    STATIC_DATA = "staticData"
    API_DATA = "apiData"
    SQL_DATA = "sqlData"


class SAMPluginSpecKeys(SmarterEnumAbstract):
    """Smarter API V0 Plugin Spec keys enumeration."""

    SELECTOR = "selector"
    PROMPT = "prompt"
    DATA = "data"


class SAMPluginSpecSelectorKeys(SmarterEnumAbstract):
    """Smarter API V0 Plugin Spec Selector keys enumeration."""

    DIRECTIVE = "directive"


class SAMPluginSpecPromptKeys(SmarterEnumAbstract):
    """Smarter API V0 Plugin Spec Prompt keys enumeration."""

    SYSTEMROLE = "systemRole"
    MODEL = "model"
    TEMPERATURE = "temperature"
    MAXTOKENS = "maxTokens"


class SmartApiPluginSpecDataKeys(SmarterEnumAbstract):
    """Smarter API V0 Plugin Spec Data keys enumeration."""

    DESCRIPTION = "description"
