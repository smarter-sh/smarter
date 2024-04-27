"""Smarter API V0 Plugin manifest specification."""

from smarter.apps.api.v0.manifests import (
    SmarterApi,
    SmarterApiManifestKeys,
    SmarterApiManifestKinds,
    SmarterApiSpecKeyOptions,
    SmarterEnumAbstract,
)


class SmarterApiManifestKeysPluginMetadata(SmarterEnumAbstract):
    """Smarter API V0 Plugin Metadata keys enumeration."""

    NAME = "name"
    CLASS = "class"
    DESCRIPTION = "description"
    VERSION = "version"
    TAGS = "tags"


class SmarterApiManifestPluginMetadataClass(SmarterEnumAbstract):
    """Smarter API V0 Plugin Metadata Class keys enumeration."""

    STATIC = "static"
    API = "api"
    SQL = "sql"


class SmarterApiManifestPluginSpecKeys(SmarterEnumAbstract):
    """Smarter API V0 Plugin Spec keys enumeration."""

    SELECTOR = "selector"
    PROMPT = "prompt"
    DATA = "data"


class SmartApiPluginSpecSelectorKeys(SmarterEnumAbstract):
    """Smarter API V0 Plugin Spec Selector keys enumeration."""

    DIRECTIVE = "directive"


class SmarterApiManifestPluginSpecPromptKey(SmarterEnumAbstract):
    """Smarter API V0 Plugin Spec Prompt keys enumeration."""

    SYSTEMROLE = "systemRole"
    MODEL = "model"
    TEMPERATURE = "temperature"
    MAXTOKENS = "maxTokens"


class SmartApiPluginSpecDataKeys(SmarterEnumAbstract):
    """Smarter API V0 Plugin Spec Data keys enumeration."""

    DESCRIPTION = "description"


class SmarterApiPlugin(SmarterApi):
    """Smarter API V0 Plugin class."""

    plugin_spec = {
        SmarterApiManifestKeys.KIND: SmarterApiManifestKinds.PLUGIN,
        SmarterApiManifestKeys.METADATA: {
            SmarterApiManifestKeysPluginMetadata.NAME: (str, [SmarterApiSpecKeyOptions.REQUIRED]),
            SmarterApiManifestKeysPluginMetadata.CLASS: SmarterApiManifestPluginMetadataClass.all_values(),
            SmarterApiManifestKeysPluginMetadata.DESCRIPTION: (str, [SmarterApiSpecKeyOptions.REQUIRED]),
            SmarterApiManifestKeysPluginMetadata.VERSION: (str, [SmarterApiSpecKeyOptions.REQUIRED]),
            SmarterApiManifestKeysPluginMetadata.TAGS: (list, [SmarterApiSpecKeyOptions.OPTIONAL]),
        },
        SmarterApiManifestKeys.SPEC: {
            SmarterApiManifestPluginSpecKeys.SELECTOR: {
                SmartApiPluginSpecSelectorKeys.DIRECTIVE: (str, [SmarterApiSpecKeyOptions.REQUIRED]),
            },
            SmarterApiManifestPluginSpecKeys.PROMPT: {
                SmarterApiManifestPluginSpecPromptKey.SYSTEMROLE: (str, [SmarterApiSpecKeyOptions.REQUIRED]),
                SmarterApiManifestPluginSpecPromptKey.MODEL: (str, [SmarterApiSpecKeyOptions.REQUIRED]),
                SmarterApiManifestPluginSpecPromptKey.TEMPERATURE: (float, [SmarterApiSpecKeyOptions.REQUIRED]),
                SmarterApiManifestPluginSpecPromptKey.MAXTOKENS: (int, [SmarterApiSpecKeyOptions.REQUIRED]),
            },
            SmarterApiManifestPluginSpecKeys.DATA: {
                SmartApiPluginSpecDataKeys.DESCRIPTION: (str, [SmarterApiSpecKeyOptions.REQUIRED]),
            },
        },
    }

    def get_spec(self) -> dict:
        spec = super().get_spec()
        spec.update(self.plugin_spec)
        return spec
