"""Smarter API Vectorsearch Manifest."""

from typing import ClassVar, Optional

from pydantic import Field

from smarter.apps.vectorsearch.manifest.models.vectorsearch.const import MANIFEST_KIND
from smarter.lib.manifest.enum import SAMKeys
from smarter.lib.manifest.models import AbstractSAMBase

from .metadata import SAMVectorsearchMetadata
from .spec import SAMVectorsearchSpec
from .status import SAMVectorsearchStatus

MODULE_IDENTIFIER = MANIFEST_KIND


class SAMVectorsearch(AbstractSAMBase):
    """Smarter API Manifest - Vectorsearch."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    metadata: SAMVectorsearchMetadata = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.METADATA.value}[obj]: Required, the {MANIFEST_KIND} metadata.",
    )
    spec: SAMVectorsearchSpec = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.SPEC.value}[obj]: Required, the {MANIFEST_KIND} specification.",
    )
    status: Optional[SAMVectorsearchStatus] = Field(
        default=None,
        description=f"{class_identifier}.{SAMKeys.STATUS.value}[obj]: Optional, Read-only. Stateful status information about the {MANIFEST_KIND}.",
    )
