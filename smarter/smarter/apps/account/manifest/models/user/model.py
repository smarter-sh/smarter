"""Smarter API User Manifest"""

from typing import ClassVar, Optional

from pydantic import Field

from smarter.apps.plugin.manifest.models.plugin.const import MANIFEST_KIND
from smarter.lib.manifest.enum import SAMKeys
from smarter.lib.manifest.models import AbstractSAMBase

from .metadata import SAMUserMetadata
from .spec import SAMUserSpec
from .status import SAMUserStatus


MODULE_IDENTIFIER = MANIFEST_KIND


class SAMUser(AbstractSAMBase):
    """Smarter API Manifest - User"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    metadata: SAMUserMetadata = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.METADATA.value}[obj]: Required, the {MANIFEST_KIND} metadata.",
    )
    spec: SAMUserSpec = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.SPEC.value}[obj]: Required, the {MANIFEST_KIND} specification.",
    )
    status: Optional[SAMUserStatus] = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.STATUS.value}[obj]: Optional, Read-only. Stateful status information about the {MANIFEST_KIND}.",
    )
