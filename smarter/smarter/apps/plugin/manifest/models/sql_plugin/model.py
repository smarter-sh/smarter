"""Smarter API Plugin Manifest"""

from typing import ClassVar

from pydantic import Field

from smarter.apps.plugin.manifest.models.common.plugin.model import SAMPluginCommon
from smarter.apps.plugin.manifest.models.sql_plugin.const import MANIFEST_KIND
from smarter.lib.manifest.enum import SAMKeys

from .spec import SAMSqlPluginSpec


MODULE_IDENTIFIER = MANIFEST_KIND


class SAMSqlPlugin(SAMPluginCommon):
    """Smarter API Manifest - Sql Connection Model"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    spec: SAMSqlPluginSpec = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.SPEC.value}[obj]: Required, the {MANIFEST_KIND} specification.",
    )
