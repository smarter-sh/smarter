"""Smarter API Manifest - PromptToolCall.status."""

import os
from typing import ClassVar

from smarter.apps.prompt.manifest.models.prompt_tool_call.const import MANIFEST_KIND
from smarter.lib.manifest.models import AbstractSAMStatusBase

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMPromptToolCallStatus(AbstractSAMStatusBase):
    """Smarter API PromptToolCall Manifest - Status class."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER
