"""Smarter API PromptToolCall - PromptToolCall.metadata."""

import os
from typing import ClassVar

from smarter.apps.prompt.manifest.models.prompt_tool_call.const import MANIFEST_KIND
from smarter.lib.manifest.models import AbstractSAMMetadataBase

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMPromptToolCallMetadata(AbstractSAMMetadataBase):
    """Smarter API PromptToolCall Manifest - Metadata class."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER
