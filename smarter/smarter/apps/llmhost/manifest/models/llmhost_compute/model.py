"""Smarter API LLMHostCompute Manifest."""

from typing import ClassVar, Optional

from pydantic import Field

from smarter.apps.llmhost.manifest.models.llmhost_compute.const import MANIFEST_KIND
from smarter.lib.manifest.enum import SAMKeys
from smarter.lib.manifest.models import AbstractSAMBase

from .metadata import SAMLLMHostComputeMetadata
from .spec import SAMLLMHostComputeSpec
from .status import SAMLLMHostComputeStatus

MODULE_IDENTIFIER = MANIFEST_KIND


class SAMLLMHostCompute(AbstractSAMBase):
    """Smarter API Manifest - LLMHostCompute."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    metadata: SAMLLMHostComputeMetadata = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.METADATA.value}[obj]: Required, the {MANIFEST_KIND} metadata.",
    )
    spec: SAMLLMHostComputeSpec = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.SPEC.value}[obj]: Required, the {MANIFEST_KIND} specification.",
    )
    status: Optional[SAMLLMHostComputeStatus] = Field(
        default=None,
        description=f"{class_identifier}.{SAMKeys.STATUS.value}[obj]: Optional, Read-only. Stateful status information about the {MANIFEST_KIND}.",
    )
