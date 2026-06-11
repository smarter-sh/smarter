"""Smarter API Manifest - Prompt.status."""

import os
from typing import ClassVar

from smarter.apps.prompt.manifest.models.prompt_history.const import MANIFEST_KIND
from smarter.lib.manifest.models import AbstractSAMStatusBase

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMPromptHistoryStatus(AbstractSAMStatusBase):
    """Smarter API Prompt Manifest - Status class."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER
