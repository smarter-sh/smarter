"""Smarter API Manifest - Proxy.status."""

import os
from typing import ClassVar, Optional

from pydantic import Field

from smarter.apps.proxy.manifest.models.proxy.const import MANIFEST_KIND
from smarter.lib.manifest.models import AbstractSAMStatusBase

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMProxyStatus(AbstractSAMStatusBase):
    """
    Smarter API Proxy Manifest - Status class.

    Read only. Besides ownership, it reports where the Proxy is, and where it forwards to.
    """

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    accountNumber: str = Field(
        description=f"{class_identifier}.accountNumber: The account owner of this {MANIFEST_KIND}. Read only.",
    )
    username: str = Field(
        description=f"{class_identifier}.username: The Smarter user who created this {MANIFEST_KIND}. Read only.",
    )
    url: Optional[str] = Field(
        default=None,
        description=(
            f"{class_identifier}.url: The URL of the {MANIFEST_KIND}'s passthrough endpoint, to use as the base "
            "URL of the provider's SDK. Read only."
        ),
    )
    upstreamUrl: Optional[str] = Field(
        default=None,
        description=(
            f"{class_identifier}.upstreamUrl: The base URL of the provider's API, to which requests are "
            "forwarded: spec.baseUrl, else the Provider's. Read only."
        ),
    )
    apiKeySecret: Optional[str] = Field(
        default=None,
        description=(
            f"{class_identifier}.apiKeySecret: The name of the Secret whose API key is added to requests: "
            "spec.apiKey, else the Provider's. None if there is none. Read only."
        ),
    )
