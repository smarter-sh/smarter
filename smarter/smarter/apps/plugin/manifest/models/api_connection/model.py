"""Smarter API Plugin Manifest"""

from typing import ClassVar, Optional

from pydantic import Field

from smarter.apps.plugin.manifest.models.common.connection.model import (
    SAMConnectionCommon,
)
from smarter.lib.manifest.enum import SAMKeys

from .const import MANIFEST_KIND
from .spec import SAMApiConnectionSpec


MODULE_IDENTIFIER = MANIFEST_KIND


class SAMApiConnection(SAMConnectionCommon):
    """Smarter API Manifest - SqlPlugin Connection Model"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    spec: Optional[SAMApiConnectionSpec] = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.SPEC.value}[obj]: Required, the {MANIFEST_KIND} specification.",
    )
