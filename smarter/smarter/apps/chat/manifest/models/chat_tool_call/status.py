"""Smarter API Manifest - ChatToolCall.status"""

import os
from datetime import datetime
from typing import ClassVar, Optional

from pydantic import Field

from smarter.apps.chat.manifest.models.chat_tool_call.const import MANIFEST_KIND
from smarter.lib.manifest.models import AbstractSAMStatusBase


filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMChatToolCallStatus(AbstractSAMStatusBase):
    """Smarter API ChatToolCall Manifest - Status class."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    created: Optional[datetime] = Field(
        ...,
        description=f"{class_identifier}.created: The date in which this {MANIFEST_KIND} was created. Read only.",
    )

    modified: Optional[datetime] = Field(
        ...,
        description=f"{class_identifier}.modified: The date in which this {MANIFEST_KIND} was most recently changed. Read only.",
    )
