"""Smarter API Manifest - Account.status"""

import os
from datetime import datetime
from typing import ClassVar

from pydantic import Field

from smarter.apps.account.manifest.models.account.const import MANIFEST_KIND
from smarter.lib.manifest.models import AbstractSAMStatusBase


filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMAccountStatus(AbstractSAMStatusBase):
    """Smarter API Account Manifest - Status class."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    adminAccount: str = Field(
        None,
        description=f"{class_identifier}.adminAccount: The designated Smarter admin user for this {MANIFEST_KIND}. Read only.",
    )

    created: datetime = Field(
        None,
        description=f"{class_identifier}.created: The date in which this {MANIFEST_KIND} was created. Read only.",
    )

    modified: datetime = Field(
        None,
        description=f"{class_identifier}.modified: The date in which this {MANIFEST_KIND} was most recently changed. Read only.",
    )
