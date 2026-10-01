"""Smarter API Manifest - LLMHost.status."""

import datetime
import os
from decimal import Decimal
from typing import ClassVar, Optional

from pydantic import Field

from smarter.apps.llmhost.manifest.models.llmhost.const import MANIFEST_KIND
from smarter.lib.manifest.models import AbstractSAMStatusBase

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMLLMHostStatus(AbstractSAMStatusBase):
    """
    Smarter API LLMHost Manifest - Status class.

    Read only. Besides ownership, it reports the LLMHost's lifecycle state, where it can be
    reached, and its accumulated cost, as of its most recent status check.
    """

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    accountNumber: str = Field(
        description=f"{class_identifier}.account_number: The account owner of this {MANIFEST_KIND}. Read only.",
    )
    username: str = Field(
        description=f"{class_identifier}.username: The Smarter user who created this {MANIFEST_KIND}. Read only.",
    )
    hostStatus: Optional[str] = Field(
        default=None,
        description=f"{class_identifier}.hostStatus: the lifecycle state, e.g. pending, active or error. Read only.",
    )
    message: Optional[str] = Field(
        default=None,
        description=f"{class_identifier}.message: why the {MANIFEST_KIND} is in its state, e.g. a container error. Read only.",
    )
    replicas: Optional[int] = Field(default=None, description=f"{class_identifier}.replicas: desired. Read only.")
    readyReplicas: Optional[int] = Field(
        default=None, description=f"{class_identifier}.readyReplicas: ready. Read only."
    )
    healthy: Optional[bool] = Field(
        default=None, description=f"{class_identifier}.healthy: the result of the last health check. Read only."
    )
    endpoint: Optional[str] = Field(
        default=None,
        description=f"{class_identifier}.endpoint: the base URL inside the cluster, e.g. for LLMClients. Read only.",
    )
    publicUrl: Optional[str] = Field(
        default=None, description=f"{class_identifier}.publicUrl: the base URL of the Ingress, if any. Read only."
    )
    apiKeySecret: Optional[str] = Field(
        default=None,
        description=f"{class_identifier}.apiKeySecret: the Smarter Secret with the API key, if any. Read only.",
    )
    deployedAt: Optional[datetime.datetime] = Field(
        default=None, description=f"{class_identifier}.deployedAt: when it was last launched. Read only."
    )
    lastCheckedAt: Optional[datetime.datetime] = Field(
        default=None, description=f"{class_identifier}.lastCheckedAt: when its status was last checked. Read only."
    )
    uptimeHours: Optional[float] = Field(
        default=None, description=f"{class_identifier}.uptimeHours: hours since deployedAt. Read only."
    )
    estimatedCost: Optional[Decimal] = Field(
        default=None,
        description=f"{class_identifier}.estimatedCost: uptimeHours times replicas times each replica's share of its compute's node price. Read only.",
    )
