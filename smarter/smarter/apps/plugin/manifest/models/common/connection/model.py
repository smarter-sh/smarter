"""Smarter API Plugin Manifest"""

from abc import abstractmethod
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


MODULE_IDENTIFIER = MANIFEST_KIND


class SAMConnectionCommon(AbstractSAMBase):
    """Smarter API Manifest - Common Connection Base Model"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    metadata: Optional[SAMConnectionCommonMetadata] = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.METADATA.value}[obj]: Required, the {MANIFEST_KIND} metadata.",
    )

    @property
    @abstractmethod
    def spec(self):
        """Abstract property for spec."""

    status: Optional[SAMConnectionCommonStatus] = Field(
        default=None,
        description=f"{class_identifier}.{SAMKeys.STATUS.value}[obj]: Optional, Read-only. Stateful status information about the {MANIFEST_KIND}.",
        exclude=True,
    )
