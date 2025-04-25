"""Smarter API Secret Manifest"""

from typing import ClassVar, Optional

from pydantic import Field

from smarter.apps.account.manifest.models.secret.const import MANIFEST_KIND
from smarter.lib.manifest.enum import SAMKeys
from smarter.lib.manifest.models import AbstractSAMBase

from .metadata import SAMSecretMetadata
from .spec import SAMSecretSpec
from .status import SAMSecretStatus


MODULE_IDENTIFIER = MANIFEST_KIND


class SAMSecret(AbstractSAMBase):
    """Smarter API Manifest - Secret"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    metadata: SAMSecretMetadata = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.METADATA.value}[obj]: Required, the {MANIFEST_KIND} metadata.",
    )
    spec: SAMSecretSpec = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.SPEC.value}[obj]: Required, the {MANIFEST_KIND} specification.",
    )
    status: Optional[SAMSecretStatus] = Field(
        default=None,
        description=f"{class_identifier}.{SAMKeys.STATUS.value}[obj]: Optional, Read-only. Stateful status information about the {MANIFEST_KIND}.",
        exclude=True,
    )
