"""
Smarter API Plugin Manifest.

.. note::

    **Experimental.** The SkillPlugin was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from typing import ClassVar

from pydantic import Field

from smarter.apps.plugin.manifest.models.common.plugin.model import SAMPluginCommon
from smarter.apps.plugin.manifest.models.skill_plugin.const import MANIFEST_KIND
from smarter.lib.manifest.enum import SAMKeys

from .spec import SAMSkillPluginSpec

MODULE_IDENTIFIER = MANIFEST_KIND


class SAMSkillPlugin(SAMPluginCommon):
    """Smarter API Manifest - Skill Connection Model."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    spec: SAMSkillPluginSpec = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.SPEC.value}[obj]: Required, the {MANIFEST_KIND} specification.",
    )
