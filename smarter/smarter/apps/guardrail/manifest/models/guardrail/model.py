"""Smarter API Guardrail Manifest."""

from typing import ClassVar, Optional

from pydantic import Field

from smarter.apps.guardrail.manifest.models.guardrail.const import MANIFEST_KIND
from smarter.lib.manifest.enum import SAMKeys
from smarter.lib.manifest.models import AbstractSAMBase

from .metadata import SAMGuardrailMetadata
from .spec import SAMGuardrailSpec
from .status import SAMGuardrailStatus

MODULE_IDENTIFIER = MANIFEST_KIND


class SAMGuardrail(AbstractSAMBase):
    """Smarter API Manifest - Guardrail."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    metadata: SAMGuardrailMetadata = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.METADATA.value}[obj]: Required, the {MANIFEST_KIND} metadata.",
    )
    spec: SAMGuardrailSpec = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.SPEC.value}[obj]: Required, the {MANIFEST_KIND} specification.",
    )
    status: Optional[SAMGuardrailStatus] = Field(
        default=None,
        description=f"{class_identifier}.{SAMKeys.STATUS.value}[obj]: Optional, Read-only. Stateful status information about the {MANIFEST_KIND}.",
    )
