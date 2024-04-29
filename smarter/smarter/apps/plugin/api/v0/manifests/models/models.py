"""Smarter API V0 Plugin Manifest models."""

from pydantic import Field, field_validator, model_validator

from smarter.apps.api.v0.manifests.exceptions import SAMValidationError
from smarter.apps.api.v0.manifests.models import SAM, SAMMetadataBase, SAMStatusBase

# Plugin
from smarter.apps.plugin.api.v0.manifests.enum import SAMPluginMetadataClassValues

from .spec import SAMPluginSpec


###############################################################################
# Plugin metadata
###############################################################################
class SAMPluginMetadata(SAMMetadataBase):
    """Smarter API V0 Plugin Manifest - Metadata class."""

    plugin_class: str = Field(..., description="The class of the Plugin")

    @field_validator("plugin_class")
    def validate_plugin_class(cls, v) -> str:
        if v not in SAMPluginMetadataClassValues.all_values():
            raise SAMValidationError(
                f"Invalid value found for Plugin.metadata.class: {v}. Must be one of {SAMPluginMetadataClassValues.all_values()}"
            )
        return v


###############################################################################
# Plugin metadata
###############################################################################
class SAMPluginStatus(SAMStatusBase):
    """Smarter API V0 Plugin Manifest - Status class."""


###############################################################################
# Plugin
###############################################################################
class SAMPlugin(SAM):
    """Smarter API V0 Plugin Manifest class."""

    # override the parent class attributes in order to add the Plugin specific metadata, spec, and status
    metadata: SAMPluginMetadata
    spec: SAMPluginSpec
    status: SAMPluginStatus

    @field_validator("metadata")
    def validate_metadata(cls, v) -> SAMPluginMetadata:
        if not isinstance(v, SAMPluginMetadata):
            raise SAMValidationError("Plugin.metadata must be an instance of SAMPluginMetadata")
        return v

    @field_validator("spec")
    def validate_spec(cls, v) -> SAMPluginSpec:
        if not isinstance(v, SAMPluginSpec):
            raise SAMValidationError("Plugin.spec must be an instance of SAMPluginSpec")
        return v

    @field_validator("status")
    def validate_status(cls, v) -> SAMPluginStatus:
        if not isinstance(v, SAMPluginStatus):
            raise SAMValidationError("Pluigin.status must be an instance of SAMPluginStatus")
        return v

    @model_validator(mode="after")
    def validate_business_rules(self) -> "SAMPlugin":
        """Plugin-level business rule validations"""

        # 1. if metadata.class == 'static' then spec.data.staticData is a required field
        if self.metadata.plugin_class == SAMPluginMetadataClassValues.STATIC and not self.spec.data.static_data:
            raise SAMValidationError("spec.data.staticData is required when Plugin.class is 'static'")

        # 2. if metadata.class == 'sql' then spec.data.sqlData is a required field
        if self.metadata.plugin_class == SAMPluginMetadataClassValues.SQL and not self.spec.data.sql_data:
            raise SAMValidationError("spec.data.sqlData is required when Plugin.class is 'sql'")

        # 3. if metadata.class == 'api' then spec.data.apiData is a required field
        if self.metadata.plugin_class == SAMPluginMetadataClassValues.API and not self.spec.data.api_data:
            raise SAMValidationError("spec.data.apiData is required when Plugin.class is 'api'")

        return self
