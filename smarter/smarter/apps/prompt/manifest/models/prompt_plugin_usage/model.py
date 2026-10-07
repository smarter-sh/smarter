"""Smarter API PromptPluginUsage Manifest."""

from typing import ClassVar, Optional

from pydantic import Field

from smarter.apps.prompt.manifest.models.prompt_plugin_usage.const import MANIFEST_KIND
from smarter.lib.manifest.enum import SAMKeys
from smarter.lib.manifest.models import AbstractSAMBase

from .metadata import SAMPromptPluginUsageMetadata
from .spec import SAMPromptPluginUsageSpecConfig
from .status import SAMPromptPluginUsageStatus

MODULE_IDENTIFIER = MANIFEST_KIND


class SAMPromptPluginUsage(AbstractSAMBase):
    """Smarter API Manifest - PromptPluginUsage."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    metadata: SAMPromptPluginUsageMetadata = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.METADATA.value}[obj]: Required, the {MANIFEST_KIND} metadata.",
    )
    spec: SAMPromptPluginUsageSpecConfig = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.SPEC.value}[obj]: Required, the {MANIFEST_KIND} specification.",
    )
    status: Optional[SAMPromptPluginUsageStatus] = Field(
        default=None,
        description=f"{class_identifier}.{SAMKeys.STATUS.value}[obj]: Optional, Read-only. Stateful status information about the {MANIFEST_KIND}.",
    )
