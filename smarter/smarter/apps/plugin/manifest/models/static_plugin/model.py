"""Smarter API Plugin Manifest"""

import logging
from typing import ClassVar, Optional

from pydantic import Field, model_validator

from smarter.apps.plugin.manifest.enum import (
    SAMPluginCommonMetadataClass,
    SAMPluginCommonMetadataClassValues,
    SAMPluginCommonMetadataKeys,
    SAMPluginSpecKeys,
)
from smarter.apps.plugin.manifest.models.common.plugin.metadata import (
    SAMPluginCommonMetadata,
)
from smarter.apps.plugin.manifest.models.common.plugin.status import (
    SAMPluginCommonStatus,
)
from smarter.lib.manifest.enum import SAMKeys
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.models import AbstractSAMBase

from .const import MANIFEST_KIND
from .spec import SAMPluginStaticSpec


MODULE_IDENTIFIER = MANIFEST_KIND

logger = logging.getLogger(__name__)


class SAMStaticPlugin(AbstractSAMBase):
    """Smarter API Manifest - Plugin"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    metadata: SAMPluginCommonMetadata = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.METADATA.value}[obj]: Required, the {MANIFEST_KIND} metadata.",
    )
    spec: SAMPluginStaticSpec = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.SPEC.value}[obj]: Required, the {MANIFEST_KIND} specification.",
    )
    status: Optional[SAMPluginCommonStatus] = Field(
        default=None,
        description=f"{class_identifier}.{SAMKeys.STATUS.value}[obj]: Optional, Read-only. Stateful status information about the {MANIFEST_KIND}.",
        exclude=True,
    )

    @model_validator(mode="after")
    def validate_business_rules(self) -> "SAMStaticPlugin":
        """Plugin-level business rule validations"""
        err_desc_model_name = f"{self.kind}.{SAMKeys.SPEC.value}.{SAMPluginSpecKeys.DATA.value}"

        # Validate that the correct Plugin.spec.data is present when the Plugin.metadata.pluginClass is 'static', 'sql', or 'api'
        # example error message: "Plugin.spec.data.staticData is required when Plugin.metadata.pluginClass is 'static'"
        if (
            self.metadata.pluginClass == SAMPluginCommonMetadataClassValues.STATIC.value
            and not self.spec.data.staticData
        ):
            raise SAMValidationError(
                f"{err_desc_model_name}.{SAMPluginCommonMetadataClass.STATIC_DATA.value} is required when {self.kind}.{SAMPluginCommonMetadataKeys.PLUGIN_CLASS.value} is '{SAMPluginCommonMetadataClassValues.STATIC.value}'"
            )

        if self.metadata.pluginClass == SAMPluginCommonMetadataClassValues.SQL.value and not self.spec.data.sqlData:
            raise SAMValidationError(
                f"{err_desc_model_name}.{SAMPluginCommonMetadataClass.SQL_DATA.value} is required when {self.kind}.{SAMPluginCommonMetadataKeys.PLUGIN_CLASS.value} is '{SAMPluginCommonMetadataClassValues.SQL.value}'"
            )

        if self.metadata.pluginClass == SAMPluginCommonMetadataClassValues.API.value and not self.spec.data.apiData:
            raise SAMValidationError(
                f"{err_desc_model_name}.{SAMPluginCommonMetadataClass.API_DATA.value} is required when {self.kind}.{SAMPluginCommonMetadataKeys.PLUGIN_CLASS.value} is '{SAMPluginCommonMetadataClassValues.API.value}'"
            )

        return self
