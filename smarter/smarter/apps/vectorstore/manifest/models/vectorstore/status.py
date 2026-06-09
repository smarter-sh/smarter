"""Smarter API Manifest - Account.status"""

import os
from typing import ClassVar

from smarter.apps.account.manifest.models.account.const import MANIFEST_KIND
from smarter.lib.manifest.models import AbstractSAMStatusBase

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMVectorstoreStatus(AbstractSAMStatusBase):
    """Smarter API Vectorstore Manifest - Status class."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    vectorstore_status: str = "unknown"


__all__ = ["SAMVectorstoreStatus"]
