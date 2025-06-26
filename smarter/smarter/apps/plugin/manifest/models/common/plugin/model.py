"""Smarter API Plugin Manifest"""

from typing import ClassVar, Optional

from pydantic import Field

from smarter.apps.plugin.manifest.models.common.plugin.metadata import (
    SAMPluginCommonMetadata,
)
from smarter.apps.plugin.manifest.models.common.plugin.spec import SAMPluginCommonSpec
from smarter.apps.plugin.manifest.models.common.plugin.status import (
    SAMPluginCommonStatus,
)
from smarter.lib.manifest.enum import SAMKeys
from smarter.lib.manifest.models import AbstractSAMBase

from .const import MANIFEST_KIND


MODULE_IDENTIFIER = MANIFEST_KIND


class SAMPluginCommon(AbstractSAMBase):
    """Smarter API Manifest - Common Plugin Base Model"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    metadata: SAMPluginCommonMetadata = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.METADATA.value}[obj]: Required, the {MANIFEST_KIND} metadata.",
    )

    spec: SAMPluginCommonSpec = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.SPEC.value}[obj]: Required, the {MANIFEST_KIND} specification.",
    )

    status: Optional[SAMPluginCommonStatus] = Field(
        default=None,
        description=f"{class_identifier}.{SAMKeys.STATUS.value}[obj]: Optional, Read-only. Stateful status information about the {MANIFEST_KIND}.",
        exclude=True,
    )
