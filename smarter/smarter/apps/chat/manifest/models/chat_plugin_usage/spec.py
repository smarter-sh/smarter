"""Smarter API ChatPluginUsage - ChatPluginUsage.spec"""

import os
from typing import ClassVar

from smarter.apps.plugin.manifest.models.plugin.const import MANIFEST_KIND
from smarter.lib.manifest.models import AbstractSAMSpecBase


filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMChatPluginUsageSpecConfig(AbstractSAMSpecBase):
    """Smarter API ChatPluginUsage Manifest ChatPluginUsage.spec.config"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".configuration"
