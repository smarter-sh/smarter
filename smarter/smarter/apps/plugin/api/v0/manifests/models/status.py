"""Smarter API V0 Manifest - Plugin.status"""

import os
from typing import ClassVar

from smarter.apps.api.v0.manifests.models import AbstractSAMStatusBase

from .const import OBJECT_IDENTIFIER


filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{OBJECT_IDENTIFIER}.{filename}"


class SAMPluginStatus(AbstractSAMStatusBase):
    """Smarter API V0 Plugin Manifest - Status class."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER
