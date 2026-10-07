"""Smarter API Manifest - Budget.metadata."""

import os
from typing import ClassVar

from smarter.apps.account.manifest.models.budget.const import MANIFEST_KIND
from smarter.lib.manifest.models import AbstractSAMMetadataBase

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMBudgetMetadata(AbstractSAMMetadataBase):
    """Smarter API Budget Manifest - Metadata class."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER
