"""Smarter API Prompt Manifest."""

from typing import ClassVar, Optional

from pydantic import Field

from smarter.apps.prompt.manifest.models.prompt.const import MANIFEST_KIND
from smarter.lib.manifest.enum import SAMKeys
from smarter.lib.manifest.models import AbstractSAMBase

from .metadata import SAMPromptMetadata
from .spec import SAMPromptSpecConfig
from .status import SAMPromptStatus

MODULE_IDENTIFIER = MANIFEST_KIND


class SAMPrompt(AbstractSAMBase):
    """Smarter API Manifest - Prompt."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    metadata: SAMPromptMetadata = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.METADATA.value}[obj]: Required, the {MANIFEST_KIND} metadata.",
    )
    spec: SAMPromptSpecConfig = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.SPEC.value}[obj]: Required, the {MANIFEST_KIND} specification.",
    )
    status: Optional[SAMPromptStatus] = Field(
        default=None,
        description=f"{class_identifier}.{SAMKeys.STATUS.value}[obj]: Optional, Read-only. Stateful status information about the {MANIFEST_KIND}.",
    )
