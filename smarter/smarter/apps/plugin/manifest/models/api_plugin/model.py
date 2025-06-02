"""Smarter API Plugin Manifest"""

from typing import ClassVar

from pydantic import Field

from smarter.apps.plugin.manifest.models.api_plugin.const import MANIFEST_KIND
from smarter.apps.plugin.manifest.models.common.plugin.model import SAMPluginCommon
from smarter.lib.manifest.enum import SAMKeys

from .spec import SAMApiPluginSpec


MODULE_IDENTIFIER = MANIFEST_KIND


class SAMApiPlugin(SAMPluginCommon):
    """Smarter API Manifest - ApiPlugin Model"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    spec: SAMApiPluginSpec = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.SPEC.value}[obj]: Required, the {MANIFEST_KIND} specification.",
    )
