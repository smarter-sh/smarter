"""Smarter API Manifest - Account.metadata."""

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
            f"{class_identifier}.accountNumber[str]. The 12-digit number of the Smarter {MANIFEST_KIND}, in the format "
            "'####-####-####'. Applying a manifest that creates the account gives it this number, so that an "
            "organization's accounts have the same numbers on every platform; omitted, a new account gets a random "
            "one. It never changes: a manifest whose number differs from its existing account's is refused."
        ),
    )
