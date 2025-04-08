"""Smarter API Chat - Chat.metadata"""

import os
from typing import ClassVar

from smarter.apps.chat.manifest.models.chat_history.const import MANIFEST_KIND
from smarter.lib.manifest.models import AbstractSAMMetadataBase


filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMChatHistoryMetadata(AbstractSAMMetadataBase):
    """Smarter API Chat Manifest - Metadata class."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER
