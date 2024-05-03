"""Smarter API V0 Plugin Manifest"""

import logging
from typing import ClassVar, Optional

from pydantic import Field, model_validator

from smarter.apps.api.v0.manifests.enum import SAMKeys
from smarter.apps.api.v0.manifests.exceptions import SAMValidationError
from smarter.apps.api.v0.manifests.models import AbstractSAMBase
from smarter.apps.plugin.api.v0.manifests.enum import (
    SAMPluginMetadataClass,
    SAMPluginMetadataClassValues,
    SAMPluginMetadataKeys,
    SAMPluginSpecKeys,
)

from .const import OBJECT_IDENTIFIER
from .metadata import SAMPluginMetadata
from .spec import SAMPluginSpec
from .status import SAMPluginStatus


MODULE_IDENTIFIER = OBJECT_IDENTIFIER

logger = logging.getLogger(__name__)


class SAMPlugin(AbstractSAMBase):
    """Smarter API V0 Manifest - Plugin"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    metadata: SAMPluginMetadata = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.METADATA.value}[obj]: Required, the {OBJECT_IDENTIFIER} metadata.",
    )
    spec: SAMPluginSpec = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.SPEC.value}[obj]: Required, the {OBJECT_IDENTIFIER} specification.",
    )
    status: Optional[SAMPluginStatus] = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.STATUS.value}[obj]: Optional, Read-only. Stateful status information about the {OBJECT_IDENTIFIER}.",
    )

    @model_validator(mode="after")
    def validate_business_rules(self) -> "SAMPlugin":
        """Plugin-level business rule validations"""
        err_desc_model_name = f"{self.kind}.{SAMKeys.SPEC.value}.{SAMPluginSpecKeys.DATA.value}"

        # Validate that the correct Plugin.spec.data is present when the Plugin.metadata.pluginClass is 'static', 'sql', or 'api'
        # example error message: "Plugin.spec.data.staticData is required when Plugin.metadata.pluginClass is 'static'"
        if self.metadata.pluginClass == SAMPluginMetadataClassValues.STATIC.value and not self.spec.data.staticData:
            raise SAMValidationError(
                f"{err_desc_model_name}.{SAMPluginMetadataClass.STATIC_DATA.value} is required when {self.kind}.{SAMPluginMetadataKeys.PLUGIN_CLASS.value} is '{SAMPluginMetadataClassValues.STATIC.value}'"
            )

        if self.metadata.pluginClass == SAMPluginMetadataClassValues.SQL.value and not self.spec.data.sqlData:
            raise SAMValidationError(
                f"{err_desc_model_name}.{SAMPluginMetadataClass.SQL_DATA.value} is required when {self.kind}.{SAMPluginMetadataKeys.PLUGIN_CLASS.value} is '{SAMPluginMetadataClassValues.SQL.value}'"
            )

        if self.metadata.pluginClass == SAMPluginMetadataClassValues.API.value and not self.spec.data.apiData:
            raise SAMValidationError(
                f"{err_desc_model_name}.{SAMPluginMetadataClass.API_DATA.value} is required when {self.kind}.{SAMPluginMetadataKeys.PLUGIN_CLASS.value} is '{SAMPluginMetadataClassValues.API.value}'"
            )

        return self
