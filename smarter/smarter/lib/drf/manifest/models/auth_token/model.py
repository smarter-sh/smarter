"""Smarter API SmarterAuthToken Manifest"""

from typing import ClassVar, Optional

from pydantic import Field

from smarter.apps.plugin.manifest.models.plugin.const import MANIFEST_KIND
from smarter.lib.manifest.enum import SAMKeys
from smarter.lib.manifest.models import AbstractSAMBase

from .metadata import SAMSmarterAuthTokenMetadata
from .spec import SAMSAMSmarterAuthTokenSpecConfigSpec
from .status import SAMSmarterAuthTokenStatus


MODULE_IDENTIFIER = MANIFEST_KIND


class SAMSmarterAuthToken(AbstractSAMBase):
    """Smarter API Manifest - SmarterAuthToken"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    metadata: SAMSmarterAuthTokenMetadata = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.METADATA.value}[obj]: Required, the {MANIFEST_KIND} metadata.",
    )
    spec: SAMSAMSmarterAuthTokenSpecConfigSpec = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.SPEC.value}[obj]: Required, the {MANIFEST_KIND} specification.",
    )
    status: Optional[SAMSmarterAuthTokenStatus] = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.STATUS.value}[obj]: Optional, Read-only. Stateful status information about the {MANIFEST_KIND}.",
    )
