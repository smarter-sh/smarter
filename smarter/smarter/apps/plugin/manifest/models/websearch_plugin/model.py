"""
Smarter API Manifest - WebsearchPlugin.

.. note::

    **Experimental.** The WebsearchPlugin was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from typing import ClassVar

from pydantic import Field

from smarter.apps.plugin.manifest.models.common.plugin.model import SAMPluginCommon
from smarter.lib.manifest.enum import SAMKeys

from .const import MANIFEST_KIND
from .spec import SAMWebsearchPluginSpec

MODULE_IDENTIFIER = MANIFEST_KIND


class SAMWebsearchPlugin(SAMPluginCommon):
    """Smarter API Manifest - WebsearchPlugin Model."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    spec: SAMWebsearchPluginSpec = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.SPEC.value}[obj]: Required, the {MANIFEST_KIND} specification.",
    )
