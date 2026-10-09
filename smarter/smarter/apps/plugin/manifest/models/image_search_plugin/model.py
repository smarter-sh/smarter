"""
Smarter API Manifest - ImageSearchPlugin.

.. note::

    **Experimental.** The ImageSearchPlugin was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental.
"""

from typing import ClassVar

from pydantic import Field

from smarter.apps.plugin.manifest.models.common.plugin.model import SAMPluginCommon
from smarter.lib.manifest.enum import SAMKeys

from .const import MANIFEST_KIND
from .spec import SAMImageSearchPluginSpec

MODULE_IDENTIFIER = MANIFEST_KIND


class SAMImageSearchPlugin(SAMPluginCommon):
    """Smarter API Manifest - ImageSearchPlugin Model."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    spec: SAMImageSearchPluginSpec = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.SPEC.value}[obj]: Required, the {MANIFEST_KIND} specification.",
    )
