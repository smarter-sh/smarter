"""Smarter API V0 Manifest - Plugin.metadata"""

from pydantic import Field, field_validator

from smarter.apps.api.v0.manifests.exceptions import SAMValidationError
from smarter.apps.api.v0.manifests.models import SAMMetadataBase

# Plugin
from smarter.apps.plugin.api.v0.manifests.enum import SAMPluginMetadataClassValues


class SAMPluginMetadata(SAMMetadataBase):
    """Smarter API V0 Plugin Manifest - Metadata class."""

    pluginClass: str = Field(
        ...,
        description=f"Plugin.metadata.class: The class of the Plugin. Must be one of {SAMPluginMetadataClassValues.all_values()}",
    )

    @field_validator("pluginClass")
    def validate_plugin_class(cls, v) -> str:
        err_desc_manifest_kind = "Plugin.metadata"
        err_desc_class_name = cls.pluginClass.__class__.__name__
        err_desc_model_name = f"{err_desc_manifest_kind}.{err_desc_class_name}"

        if v not in SAMPluginMetadataClassValues.all_values():
            raise SAMValidationError(
                f"Invalid value found for {err_desc_model_name}: {v}. Must be one of {SAMPluginMetadataClassValues.all_values()}"
            )
        return v
