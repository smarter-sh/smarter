"""Smarter Connection Manifest"""

from typing import ClassVar

from pydantic import Field

from smarter.apps.connection.manifest.models.common.connection.model import (
    SAMConnectionCommon,
)
from smarter.lib.manifest.enum import SAMKeys

from .const import MANIFEST_KIND
from .spec import SAMApiConnectionSpec

MODULE_IDENTIFIER = MANIFEST_KIND


class SAMApiConnection(SAMConnectionCommon):
    """Smarter API Connection Manifest - ApiConnection Model"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    spec: SAMApiConnectionSpec = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.SPEC.value}[obj]: Required, the {MANIFEST_KIND} specification.",
    )
