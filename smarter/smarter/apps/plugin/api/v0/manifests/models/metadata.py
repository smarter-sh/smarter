"""Smarter API V0 Manifest - Plugin.metadata"""

from pydantic import Field, field_validator

from smarter.apps.api.v0.manifests.exceptions import SAMValidationError
from smarter.apps.api.v0.manifests.models import SAMMetadataBase

# Plugin
from smarter.apps.plugin.api.v0.manifests.enum import SAMPluginMetadataClassValues


###############################################################################
# Plugin metadata
###############################################################################
class SAMPluginMetadata(SAMMetadataBase):
    """Smarter API V0 Plugin Manifest - Metadata class."""

    plugin_class: str = Field(
        ...,
        description=f"Plugin.metadata.class: The class of the Plugin. Must be one of {SAMPluginMetadataClassValues.all_values()}",
    )

    @field_validator("plugin_class")
    def validate_plugin_class(cls, v) -> str:
        if v not in SAMPluginMetadataClassValues.all_values():
            raise SAMValidationError(
                f"Invalid value found for Plugin.metadata.class: {v}. Must be one of {SAMPluginMetadataClassValues.all_values()}"
            )
        return v
