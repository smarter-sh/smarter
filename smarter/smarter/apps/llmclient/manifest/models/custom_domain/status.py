"""Smarter API Manifest - CustomDomain.status."""

import os
from datetime import datetime
from typing import ClassVar, List, Optional

from pydantic import Field

from smarter.apps.llmclient.manifest.models.custom_domain.const import MANIFEST_KIND
from smarter.lib.manifest.models import AbstractSAMStatusBase

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMCustomDomainStatus(AbstractSAMStatusBase):
    """
    Smarter API CustomDomain Manifest - Status class.

    Read only. Besides ownership, it reports the domain's AWS Route53 hosted zone, whether
    the domain is verified, and its DNS records. The LLMClient that uses it is reported in
    ``dependencies``.
    """

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    accountNumber: str = Field(
        description=f"{class_identifier}.accountNumber: The account owner of this {MANIFEST_KIND}. Read only.",
    )
    username: str = Field(
        description=f"{class_identifier}.username: The Smarter user who created this {MANIFEST_KIND}. Read only.",
    )
    awsHostedZoneId: Optional[str] = Field(
        default=None,
        description=(
            f"{class_identifier}.awsHostedZoneId: The AWS Route53 hosted zone of this {MANIFEST_KIND}, "
            "once it is registered with smarter deploy. Read only."
        ),
    )
    verificationStatus: str = Field(
        default="Not Verified",
        description=(
            f"{class_identifier}.verificationStatus: Not Verified, Verifying, Verified or Failed. The domain is "
            "Verified when its NS records are delegated to its hosted zone, and its TLS certificate is issued. "
            "Read only."
        ),
    )
    verifiedAt: Optional[datetime] = Field(
        default=None,
        description=f"{class_identifier}.verifiedAt: When the domain was verified. Read only.",
    )
    verificationMessage: Optional[str] = Field(
        default=None,
        description=(
            f"{class_identifier}.verificationMessage: Why the domain is not verified yet, or why its "
            "verification failed. Read only."
        ),
    )
    dnsRecords: List[str] = Field(
        default_factory=list,
        description=f"{class_identifier}.dnsRecords: The DNS records of this {MANIFEST_KIND}. Read only.",
    )
