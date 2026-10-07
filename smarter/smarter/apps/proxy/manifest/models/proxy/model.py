"""Smarter API Proxy Manifest."""

from typing import ClassVar, Optional

from pydantic import Field

from smarter.apps.proxy.manifest.models.proxy.const import MANIFEST_KIND
from smarter.lib.manifest.enum import SAMKeys
from smarter.lib.manifest.models import AbstractSAMBase

from .metadata import SAMProxyMetadata
from .spec import SAMProxySpec
from .status import SAMProxyStatus

MODULE_IDENTIFIER = MANIFEST_KIND


class SAMProxy(AbstractSAMBase):
    """Smarter API Manifest - Proxy."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    metadata: SAMProxyMetadata = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.METADATA.value}[obj]: Required, the {MANIFEST_KIND} metadata.",
    )
    spec: SAMProxySpec = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.SPEC.value}[obj]: Required, the {MANIFEST_KIND} specification.",
    )
    status: Optional[SAMProxyStatus] = Field(
        default=None,
        description=f"{class_identifier}.{SAMKeys.STATUS.value}[obj]: Optional, Read-only. Stateful status information about the {MANIFEST_KIND}.",
    )
