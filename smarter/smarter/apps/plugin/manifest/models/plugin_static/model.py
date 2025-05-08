"""Smarter API Plugin Manifest"""

import logging
from typing import ClassVar, Optional

from pydantic import Field, model_validator

from smarter.apps.plugin.manifest.enum import (
    SAMPluginSpecKeys,
    SAMPluginStaticMetadataClass,
    SAMPluginStaticMetadataClassValues,
    SAMPluginStaticMetadataKeys,
)
from smarter.apps.plugin.manifest.models.plugin_static.const import MANIFEST_KIND
from smarter.lib.manifest.enum import SAMKeys
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.models import AbstractSAMBase

from .metadata import SAMPluginStaticMetadata
from .spec import SAMPluginSpec
from .status import SAMPluginStatus


MODULE_IDENTIFIER = MANIFEST_KIND

logger = logging.getLogger(__name__)


class SAMPlugin(AbstractSAMBase):
    """Smarter API Manifest - Plugin"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    metadata: SAMPluginStaticMetadata = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.METADATA.value}[obj]: Required, the {MANIFEST_KIND} metadata.",
    )
    spec: SAMPluginSpec = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.SPEC.value}[obj]: Required, the {MANIFEST_KIND} specification.",
    )
    status: Optional[SAMPluginStatus] = Field(
        default=None,
        description=f"{class_identifier}.{SAMKeys.STATUS.value}[obj]: Optional, Read-only. Stateful status information about the {MANIFEST_KIND}.",
        exclude=True,
    )

    @model_validator(mode="after")
    def validate_business_rules(self) -> "SAMPlugin":
        """Plugin-level business rule validations"""
        err_desc_model_name = f"{self.kind}.{SAMKeys.SPEC.value}.{SAMPluginSpecKeys.DATA.value}"

        # Validate that the correct Plugin.spec.data is present when the Plugin.metadata.pluginClass is 'static', 'sql', or 'api'
        # example error message: "Plugin.spec.data.staticData is required when Plugin.metadata.pluginClass is 'static'"
        if (
            self.metadata.pluginClass == SAMPluginStaticMetadataClassValues.STATIC.value
            and not self.spec.data.staticData
        ):
            raise SAMValidationError(
                f"{err_desc_model_name}.{SAMPluginStaticMetadataClass.STATIC_DATA.value} is required when {self.kind}.{SAMPluginStaticMetadataKeys.PLUGIN_CLASS.value} is '{SAMPluginStaticMetadataClassValues.STATIC.value}'"
            )

        if self.metadata.pluginClass == SAMPluginStaticMetadataClassValues.SQL.value and not self.spec.data.sqlData:
            raise SAMValidationError(
                f"{err_desc_model_name}.{SAMPluginStaticMetadataClass.SQL_DATA.value} is required when {self.kind}.{SAMPluginStaticMetadataKeys.PLUGIN_CLASS.value} is '{SAMPluginStaticMetadataClassValues.SQL.value}'"
            )

        if self.metadata.pluginClass == SAMPluginStaticMetadataClassValues.API.value and not self.spec.data.apiData:
            raise SAMValidationError(
                f"{err_desc_model_name}.{SAMPluginStaticMetadataClass.API_DATA.value} is required when {self.kind}.{SAMPluginStaticMetadataKeys.PLUGIN_CLASS.value} is '{SAMPluginStaticMetadataClassValues.API.value}'"
            )

        return self
