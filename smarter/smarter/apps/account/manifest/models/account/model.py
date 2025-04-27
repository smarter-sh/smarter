"""Smarter API Account Manifest"""

from typing import ClassVar, Optional

from pydantic import Field

from smarter.apps.account.manifest.models.account.const import MANIFEST_KIND
from smarter.lib.manifest.enum import SAMKeys
from smarter.lib.manifest.models import AbstractSAMBase

from .metadata import SAMAccountMetadata
from .spec import SAMAccountSpec
from .status import SAMAccountStatus


MODULE_IDENTIFIER = MANIFEST_KIND


class SAMAccount(AbstractSAMBase):
    """Smarter API Manifest - Account"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    metadata: SAMAccountMetadata = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.METADATA.value}[obj]: Required, the {MANIFEST_KIND} metadata.",
    )
    spec: SAMAccountSpec = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.SPEC.value}[obj]: Required, the {MANIFEST_KIND} specification.",
    )
    status: Optional[SAMAccountStatus] = Field(
        default=None,
        description=f"{class_identifier}.{SAMKeys.STATUS.value}[obj]: Optional, Read-only. Stateful status information about the {MANIFEST_KIND}.",
        exclude=True,
    )
