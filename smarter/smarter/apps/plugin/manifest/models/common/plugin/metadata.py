"""Smarter API Manifest - Plugin.metadata"""

from pydantic import Field, field_validator

from smarter.apps.plugin.manifest.enum import SAMPluginCommonMetadataClass
from smarter.lib.manifest.models import AbstractSAMMetadataBase


class SAMPluginCommonMetadata(AbstractSAMMetadataBase):
    """Smarter API Plugin Manifest - common Metadata class."""

    pluginClass: str = Field(
        ..., description=f"The class of the plugin. one of: {SAMPluginCommonMetadataClass.all_values()}"
    )

    @field_validator("pluginClass")
    def validate_plugin_class(cls, v: str) -> str:
        """Validate the plugin class."""
        if v not in SAMPluginCommonMetadataClass.all_values():
            raise ValueError(f"Invalid pluginClass '{v}'. Must be one of: {SAMPluginCommonMetadataClass.all_values()}")
        return v
