"""Smarter API V0 Manifest - Plugin.metadata"""

import os
from typing import ClassVar

from pydantic import Field, field_validator

from smarter.apps.api.v0.manifests.exceptions import SAMValidationError
from smarter.apps.api.v0.manifests.models import SAMMetadataBase

# Plugin
from smarter.apps.plugin.api.v0.manifests.enum import SAMPluginMetadataClassValues

from .const import OBJECT_IDENTIFIER


filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{OBJECT_IDENTIFIER}.{filename}"


class SAMPluginMetadata(SAMMetadataBase):
    """Smarter API V0 Plugin Manifest - Metadata class."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    pluginClass: str = Field(
        ...,
        description=f"{class_identifier}.pluginClass: The class of the {OBJECT_IDENTIFIER}. Must be one of {SAMPluginMetadataClassValues.all_values()}",
    )

    @field_validator("pluginClass")
    def validate_plugin_class(cls, v) -> str:
        err_desc_class_name = "pluginClass"
        err_desc_model_name = f"{cls.class_identifier}.{err_desc_class_name}"

        if v not in SAMPluginMetadataClassValues.all_values():
            raise SAMValidationError(
                f"Invalid value found for {err_desc_model_name}: '{v}'. Must be one of {SAMPluginMetadataClassValues.all_values()}"
            )
        return v
