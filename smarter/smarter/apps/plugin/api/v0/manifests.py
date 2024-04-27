"""Smarter Api Manifest ("SAM") specification for Plugin."""

from smarter.apps.api.v0.manifests import (
    SAM,
    SAMDataFormats,
    SAMKeys,
    SAMKinds,
    SAMSpecificationKeyOptions,
    SmarterEnumAbstract,
)


class SAMPluginMetadataKeys(SmarterEnumAbstract):
    """Smarter API V0 Plugin Metadata keys enumeration."""

    CLASS = "class"


class SAMPluginMetadataClass(SmarterEnumAbstract):
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


class SAMPluginSpecPromptKeys(SmarterEnumAbstract):
    """Smarter API V0 Plugin Spec Prompt keys enumeration."""

    SYSTEMROLE = "systemRole"
    MODEL = "model"
    TEMPERATURE = "temperature"
    MAXTOKENS = "maxTokens"


class SmartApiPluginSpecDataKeys(SmarterEnumAbstract):
    """Smarter API V0 Plugin Spec Data keys enumeration."""

    DESCRIPTION = "description"


class SAMPlugin(SAM):
    """Smarter API V0 Plugin class."""

    def __init__(
        self,
        manifest: str = None,
        data_format: SAMDataFormats = None,
        file_path: str = None,
        url: str = None,
    ):
        super().__init__(manifest, data_format, file_path, url)

        plugin_specification = {
            SAMKeys.KIND: SAMKinds.PLUGIN,
            SAMKeys.METADATA: {
                SAMPluginMetadataKeys.CLASS: SAMPluginMetadataClass.all_values(),
            },
            SAMKeys.SPEC: {
                SAMPluginSpecKeys.SELECTOR: {
                    SAMPluginSpecSelectorKeys.DIRECTIVE: (str, [SAMSpecificationKeyOptions.REQUIRED]),
                },
                SAMPluginSpecKeys.PROMPT: {
                    SAMPluginSpecPromptKeys.SYSTEMROLE: (
                        str,
                        [SAMSpecificationKeyOptions.REQUIRED],
                    ),
                    SAMPluginSpecPromptKeys.MODEL: (str, [SAMSpecificationKeyOptions.REQUIRED]),
                    SAMPluginSpecPromptKeys.TEMPERATURE: (
                        float,
                        [SAMSpecificationKeyOptions.REQUIRED],
                    ),
                    SAMPluginSpecPromptKeys.MAXTOKENS: (
                        int,
                        [SAMSpecificationKeyOptions.REQUIRED],
                    ),
                },
                SAMPluginSpecKeys.DATA: {
                    SmartApiPluginSpecDataKeys.DESCRIPTION: (str, [SAMSpecificationKeyOptions.REQUIRED]),
                },
            },
        }

        # update the base specification with the plugin-specific specification
        specification = super().specification.copy()
        specification.update(plugin_specification)
        super()._specification = specification

        # revalidate the specification
        self.validate()

    @property
    def manifest_metadata_keys(self) -> list[str]:
        super_meta_keys = super().metadata_keys
        these_keys = SAMPluginMetadataKeys.all_values()
        return super_meta_keys + these_keys

    @property
    def manifest_spec_keys(self) -> list[str]:
        super_spec_keys = super().spec_keys
        these_keys = SAMPluginSpecKeys.all_values()
        return super_spec_keys + these_keys

    @property
    def manifest_status_keys(self) -> list[str]:
        return []

    @property
    def manifest_plugin_classes(self) -> list[str]:
        return SAMPluginMetadataClass.all_values()

    @property
    def manifest_plugin_prompt_spec_keys(self) -> list[str]:
        return SAMPluginSpecPromptKeys.all_values()

    @property
    def manifest_plugin_selector_spec_keys(self) -> list[str]:
        return SAMPluginSpecSelectorKeys.all_values()

    def validate(self, recursed_data: dict = None, recursed_spec: dict = None):
        """Validate the plugin specification."""
        super().validate(recursed_data=recursed_data, recursed_spec=recursed_spec)

        # do plugin-specific validation here: static, api, sql
