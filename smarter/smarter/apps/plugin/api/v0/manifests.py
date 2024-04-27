"""Smarter API V0 Plugin manifest specification."""

from smarter.apps.api.v0.manifests import (
    SmarterApiManifest,
    SmarterApiManifestDataFormats,
    SmarterApiManifestKeys,
    SmarterApiManifestKinds,
    SmarterApiSpecificationKeyOptions,
    SmarterEnumAbstract,
)


class SmarterApiManifestPluginMetadataKeys(SmarterEnumAbstract):
    """Smarter API V0 Plugin Metadata keys enumeration."""

    CLASS = "class"


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


class SmarterApiManifestPluginSpecPromptKeys(SmarterEnumAbstract):
    """Smarter API V0 Plugin Spec Prompt keys enumeration."""

    SYSTEMROLE = "systemRole"
    MODEL = "model"
    TEMPERATURE = "temperature"
    MAXTOKENS = "maxTokens"


class SmartApiPluginSpecDataKeys(SmarterEnumAbstract):
    """Smarter API V0 Plugin Spec Data keys enumeration."""

    DESCRIPTION = "description"


class SmarterApiPlugin(SmarterApiManifest):
    """Smarter API V0 Plugin class."""

    def __init__(
        self,
        manifest: str = None,
        data_format: SmarterApiManifestDataFormats = None,
        file_path: str = None,
        url: str = None,
    ):
        super().__init__(manifest, data_format, file_path, url)

        plugin_specification = {
            SmarterApiManifestKeys.KIND: SmarterApiManifestKinds.PLUGIN,
            SmarterApiManifestKeys.METADATA: {
                SmarterApiManifestPluginMetadataKeys.CLASS: SmarterApiManifestPluginMetadataClass.all_values(),
            },
            SmarterApiManifestKeys.SPEC: {
                SmarterApiManifestPluginSpecKeys.SELECTOR: {
                    SmartApiPluginSpecSelectorKeys.DIRECTIVE: (str, [SmarterApiSpecificationKeyOptions.REQUIRED]),
                },
                SmarterApiManifestPluginSpecKeys.PROMPT: {
                    SmarterApiManifestPluginSpecPromptKeys.SYSTEMROLE: (
                        str,
                        [SmarterApiSpecificationKeyOptions.REQUIRED],
                    ),
                    SmarterApiManifestPluginSpecPromptKeys.MODEL: (str, [SmarterApiSpecificationKeyOptions.REQUIRED]),
                    SmarterApiManifestPluginSpecPromptKeys.TEMPERATURE: (
                        float,
                        [SmarterApiSpecificationKeyOptions.REQUIRED],
                    ),
                    SmarterApiManifestPluginSpecPromptKeys.MAXTOKENS: (
                        int,
                        [SmarterApiSpecificationKeyOptions.REQUIRED],
                    ),
                },
                SmarterApiManifestPluginSpecKeys.DATA: {
                    SmartApiPluginSpecDataKeys.DESCRIPTION: (str, [SmarterApiSpecificationKeyOptions.REQUIRED]),
                },
            },
        }
        specification = self.specification.copy()
        specification.update(plugin_specification)
        self._specification = specification
        self.validate()

    @property
    def manifest_metadata_keys(self) -> list[str]:
        super_meta_keys = super().metadata_keys
        these_keys = SmarterApiManifestPluginMetadataKeys.all_values()
        return super_meta_keys + these_keys

    @property
    def manifest_spec_keys(self) -> list[str]:
        super_spec_keys = super().spec_keys
        these_keys = SmarterApiManifestPluginSpecKeys.all_values()
        return super_spec_keys + these_keys

    @property
    def manifest_status_keys(self) -> list[str]:
        return []

    @property
    def manifest_plugin_classes(self) -> list[str]:
        return SmarterApiManifestPluginMetadataClass.all_values()

    @property
    def manifest_plugin_prompt_spec_keys(self) -> list[str]:
        return SmarterApiManifestPluginSpecPromptKeys.all_values()

    @property
    def manifest_plugin_selector_spec_keys(self) -> list[str]:
        return SmartApiPluginSpecSelectorKeys.all_values()

    def validate(self, recursed_data: dict = None, recursed_spec: dict = None):
        """Validate the plugin specification."""
        super().validate(recursed_data=recursed_data, recursed_spec=recursed_spec)

        # do plugin-specific validation here: static, api, sql
