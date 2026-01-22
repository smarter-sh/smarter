"""Smarter API Manifest - Secret.spec"""

import os
from datetime import datetime, timezone
from typing import ClassVar, Optional

from pydantic import Field, field_validator

from smarter.apps.account.manifest.models.secret.const import MANIFEST_KIND
from smarter.lib.manifest.models import AbstractSAMSpecBase

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMSecretSpecConfig(AbstractSAMSpecBase):
    """Smarter API Secret Manifest Secret.spec.config"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".configuration"

    value: str = Field(
        ...,
        description=(f"{class_identifier}.value[str]. Required. The unencrypted value of the {MANIFEST_KIND}."),
    )
    expiration_date: Optional[datetime] = Field(
        default=None,
        description=(f"{class_identifier}.expiration_date[str]. Optional. The expiration date of the {MANIFEST_KIND}."),
    )

    @field_validator("expiration_date")
    def ensure_utc(cls, v):
        if v is None:
            return v
        if isinstance(v, datetime):
            if v.tzinfo is None:
                return v.replace(tzinfo=timezone.utc)
            return v
        raise ValueError("expiration_date must be a datetime object")


class SAMSecretSpec(AbstractSAMSpecBase):
    """Smarter API Secret Manifest Secret.spec"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    config: SAMSecretSpecConfig = Field(
        ...,
        description=(f"{class_identifier}.config[object]. The configuration for the {MANIFEST_KIND}."),
    )
