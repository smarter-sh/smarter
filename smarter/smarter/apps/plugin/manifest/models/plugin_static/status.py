"""Smarter API Manifest - Plugin.status"""

import os
from datetime import datetime
from typing import ClassVar

from pydantic import Field

from smarter.apps.plugin.manifest.models.plugin_static.const import MANIFEST_KIND
from smarter.lib.manifest.models import AbstractSAMStatusBase


filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMPluginStatus(AbstractSAMStatusBase):
    """Smarter API Plugin Manifest - Status class."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    account_number: str = Field(
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
