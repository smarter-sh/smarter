"""Smarter API Plugin Manifest"""

from typing import ClassVar, Optional

from pydantic import Field

from smarter.apps.plugin.manifest.models.api_connection.const import MANIFEST_KIND
from smarter.lib.manifest.enum import SAMKeys
from smarter.lib.manifest.models import AbstractSAMBase

from .metadata import SAMApiConnectionMetadata
from .spec import SAMApiConnectionSpec
from .status import SAMApiConnectionStatus


MODULE_IDENTIFIER = MANIFEST_KIND


class SAMApiConnection(AbstractSAMBase):
    """Smarter API Manifest - PluginSql Connection Model"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    metadata: SAMApiConnectionMetadata = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.METADATA.value}[obj]: Required, the {MANIFEST_KIND} metadata.",
    )
    spec: SAMApiConnectionSpec = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.SPEC.value}[obj]: Required, the {MANIFEST_KIND} specification.",
    )
    status: Optional[SAMApiConnectionStatus] = Field(
        default=None,
        description=f"{class_identifier}.{SAMKeys.STATUS.value}[obj]: Optional, Read-only. Stateful status information about the {MANIFEST_KIND}.",
        exclude=True,
    )
