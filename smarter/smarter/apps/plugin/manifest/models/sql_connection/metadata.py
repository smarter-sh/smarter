"""Smarter API Manifest - Plugin.metadata"""

import os
from typing import ClassVar, Optional

from pydantic import Field

# Plugin
from smarter.apps.plugin.manifest.models.sql_connection.const import MANIFEST_KIND
from smarter.lib.manifest.models import AbstractSAMMetadataBase


filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMPluginSqlMetadata(AbstractSAMMetadataBase):
    """Smarter API Plugin Manifest - Metadata class."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    description: Optional[str] = Field(
        None,
        description=f"{class_identifier}.description[str]: Required, a brief description of the {MANIFEST_KIND}.",
    )

    version: Optional[str] = Field(
        None,
        description=f"{class_identifier}.version[str]: Required, the version of the {MANIFEST_KIND}.",
    )
