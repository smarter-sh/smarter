"""Smarter API Orchestrator Manifest."""

from typing import ClassVar, Optional

from pydantic import Field

from smarter.apps.orchestrator.manifest.models.orchestrator.const import MANIFEST_KIND
from smarter.lib.manifest.enum import SAMKeys
from smarter.lib.manifest.models import AbstractSAMBase

from .metadata import SAMOrchestratorMetadata
from .spec import SAMOrchestratorSpec
from .status import SAMOrchestratorStatus

MODULE_IDENTIFIER = MANIFEST_KIND


class SAMOrchestrator(AbstractSAMBase):
    """Smarter API Manifest - Orchestrator."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    metadata: SAMOrchestratorMetadata = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.METADATA.value}[obj]: Required, the {MANIFEST_KIND} metadata.",
    )
    spec: SAMOrchestratorSpec = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.SPEC.value}[obj]: Required, the {MANIFEST_KIND} specification.",
    )
    status: Optional[SAMOrchestratorStatus] = Field(
        default=None,
        description=f"{class_identifier}.{SAMKeys.STATUS.value}[obj]: Optional, Read-only. Stateful status information about the {MANIFEST_KIND}.",
    )
