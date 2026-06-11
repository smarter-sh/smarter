"""Smarter API PromptPluginUsage - PromptPluginUsage.spec."""

import os
from typing import ClassVar

from smarter.apps.prompt.manifest.models.chat_plugin_usage.const import MANIFEST_KIND
from smarter.lib.manifest.models import AbstractSAMSpecBase

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMChatPluginUsageSpecConfig(AbstractSAMSpecBase):
    """Smarter API PromptPluginUsage Manifest PromptPluginUsage.spec.config."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".configuration"
