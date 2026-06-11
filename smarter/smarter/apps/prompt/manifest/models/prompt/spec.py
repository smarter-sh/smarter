"""Smarter API Prompt - Prompt.spec."""

import os
from typing import ClassVar

from smarter.apps.prompt.manifest.models.prompt.const import MANIFEST_KIND
from smarter.lib.manifest.models import AbstractSAMSpecBase

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMPromptSpecConfig(AbstractSAMSpecBase):
    """Smarter API Prompt Manifest Prompt.spec.config."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".configuration"
