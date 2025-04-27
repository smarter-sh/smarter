"""Smarter API Manifest - User.status"""

import os
from datetime import datetime
from typing import ClassVar

from pydantic import Field

from smarter.apps.account.manifest.models.secret.const import MANIFEST_KIND
from smarter.lib.manifest.models import AbstractSAMStatusBase


filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMSecretStatus(AbstractSAMStatusBase):
    """Smarter API Secret Manifest - Status class."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    accountNumber: str = Field(
        None,
        description=f"{class_identifier}.account_number: The account owner of this {MANIFEST_KIND}. Read only.",
    )

    username: str = Field(
        None,
        description=f"{class_identifier}.account_number: The Smarter user who created this {MANIFEST_KIND}. Read only.",
    )

    created: datetime = Field(
        None,
        description=f"{class_identifier}.created: The date in which this {MANIFEST_KIND} was created. Read only.",
    )

    modified: datetime = Field(
        None,
        description=f"{class_identifier}.modified: The date in which this {MANIFEST_KIND} was most recently changed. Read only.",
    )

    lastAccessed: datetime = Field(
        None,
        description=f"{class_identifier}.last_accessed: The date in which this {MANIFEST_KIND} was most recently accessed. Read only.",
    )
