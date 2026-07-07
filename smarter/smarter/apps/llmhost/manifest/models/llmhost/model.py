"""Smarter API LLMHost Manifest."""

from typing import ClassVar, Optional

from pydantic import Field

from smarter.apps.llmhost.manifest.models.llmhost.const import MANIFEST_KIND
from smarter.lib.manifest.enum import SAMKeys
from smarter.lib.manifest.models import AbstractSAMBase

from .metadata import SAMLLMHostMetadata
from .spec import SAMLLMHostSpec
from .status import SAMLLMHostStatus

MODULE_IDENTIFIER = MANIFEST_KIND


class SAMLLMHost(AbstractSAMBase):
    """Smarter API Manifest - LLMHost."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    metadata: SAMLLMHostMetadata = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.METADATA.value}[obj]: Required, the {MANIFEST_KIND} metadata.",
    )
    spec: SAMLLMHostSpec = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.SPEC.value}[obj]: Required, the {MANIFEST_KIND} specification.",
    )
    status: Optional[SAMLLMHostStatus] = Field(
        default=None,
        description=f"{class_identifier}.{SAMKeys.STATUS.value}[obj]: Optional, Read-only. Stateful status information about the {MANIFEST_KIND}.",
    )
