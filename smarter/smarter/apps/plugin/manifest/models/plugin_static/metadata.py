"""Smarter API Manifest - Plugin.metadata"""

import os
from typing import ClassVar

from pydantic import Field, field_validator

from smarter.apps.plugin.manifest.enum import SAMPluginStaticMetadataClassValues

# Plugin
from smarter.apps.plugin.manifest.models.plugin_static.const import MANIFEST_KIND
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.models import AbstractSAMMetadataBase


filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMPluginStaticMetadata(AbstractSAMMetadataBase):
    """Smarter API Plugin Manifest - Metadata class."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    pluginClass: str = Field(
        SAMPluginStaticMetadataClassValues.STATIC.value,
        description=f"{class_identifier}.pluginClass: The class of the {MANIFEST_KIND}. Must be set to {SAMPluginStaticMetadataClassValues.STATIC.value}",
    )

    @field_validator("pluginClass")
    def validate_plugin_class(cls, v) -> str:
        err_desc_class_name = "pluginClass"
        err_desc_model_name = f"{cls.class_identifier}.{err_desc_class_name}"

        if v not in SAMPluginStaticMetadataClassValues.all_values():
            raise SAMValidationError(
                f"Invalid value found for {err_desc_model_name}: '{v}'. Must be one of {SAMPluginStaticMetadataClassValues.all_values()}"
            )
        return v
