"""Smarter API SmarterAuthToken - SmarterAuthToken.metadata"""

import os
from typing import ClassVar

from smarter.lib.drf.manifest.models.auth_token.const import MANIFEST_KIND
from smarter.lib.manifest.models import AbstractSAMMetadataBase


filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMSmarterAuthTokenMetadata(AbstractSAMMetadataBase):
    """Smarter API SmarterAuthToken Manifest - Metadata class."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER
