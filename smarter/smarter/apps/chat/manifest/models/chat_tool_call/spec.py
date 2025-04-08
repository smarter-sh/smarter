"""Smarter API ChatToolCall - ChatToolCall.spec"""

import os
from typing import ClassVar

from smarter.apps.chat.manifest.models.chat_tool_call.const import MANIFEST_KIND
from smarter.lib.manifest.models import AbstractSAMSpecBase


filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMChatToolCallSpecConfig(AbstractSAMSpecBase):
    """Smarter API ChatToolCall Manifest ChatToolCall.spec.config"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".configuration"
