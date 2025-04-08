"""Smarter API Manifest - User.metadata"""

import os
from typing import ClassVar

from pydantic import Field

# User
from smarter.apps.account.manifest.models.user.const import MANIFEST_KIND
from smarter.lib.manifest.models import AbstractSAMMetadataBase


filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMUserMetadata(AbstractSAMMetadataBase):
    """Smarter API User Manifest - Metadata class."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    username: str = Field(
        ...,
        description=(f"{class_identifier}.username[str]. Required. The Django username of the user."),
    )
