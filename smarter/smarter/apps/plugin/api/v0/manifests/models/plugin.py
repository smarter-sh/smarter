"""Smarter API V0 Plugin Manifest"""

from typing import Optional

from pydantic import Field, model_validator

from smarter.apps.api.v0.manifests.exceptions import SAMValidationError
from smarter.apps.api.v0.manifests.models import SAM

# Plugin
from smarter.apps.plugin.api.v0.manifests.enum import SAMPluginMetadataClassValues

from ..enum import SAMPluginMetadataClassValues
from .metadata import SAMPluginMetadata
from .spec import SAMPluginSpec
from .status import SAMPluginStatus


class SAMPlugin(SAM):
    """Smarter API V0 Manifest - Plugin"""

    metadata: SAMPluginMetadata = Field(..., description="Plugin.metadata[obj]: Required, the Plugin metadata.")
    spec: SAMPluginSpec = Field(..., description="Plugin.spec[obj]: Required, the Plugin specification.")
    status: Optional[SAMPluginStatus] = Field(
        ..., description="Plugin.status[obj]: Optional, Read-only. Stateful status information about the Plugin."
    )

    @model_validator(mode="after")
    def validate_business_rules(self) -> "SAMPlugin":
        """Plugin-level business rule validations"""
        err_desc_manifest_kind = self.kind
        err_desc_spec_name = self.spec.__class__.__name__
        err_desc_data_name = self.spec.data.__class__.__name__
        err_desc_model_name = f"{err_desc_manifest_kind}.{err_desc_spec_name}.{err_desc_data_name}"

        pluginClass_name = self.metadata.pluginClass.__class__.__name__

        # Validate that the correct Plugin.spec.data is present when the Plugin.metadata.pluginClass is 'static', 'sql', or 'api'
        # example error message: "Plugin.spec.data.staticData is required when Plugin.metadata.pluginClass is 'static'"
        if self.metadata.pluginClass == SAMPluginMetadataClassValues.STATIC and not self.spec.data.staticData:
            required_attribute_name = self.spec.data.staticData.__class__.__name__
            raise SAMValidationError(
                f"{err_desc_model_name}.{required_attribute_name} is required when {err_desc_manifest_kind}.{pluginClass_name} is '{SAMPluginMetadataClassValues.STATIC.value}'"
            )

        if self.metadata.pluginClass == SAMPluginMetadataClassValues.SQL and not self.spec.data.sqlData:
            required_attribute_name = self.spec.data.sqlData.__class__.__name__
            raise SAMValidationError(
                f"{err_desc_model_name}.{required_attribute_name} is required when {err_desc_manifest_kind}.{pluginClass_name} is '{SAMPluginMetadataClassValues.SQL.value}'"
            )

        if self.metadata.pluginClass == SAMPluginMetadataClassValues.API and not self.spec.data.apiData:
            required_attribute_name = self.spec.data.apiData.__class__.__name__
            raise SAMValidationError(
                f"{err_desc_model_name}.{required_attribute_name} is required when {err_desc_manifest_kind}.{pluginClass_name} is '{SAMPluginMetadataClassValues.API.value}'"
            )

        return self
