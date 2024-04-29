"""Smarter API V0 PLugin enum classes."""

from smarter.apps.api.v0.manifests.enum import SmarterEnumAbstract


class SAMPluginMetadataKeys(SmarterEnumAbstract):
    """Smarter API V0 Plugin Metadata keys enumeration."""

    CLASS = "class"


class SAMPluginMetadataClassValues(SmarterEnumAbstract):
    """Smarter API V0 Plugin Metadata Class keys enumeration."""

    STATIC = "static"
    API = "api"
    SQL = "sql"


class SAMPluginSpecKeys(SmarterEnumAbstract):
    """Smarter API V0 Plugin Spec keys enumeration."""

    SELECTOR = "selector"
    PROMPT = "prompt"
    DATA = "data"


class SAMPluginSpecSelectorKeys(SmarterEnumAbstract):
    """Smarter API V0 Plugin Spec Selector keys enumeration."""

    DIRECTIVE = "directive"
    SEARCHTERMS = "searchTerms"


class SAMPluginSpecSelectorKeyDirectiveValues(SmarterEnumAbstract):
    """Smarter API V0 Plugin Spec Selector keys enumeration."""

    SEARCHTERMS = "searchTerms"  # Smarter handler applied key word search
    ALWAYS = "always"  # Plugin is always selected, for every prompt request
    LLM = "llm"  # Plugin is included in a list of plugins shown to an LLM prompt
    # in which we ask it to select suitable plugins to use for the prompt


class SAMPluginSpecPromptKeys(SmarterEnumAbstract):
    """Smarter API V0 Plugin Spec Prompt keys enumeration."""

    SYSTEMROLE = "systemRole"
    MODEL = "model"
    TEMPERATURE = "temperature"
    MAXTOKENS = "maxTokens"


class SAMPluginSpecDataKeys(SmarterEnumAbstract):
    """Smarter API V0 Plugin Spec Data keys enumeration."""

    DESCRIPTION = "description"
