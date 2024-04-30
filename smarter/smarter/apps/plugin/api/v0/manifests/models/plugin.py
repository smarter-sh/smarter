"""Smarter API V0 Plugin Manifest"""

from typing import ClassVar, Optional

from pydantic import Field, model_validator

from smarter.apps.api.v0.manifests.exceptions import SAMValidationError
from smarter.apps.api.v0.manifests.models import SAM
from smarter.apps.plugin.api.v0.manifests.enum import SAMPluginMetadataClassValues

from .const import OBJECT_IDENTIFIER
from .metadata import SAMPluginMetadata
from .spec import SAMPluginSpec
from .status import SAMPluginStatus


MODULE_IDENTIFIER = OBJECT_IDENTIFIER


class SAMPlugin(SAM):
    """Smarter API V0 Manifest - Plugin"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    metadata: SAMPluginMetadata = Field(
        ..., description=f"{class_identifier}.metadata[obj]: Required, the {OBJECT_IDENTIFIER} metadata."
    )
    spec: SAMPluginSpec = Field(
        ..., description=f"{class_identifier}.spec[obj]: Required, the {OBJECT_IDENTIFIER} specification."
    )
    status: Optional[SAMPluginStatus] = Field(
        ...,
        description=f"{class_identifier}.status[obj]: Optional, Read-only. Stateful status information about the {OBJECT_IDENTIFIER}.",
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
