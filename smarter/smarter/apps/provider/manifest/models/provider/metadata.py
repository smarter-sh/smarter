"""Smarter API Manifest - User.metadata"""

import os
from typing import ClassVar

from pydantic import Field

# User
from smarter.apps.provider.manifest.models.provider.const import MANIFEST_KIND
from smarter.lib.manifest.models import AbstractSAMMetadataBase


filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMProviderMetadata(AbstractSAMMetadataBase):
    """Smarter API Provider Manifest - Metadata class."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER
