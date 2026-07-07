"""Smarter API Manifest - MCPClient.status."""

import os
from typing import ClassVar

from pydantic import Field

from smarter.apps.mcpclient.manifest.models.mcpclient.const import MANIFEST_KIND
from smarter.lib.manifest.models import AbstractSAMStatusBase

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMMCPClientStatus(AbstractSAMStatusBase):
    """Smarter API MCPClient Manifest - Status class."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    accountNumber: str = Field(
        description=f"{class_identifier}.account_number: The account owner of this {MANIFEST_KIND}. Read only.",
    )

    username: str = Field(
        description=f"{class_identifier}.username: The Smarter user who created this {MANIFEST_KIND}. Read only.",
    )
