"""Smarter API V0 Manifest - Plugin.status"""

import os
from typing import ClassVar

from smarter.lib.manifest.models import AbstractSAMStatusBase

from ..const import MANIFEST_KIND


filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMPluginStatus(AbstractSAMStatusBase):
    """Smarter API V0 Plugin Manifest - Status class."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER
