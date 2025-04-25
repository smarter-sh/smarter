"""Smarter API Manifest - Secret.metadata"""

import os
from typing import ClassVar

from pydantic import Field

# Secret Manifest
from smarter.apps.account.manifest.models.secret.const import MANIFEST_KIND
from smarter.lib.manifest.models import AbstractSAMMetadataBase


filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMSecretMetadata(AbstractSAMMetadataBase):
    """Smarter API Secret Manifest - Metadata class."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    name: str = Field(
        ...,
        description=(
            f"{class_identifier}.name[str]. Required. The name of the secret. camelCase, no spaces, no special characters."
        ),
    )
