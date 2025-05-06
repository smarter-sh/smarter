"""Smarter API Plugin Manifest"""

from typing import ClassVar, Optional

from pydantic import Field

from smarter.apps.plugin.manifest.models.plugin.const import MANIFEST_KIND
from smarter.lib.manifest.enum import SAMKeys
from smarter.lib.manifest.models import AbstractSAMBase

from .metadata import SAMPluginDataSqlConnectionMetadata
from .spec import SAMPluginDataSqlConnectionSpec
from .status import SAMPluginDataSqlConnectionStatus


MODULE_IDENTIFIER = MANIFEST_KIND


class SAMPluginDataSqlConnection(AbstractSAMBase):
    """Smarter API Manifest - Plugin Data SQL Connection Model"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    metadata: SAMPluginDataSqlConnectionMetadata = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.METADATA.value}[obj]: Required, the {MANIFEST_KIND} metadata.",
    )
    spec: SAMPluginDataSqlConnectionSpec = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.SPEC.value}[obj]: Required, the {MANIFEST_KIND} specification.",
    )
    status: Optional[SAMPluginDataSqlConnectionStatus] = Field(
        default=None,
        description=f"{class_identifier}.{SAMKeys.STATUS.value}[obj]: Optional, Read-only. Stateful status information about the {MANIFEST_KIND}.",
        exclude=True,
    )
