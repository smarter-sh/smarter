"""Smarter API Chat Manifest"""

from typing import ClassVar, Optional

from pydantic import Field

from smarter.apps.plugin.manifest.models.plugin.const import MANIFEST_KIND
from smarter.lib.manifest.enum import SAMKeys
from smarter.lib.manifest.models import AbstractSAMBase

from .metadata import SAMChatHistoryMetadata
from .spec import SAMChatHistorySpecConfig
from .status import SAMChatHistoryStatus


MODULE_IDENTIFIER = MANIFEST_KIND


class SAMChatHistory(AbstractSAMBase):
    """Smarter API Manifest - Chat"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    metadata: SAMChatHistoryMetadata = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.METADATA.value}[obj]: Required, the {MANIFEST_KIND} metadata.",
    )
    spec: SAMChatHistorySpecConfig = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.SPEC.value}[obj]: Required, the {MANIFEST_KIND} specification.",
    )
    status: Optional[SAMChatHistoryStatus] = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.STATUS.value}[obj]: Optional, Read-only. Stateful status information about the {MANIFEST_KIND}.",
    )
