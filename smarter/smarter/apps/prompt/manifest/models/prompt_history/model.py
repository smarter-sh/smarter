"""Smarter API Prompt Manifest."""

from typing import ClassVar, Optional

from pydantic import Field

from smarter.apps.prompt.manifest.models.prompt_history.const import MANIFEST_KIND
from smarter.lib.manifest.enum import SAMKeys
from smarter.lib.manifest.models import AbstractSAMBase

from .metadata import SAMPromptHistoryMetadata
from .spec import SAMPromptHistorySpecConfig
from .status import SAMPromptHistoryStatus

MODULE_IDENTIFIER = MANIFEST_KIND


class SAMPromptHistory(AbstractSAMBase):
    """Smarter API Manifest - Prompt."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    metadata: SAMPromptHistoryMetadata = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.METADATA.value}[obj]: Required, the {MANIFEST_KIND} metadata.",
    )
    spec: SAMPromptHistorySpecConfig = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.SPEC.value}[obj]: Required, the {MANIFEST_KIND} specification.",
    )
    status: Optional[SAMPromptHistoryStatus] = Field(
        default=None,
        description=f"{class_identifier}.{SAMKeys.STATUS.value}[obj]: Optional, Read-only. Stateful status information about the {MANIFEST_KIND}.",
    )
