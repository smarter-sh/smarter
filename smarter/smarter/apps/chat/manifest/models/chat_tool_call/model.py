"""Smarter API ChatToolCall Manifest"""

from typing import ClassVar, Optional

from pydantic import Field

from smarter.apps.chat.manifest.models.chat_tool_call.const import MANIFEST_KIND
from smarter.lib.manifest.enum import SAMKeys
from smarter.lib.manifest.models import AbstractSAMBase

from .metadata import SAMChatToolCallMetadata
from .spec import SAMChatToolCallSpecConfig
from .status import SAMChatToolCallStatus


MODULE_IDENTIFIER = MANIFEST_KIND


class SAMChatToolCall(AbstractSAMBase):
    """Smarter API Manifest - ChatToolCall"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    metadata: SAMChatToolCallMetadata = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.METADATA.value}[obj]: Required, the {MANIFEST_KIND} metadata.",
    )
    spec: SAMChatToolCallSpecConfig = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.SPEC.value}[obj]: Required, the {MANIFEST_KIND} specification.",
    )
    status: Optional[SAMChatToolCallStatus] = Field(
        default=None,
        description=f"{class_identifier}.{SAMKeys.STATUS.value}[obj]: Optional, Read-only. Stateful status information about the {MANIFEST_KIND}.",
        exclude=True,
    )
