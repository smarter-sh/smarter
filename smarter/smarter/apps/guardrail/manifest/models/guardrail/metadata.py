"""Smarter API Manifest - Guardrail.metadata."""

import os
from typing import ClassVar

# Guardrail
from smarter.apps.guardrail.manifest.models.guardrail.const import MANIFEST_KIND
from smarter.lib.manifest.models import AbstractSAMMetadataBase

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMGuardrailMetadata(AbstractSAMMetadataBase):
    """Smarter API Guardrail Manifest - Metadata class."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER
