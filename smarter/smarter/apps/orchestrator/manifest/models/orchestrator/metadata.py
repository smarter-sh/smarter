"""Smarter API Manifest - Orchestrator.metadata."""

import os
from typing import ClassVar

# Orchestrator
from smarter.apps.orchestrator.manifest.models.orchestrator.const import MANIFEST_KIND
from smarter.lib.manifest.models import AbstractSAMMetadataBase

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMOrchestratorMetadata(AbstractSAMMetadataBase):
    """Smarter API Orchestrator Manifest - Metadata class."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER
