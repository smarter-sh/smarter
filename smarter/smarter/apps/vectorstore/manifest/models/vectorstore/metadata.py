"""Smarter API Manifest - Vectorstore.metadata"""

import os
from typing import ClassVar

from smarter.lib.manifest.models import AbstractSAMMetadataBase

from .const import MANIFEST_KIND

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMVectorstoreMetadata(AbstractSAMMetadataBase):
    """Smarter API Vectorstore Manifest - Metadata class."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER
