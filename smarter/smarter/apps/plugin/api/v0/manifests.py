"""Smarter API V0 Plugin manifest specification."""

from smarter.apps.api.v0.manifests import (
    SmarterApi,
    SmarterApiManifestKeys,
    SmarterApiManifestKinds,
    SmarterApiSpecKeyTypes,
    SmarterEnumAbstract,
)


class SmarterApiManifestKeysPluginMetadata(SmarterEnumAbstract):
    """Smarter API V0 Plugin Metadata keys enumeration."""

    NAME = "name"
    CLASS = "class"
    DESCRIPTION = "description"
    VERSION = "version"
    TAGS = "tags"


class SmarterApiManifestKeysPluginMetadataClass(SmarterEnumAbstract):
    """Smarter API V0 Plugin Metadata Class keys enumeration."""

    STATIC = "static"
    API = "api"
    SQL = "sql"


class SmartApiV1KeysPluginSpec(SmarterEnumAbstract):
    """Smarter API V0 Plugin Spec keys enumeration."""

    SELECTOR = "selector"
    PROMPT = "prompt"
    DATA = "data"


class SmartApiV1KeysPluginSpecSelector(SmarterEnumAbstract):
    """Smarter API V0 Plugin Spec Selector keys enumeration."""

    DIRECTIVE = "directive"


class SmarterApiManifestKeysPluginSpecPrompt(SmarterEnumAbstract):
    """Smarter API V0 Plugin Spec Prompt keys enumeration."""

    SYSTEMROLE = "systemRole"
    MODEL = "model"
    TEMPERATURE = "temperature"
    MAXTOKENS = "maxTokens"


class SmartApiV1KeysPluginSpecData(SmarterEnumAbstract):
    """Smarter API V0 Plugin Spec Data keys enumeration."""

    DESCRIPTION = "description"


class SmarterApiV1Plugin(SmarterApi):
    """Smarter API V0 Plugin class."""

    _plugin_spec = {
        SmarterApiManifestKeys.KIND: SmarterApiManifestKinds.PLUGIN,
        SmarterApiManifestKeys.METADATA: {
            SmarterApiManifestKeysPluginMetadata.NAME: (str, [SmarterApiSpecKeyTypes.REQUIRED]),
            SmarterApiManifestKeysPluginMetadata.CLASS: SmarterApiManifestKeysPluginMetadataClass.all_values(),
            SmarterApiManifestKeysPluginMetadata.DESCRIPTION: (str, [SmarterApiSpecKeyTypes.REQUIRED]),
            SmarterApiManifestKeysPluginMetadata.VERSION: (str, [SmarterApiSpecKeyTypes.REQUIRED]),
            SmarterApiManifestKeysPluginMetadata.TAGS: (list, [SmarterApiSpecKeyTypes.OPTIONAL]),
        },
        SmarterApiManifestKeys.SPEC: {
            SmartApiV1KeysPluginSpec.SELECTOR: {
                SmartApiV1KeysPluginSpecSelector.DIRECTIVE: (str, [SmarterApiSpecKeyTypes.REQUIRED]),
            },
            SmartApiV1KeysPluginSpec.PROMPT: {
                SmarterApiManifestKeysPluginSpecPrompt.SYSTEMROLE: (str, [SmarterApiSpecKeyTypes.REQUIRED]),
                SmarterApiManifestKeysPluginSpecPrompt.MODEL: (str, [SmarterApiSpecKeyTypes.REQUIRED]),
                SmarterApiManifestKeysPluginSpecPrompt.TEMPERATURE: (float, [SmarterApiSpecKeyTypes.REQUIRED]),
                SmarterApiManifestKeysPluginSpecPrompt.MAXTOKENS: (int, [SmarterApiSpecKeyTypes.REQUIRED]),
            },
            SmartApiV1KeysPluginSpec.DATA: {
                SmartApiV1KeysPluginSpecData.DESCRIPTION: (str, [SmarterApiSpecKeyTypes.REQUIRED]),
            },
        },
    }

    @property
    def plugin_spec(self) -> dict:
        return self._plugin_spec

    def get_spec(self) -> dict:  # pylint: disable=W0221
        spec = super().get_spec()
        spec.update(self.plugin_spec)
        return spec
