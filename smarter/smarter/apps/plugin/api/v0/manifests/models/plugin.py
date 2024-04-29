"""Smarter API V0 Plugin Manifest"""

from typing import Optional

from pydantic import Field, model_validator

from smarter.apps.api.v0.manifests.exceptions import SAMValidationError
from smarter.apps.api.v0.manifests.models import SAM

# Plugin
from smarter.apps.plugin.api.v0.manifests.enum import SAMPluginMetadataClassValues

from .metadata import SAMPluginMetadata
from .spec import SAMPluginSpec
from .status import SAMPluginStatus


class SAMPlugin(SAM):
    """Smarter API V0 Manifest - Plugin"""

    metadata: SAMPluginMetadata = Field(..., description="Plugin.metadata: the Plugin metadata")
    spec: SAMPluginSpec = Field(..., description="Plugin.spec: the Plugin spec")
    status: Optional[SAMPluginStatus] = Field(..., description="Plugin.status: Read-only. the Plugin status")

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
