"""Smarter API Account Manifest"""

from typing import ClassVar, Optional

from pydantic import Field

from smarter.apps.provider.manifest.models.provider.const import MANIFEST_KIND
from smarter.lib.manifest.enum import SAMKeys
from smarter.lib.manifest.models import AbstractSAMBase

from .metadata import SAMProviderMetadata
from .spec import SAMProviderSpec
from .status import SAMProviderStatus


MODULE_IDENTIFIER = MANIFEST_KIND


class SAMProvider(AbstractSAMBase):
    """Smarter API Manifest - Account"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    metadata: SAMProviderMetadata = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.METADATA.value}[obj]: Required, the {MANIFEST_KIND} metadata.",
    )
    spec: SAMProviderSpec = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.SPEC.value}[obj]: Required, the {MANIFEST_KIND} specification.",
    )
    status: Optional[SAMProviderStatus] = Field(
        default=None,
        description=f"{class_identifier}.{SAMKeys.STATUS.value}[obj]: Optional, Read-only. Stateful status information about the {MANIFEST_KIND}.",
        exclude=True,
    )
