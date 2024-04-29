"""Smarter Api Manifest ("SAM") specification for Plugin."""

from smarter.apps.api.v0.manifests.enum import (
    SAMKeys,
    SAMKinds,
    SAMSpecificationKeyOptions,
)
from smarter.apps.api.v0.manifests.handler import SAMLoader

from .enum import (
    SAMPluginMetadataClassValues,
    SAMPluginMetadataKeys,
    SAMPluginSpecDataKeys,
    SAMPluginSpecKeys,
    SAMPluginSpecPromptKeys,
    SAMPluginSpecSelectorKeys,
)


class SAMPluginLoader(SAMLoader):
    """Smarter API V0 Plugin class."""

    plugin_specification = {
        SAMKeys.KIND: SAMKinds.PLUGIN,
        SAMKeys.METADATA: {
            SAMPluginMetadataKeys.CLASS: SAMPluginMetadataClassValues.all_values(),
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
                SAMPluginSpecDataKeys.DESCRIPTION: (str, [SAMSpecificationKeyOptions.REQUIRED]),
            },
        },
    }

    def __init__(
        self,
        manifest: str = None,
        file_path: str = None,
        url: str = None,
    ):
        super().__init__(manifest=manifest, file_path=file_path, url=url)

        # update the base specification with the plugin-specific specification
        specification = super().specification.copy()
        specification.update(self.plugin_specification)
        super()._specification = specification

        # revalidate the specification
        self.validate_manifest()

    @property
    def manifest_metadata_keys(self) -> list[str]:
        super_meta_keys = super().manifest_metadata_keys
        these_keys = SAMPluginMetadataKeys.all_values()
        return super_meta_keys + these_keys

    @property
    def manifest_spec_keys(self) -> list[str]:
        super_spec_keys = super().manifest_spec_keys
        these_keys = SAMPluginSpecKeys.all_values()
        return super_spec_keys + these_keys

    @property
    def manifest_status_keys(self) -> list[str]:
        return []

    @property
    def manifest_plugin_classes(self) -> list[str]:
        return SAMPluginMetadataClassValues.all_values()

    @property
    def manifest_plugin_prompt_spec_keys(self) -> list[str]:
        return SAMPluginSpecPromptKeys.all_values()

    @property
    def manifest_plugin_selector_spec_keys(self) -> list[str]:
        return SAMPluginSpecSelectorKeys.all_values()
