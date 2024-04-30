"""Smarter API V0 Manifest - Plugin.status"""

from typing import ClassVar

from smarter.apps.api.v0.manifests.models import SAMStatusBase

from .const import OBJECT_IDENTIFIER


MODULE_IDENTIFIER = f"{OBJECT_IDENTIFIER}.{__file__}"


class SAMPluginStatus(SAMStatusBase):
    """Smarter API V0 Plugin Manifest - Status class."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER
