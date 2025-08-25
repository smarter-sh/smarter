"""Smarter API Plugin Manifest"""

from typing import ClassVar, Optional

from pydantic import Field

from smarter.apps.plugin.manifest.models.common.connection.metadata import (
    SAMConnectionCommonMetadata,
)
from smarter.apps.plugin.manifest.models.common.connection.status import (
    SAMConnectionCommonStatus,
)
from smarter.lib.manifest.enum import SAMKeys
from smarter.lib.manifest.models import AbstractSAMBase

from .const import MANIFEST_KIND
from .spec import SAMSqlConnectionSpec


MODULE_IDENTIFIER = MANIFEST_KIND


class SAMSqlConnection(AbstractSAMBase):
    """Smarter API Manifest - SqlPlugin Connection Model"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    metadata: SAMConnectionCommonMetadata = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.METADATA.value}[obj]: Required, the {MANIFEST_KIND} metadata.",
    )
    spec: SAMSqlConnectionSpec = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.SPEC.value}[obj]: Required, the {MANIFEST_KIND} specification.",
    )
    status: Optional[SAMConnectionCommonStatus] = Field(
        default=None,
        description=f"{class_identifier}.{SAMKeys.STATUS.value}[obj]: Optional, Read-only. Stateful status information about the {MANIFEST_KIND}.",
        exclude=True,
    )
