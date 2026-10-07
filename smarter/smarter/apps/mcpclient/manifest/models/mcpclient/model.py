"""Smarter API MCPClient Manifest."""

from typing import ClassVar, Optional

from pydantic import Field

from smarter.apps.mcpclient.manifest.models.mcpclient.const import MANIFEST_KIND
from smarter.lib.manifest.enum import SAMKeys
from smarter.lib.manifest.models import AbstractSAMBase

from .metadata import SAMMCPClientMetadata
from .spec import SAMMCPClientSpec
from .status import SAMMCPClientStatus

MODULE_IDENTIFIER = MANIFEST_KIND


class SAMMCPClient(AbstractSAMBase):
    """Smarter API Manifest - MCPClient."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    metadata: SAMMCPClientMetadata = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.METADATA.value}[obj]: Required, the {MANIFEST_KIND} metadata.",
    )
    spec: SAMMCPClientSpec = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.SPEC.value}[obj]: Required, the {MANIFEST_KIND} specification.",
    )
    status: Optional[SAMMCPClientStatus] = Field(
        default=None,
        description=f"{class_identifier}.{SAMKeys.STATUS.value}[obj]: Optional, Read-only. Stateful status information about the {MANIFEST_KIND}.",
    )
