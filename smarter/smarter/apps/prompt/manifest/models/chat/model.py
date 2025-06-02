"""Smarter API Chat Manifest"""

from typing import ClassVar, Optional

from pydantic import Field

from smarter.apps.prompt.manifest.models.chat.const import MANIFEST_KIND
from smarter.lib.manifest.enum import SAMKeys
from smarter.lib.manifest.models import AbstractSAMBase

from .metadata import SAMChatMetadata
from .spec import SAMChatSpecConfig
from .status import SAMChatStatus


MODULE_IDENTIFIER = MANIFEST_KIND


class SAMChat(AbstractSAMBase):
    """Smarter API Manifest - Chat"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    metadata: SAMChatMetadata = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.METADATA.value}[obj]: Required, the {MANIFEST_KIND} metadata.",
    )
    spec: SAMChatSpecConfig = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.SPEC.value}[obj]: Required, the {MANIFEST_KIND} specification.",
    )
    status: Optional[SAMChatStatus] = Field(
        default=None,
        description=f"{class_identifier}.{SAMKeys.STATUS.value}[obj]: Optional, Read-only. Stateful status information about the {MANIFEST_KIND}.",
        exclude=True,
    )
