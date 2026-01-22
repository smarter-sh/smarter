"""Smarter API Manifest - User.status"""

import os
from datetime import datetime
from typing import ClassVar, Optional

from pydantic import Field

from smarter.apps.account.manifest.models.secret.const import MANIFEST_KIND
from smarter.lib.manifest.models import AbstractSAMStatusBase

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMSecretStatus(AbstractSAMStatusBase):
    """Smarter API Secret Manifest - Status class (read-only, like Kubernetes status attributes)."""

    # pylint: disable=missing-class-docstring
    class Config:
        frozen = True  # Make all fields read-only after creation, like Kubernetes status

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    accountNumber: str = Field(
        description=f"{class_identifier}.account_number: The account owner of this {MANIFEST_KIND}. Read only.",
    )

    username: str = Field(
        description=f"{class_identifier}.account_number: The Smarter user who created this {MANIFEST_KIND}. Read only.",
    )

    created: datetime = Field(
        description=f"{class_identifier}.created: The date in which this {MANIFEST_KIND} was created. Read only.",
    )

    modified: datetime = Field(
        description=f"{class_identifier}.modified: The date in which this {MANIFEST_KIND} was most recently changed. Read only.",
    )

    last_accessed: Optional[datetime] = Field(
        None,
        description=f"{class_identifier}.last_accessed: The date in which this {MANIFEST_KIND} was most recently accessed. Read only.",
    )
