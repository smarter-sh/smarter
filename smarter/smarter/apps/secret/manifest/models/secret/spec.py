"""Smarter API Manifest - Secret.spec."""

import os
from datetime import datetime, timezone
from typing import ClassVar, Optional

from pydantic import Field, field_serializer, field_validator

from smarter.apps.secret.manifest.models.secret.const import MANIFEST_KIND
from smarter.common.utils import mask_string
from smarter.lib.manifest.models import AbstractSAMSpecBase

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMSecretSpecConfig(AbstractSAMSpecBase):
    """Smarter API Secret Manifest Secret.spec.config."""

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
        """
        Treat a naive ``expiration_date`` as UTC.

        :param v: The expiration date, or None.
        :returns: The date, with UTC as its time zone if it had none, or None.
        :raises ValueError: when it is not a datetime.
        """
        if v is None:
            return v
        if isinstance(v, datetime):
            if v.tzinfo is None:
                return v.replace(tzinfo=timezone.utc)
            return v
        raise ValueError("expiration_date must be a datetime object")

    @field_serializer("value")
    def mask_value(self, v: str) -> str:
        """
        Mask the secret value when the spec is serialized, so that it is never shown.

        :param v: The secret value.
        :returns: The masked value, or the value unchanged when it is empty.
        """
        if not v:
            return v
        return mask_string(v)


class SAMSecretSpec(AbstractSAMSpecBase):
    """Smarter API Secret Manifest Secret.spec."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    config: SAMSecretSpecConfig = Field(
        ...,
        description=(f"{class_identifier}.config[object]. The configuration for the {MANIFEST_KIND}."),
    )
