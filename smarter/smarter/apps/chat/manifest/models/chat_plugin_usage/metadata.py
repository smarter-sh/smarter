"""Smarter API ChatPluginUsage - ChatPluginUsage.metadata"""

import os
from typing import ClassVar

from smarter.apps.plugin.manifest.models.plugin.const import MANIFEST_KIND
from smarter.lib.manifest.models import AbstractSAMMetadataBase


filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMChatPluginUsageMetadata(AbstractSAMMetadataBase):
    """Smarter API ChatPluginUsage Manifest - Metadata class."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER
