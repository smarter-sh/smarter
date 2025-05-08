"""Smarter API Manifest - Plugin.status"""

import os
from typing import ClassVar

from smarter.apps.plugin.manifest.models.plugin_api.const import MANIFEST_KIND
from smarter.lib.manifest.models import AbstractSAMStatusBase


filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMApiConnectionStatus(AbstractSAMStatusBase):
    """Smarter API Plugin Manifest - Status class."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER
