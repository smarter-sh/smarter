"""Smarter API Manifest - Vectorsearch.metadata."""

import os
from typing import ClassVar

# Vectorsearch
from smarter.apps.vectorsearch.manifest.models.vectorsearch.const import MANIFEST_KIND
from smarter.lib.manifest.models import AbstractSAMMetadataBase

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMVectorsearchMetadata(AbstractSAMMetadataBase):
    """Smarter API Vectorsearch Manifest - Metadata class."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER
