"""Smarter API PromptToolCall Manifest."""

from typing import ClassVar, Optional

from pydantic import Field

from smarter.apps.prompt.manifest.models.prompt_tool_call.const import MANIFEST_KIND
from smarter.lib.manifest.enum import SAMKeys
from smarter.lib.manifest.models import AbstractSAMBase

from .metadata import SAMPromptToolCallMetadata
from .spec import SAMPromptToolCallSpecConfig
from .status import SAMPromptToolCallStatus

MODULE_IDENTIFIER = MANIFEST_KIND


class SAMPromptToolCall(AbstractSAMBase):
    """Smarter API Manifest - PromptToolCall."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    metadata: SAMPromptToolCallMetadata = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.METADATA.value}[obj]: Required, the {MANIFEST_KIND} metadata.",
    )
    spec: SAMPromptToolCallSpecConfig = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.SPEC.value}[obj]: Required, the {MANIFEST_KIND} specification.",
    )
    status: Optional[SAMPromptToolCallStatus] = Field(
        default=None,
        description=f"{class_identifier}.{SAMKeys.STATUS.value}[obj]: Optional, Read-only. Stateful status information about the {MANIFEST_KIND}.",
    )
