"""Smarter API Manifest - LLMHostCompute.metadata."""

import os
from typing import ClassVar

from smarter.apps.llmhost.manifest.models.llmhost_compute.const import MANIFEST_KIND
from smarter.lib.manifest.models import AbstractSAMMetadataBase

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMLLMHostComputeMetadata(AbstractSAMMetadataBase):
    """Smarter API LLMHostCompute Manifest - Metadata class."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER
