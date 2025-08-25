"""Smarter API Manifest - Account.status"""

import os
from datetime import datetime
from typing import ClassVar

from pydantic import EmailStr, Field

from smarter.apps.account.manifest.models.account.const import MANIFEST_KIND
from smarter.lib.manifest.models import AbstractSAMStatusBase


filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMProviderStatus(AbstractSAMStatusBase):
    """Smarter API Provider Manifest - Status class."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    owner: str = Field(
        None,
        description=f"{class_identifier}.owner: The designated Smarter user that owns this {MANIFEST_KIND}. Read only.",
    )

    created: datetime = Field(
        None,
        description=f"{class_identifier}.created: The date in which this {MANIFEST_KIND} was created. Read only.",
    )

    modified: datetime = Field(
        None,
        description=f"{class_identifier}.modified: The date in which this {MANIFEST_KIND} was most recently changed. Read only.",
    )

    is_active: bool = Field(
        True,
        description=f"{class_identifier}.is_active: Indicates whether this {MANIFEST_KIND} is currently active. Read only.",
    )
    is_flagged: bool = Field(
        False,
        description=f"{class_identifier}.is_flagged: Indicates whether this {MANIFEST_KIND} has been flagged for review. Read only.",
    )
    is_deprecated: bool = Field(
        False,
        description=f"{class_identifier}.is_deprecated: Indicates whether this {MANIFEST_KIND} is deprecated. Read only.",
    )
    is_suspended: bool = Field(
        False,
        description=f"{class_identifier}.is_suspended: Indicates whether this {MANIFEST_KIND} is currently suspended. Read only.",
    )
    is_verified: bool = Field(
        False,
        description=f"{class_identifier}.is_verified: Indicates whether this {MANIFEST_KIND} has been verified. Read only.",
    )
    ownership_requested: EmailStr = Field(
        None,
        description=f"{class_identifier}.ownership_requested: The Smarter user that has requested ownership of this {MANIFEST_KIND}. Read only.",
    )
    contact_email_verified: datetime = Field(
        None,
        description=f"{class_identifier}.contact_email_verified: The date in which the contact email for this {MANIFEST_KIND} was verified. Read only.",
    )
    support_email_verified: datetime = Field(
        None,
        description=f"{class_identifier}.support_email_verified: The date in which the support email for this {MANIFEST_KIND} was verified. Read only.",
    )
    tos_accepted_at: datetime = Field(
        None,
        description=f"{class_identifier}.tos_accepted_at: The date in which the Terms of Service for this {MANIFEST_KIND} were accepted. Read only.",
    )
    tos_accepted_by: EmailStr = Field(
        None,
        description=f"{class_identifier}.tos_accepted_by: The Smarter user that accepted the Terms of Service for this {MANIFEST_KIND}. Read only.",
    )
    can_activate: bool = Field(
        True,
        description=f"{class_identifier}.can_activate: Indicates whether this {MANIFEST_KIND} can be activated. Read only.",
    )
