"""Smarter API V0 Manifest - Plugin.metadata"""

from pydantic import Field, field_validator

from smarter.apps.api.v0.manifests.exceptions import SAMValidationError
from smarter.apps.api.v0.manifests.models import SAMMetadataBase

# Plugin
from smarter.apps.plugin.api.v0.manifests.enum import SAMPluginMetadataClassValues

from .const import OBJECT_IDENTIFIER


MODULE_IDENTIFIER = f"{OBJECT_IDENTIFIER}.{__file__}"


class SAMPluginMetadata(SAMMetadataBase):
    """Smarter API V0 Plugin Manifest - Metadata class."""

    class_identifier = MODULE_IDENTIFIER

    pluginClass: str = Field(
        ...,
        description=f"{class_identifier}.pluginClass: The class of the {OBJECT_IDENTIFIER}. Must be one of {SAMPluginMetadataClassValues.all_values()}",
    )

    @field_validator("pluginClass")
    def validate_plugin_class(cls, v) -> str:
        err_desc_class_name = cls.pluginClass.__class__.__name__
        err_desc_model_name = f"{cls.class_identifier}.{err_desc_class_name}"

        if v not in SAMPluginMetadataClassValues.all_values():
            raise SAMValidationError(
                f"Invalid value found for {err_desc_model_name}: {v}. Must be one of {SAMPluginMetadataClassValues.all_values()}"
            )
        return v
