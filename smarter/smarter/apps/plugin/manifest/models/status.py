"""Smarter API Manifest - Plugin.status"""

import os
from datetime import datetime
from typing import ClassVar

from pydantic import Field

from smarter.lib.manifest.models import AbstractSAMStatusBase

from ..const import MANIFEST_KIND


filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMPluginStatus(AbstractSAMStatusBase):
    """Smarter API Plugin Manifest - Status class."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    created: datetime = Field(
        None,
        description=f"{class_identifier}.created: The date in which this {MANIFEST_KIND} was created. Read only.",
    )

    modified: datetime = Field(
        None,
        description=f"{class_identifier}.created: The date in which this {MANIFEST_KIND} was most recently changed. Read only.",
    )
