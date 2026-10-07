"""Smarter API Manifest - Account.metadata"""

import os
from typing import ClassVar, Optional

from pydantic import Field

from smarter.apps.account.manifest.models.account.const import MANIFEST_KIND
from smarter.lib.manifest.models import AbstractSAMMetadataBase

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMAccountMetadata(AbstractSAMMetadataBase):
    """Smarter API Account Manifest - Metadata class."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    accountNumber: Optional[str] = Field(
        None,
        description=(
            f"{class_identifier}.accountNumber[str]. Your preassigned 12-digit account number for your Smarter {MANIFEST_KIND} in the format '####-####-####'. Read only."
        ),
    )
