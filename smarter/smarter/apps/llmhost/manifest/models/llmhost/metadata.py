"""Smarter API Manifest - LLMHost.metadata."""

import os
from typing import ClassVar

# LLMHost
from smarter.apps.llmhost.manifest.models.llmhost.const import MANIFEST_KIND
from smarter.lib.manifest.models import AbstractSAMMetadataBase

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMLLMHostMetadata(AbstractSAMMetadataBase):
    """Smarter API LLMHost Manifest - Metadata class."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER
