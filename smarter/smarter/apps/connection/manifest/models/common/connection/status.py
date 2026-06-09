"""Smarter API Manifest - Connection.status"""

import os
from typing import ClassVar

from pydantic import Field

from smarter.lib.manifest.models import AbstractSAMStatusBase

from .const import MANIFEST_KIND

filename = os.path.splitext(os.path.basename(__file__))[0]

MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMConnectionCommonStatus(AbstractSAMStatusBase):
    """Smarter API Connection Manifest - Status class."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    account_number: str = Field(
        description=f"{class_identifier}.account_number: The account owner of this {MANIFEST_KIND}. Read only.",
    )

    username: str = Field(
        description=f"{class_identifier}.username: The Smarter user who created this {MANIFEST_KIND}. Read only.",
    )
