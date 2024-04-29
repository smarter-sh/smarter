"""Smarter API V0 PLugin Manifest - enumerated datatypes."""

from smarter.apps.api.v0.manifests.enum import SmarterEnumAbstract


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
