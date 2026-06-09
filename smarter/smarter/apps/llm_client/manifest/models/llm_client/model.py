"""Smarter API LLMClient Manifest."""

from typing import ClassVar, Optional

from pydantic import Field

from smarter.apps.llm_client.manifest.models.llm_client.const import MANIFEST_KIND
from smarter.lib.manifest.enum import SAMKeys
from smarter.lib.manifest.models import AbstractSAMBase

from .metadata import SAMLLMClientMetadata
from .spec import SAMLLMClientSpec
from .status import SAMLLMClientStatus

MODULE_IDENTIFIER = MANIFEST_KIND


class SAMLLMClient(AbstractSAMBase):
    """Smarter API Manifest - LLMClient."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    metadata: SAMLLMClientMetadata = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.METADATA.value}[obj]: Required, the {MANIFEST_KIND} metadata.",
    )
    spec: SAMLLMClientSpec = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.SPEC.value}[obj]: Required, the {MANIFEST_KIND} specification.",
    )
    status: Optional[SAMLLMClientStatus] = Field(
        default=None,
        description=f"{class_identifier}.{SAMKeys.STATUS.value}[obj]: Optional, Read-only. Stateful status information about the {MANIFEST_KIND}.",
    )
