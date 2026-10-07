"""Smarter API Manifest - LLMHostCompute.status."""

import datetime
import os
from typing import ClassVar, Optional

from pydantic import Field

from smarter.apps.llmhost.manifest.models.llmhost_compute.const import MANIFEST_KIND
from smarter.lib.manifest.models import AbstractSAMStatusBase

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMLLMHostComputeStatus(AbstractSAMStatusBase):
    """
    Smarter API LLMHostCompute Manifest - Status class.

    Read only. Besides ownership, it reports the node group, as of its most recent reconcile.
    """

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    accountNumber: str = Field(
        description=f"{class_identifier}.account_number: The account owner of this {MANIFEST_KIND}. Read only.",
    )
    username: str = Field(
        description=f"{class_identifier}.username: The Smarter user who created this {MANIFEST_KIND}. Read only.",
    )
    nodeGroupName: Optional[str] = Field(
        default=None, description=f"{class_identifier}.nodeGroupName: the cloud's name of the node group. Read only."
    )
    nodeGroupStatus: Optional[str] = Field(
        default=None,
        description=f"{class_identifier}.nodeGroupStatus: e.g. absent, CREATING or ACTIVE. Read only.",
    )
    desiredNodes: Optional[int] = Field(
        default=None, description=f"{class_identifier}.desiredNodes: the node group's desired size. Read only."
    )
    readyNodes: Optional[int] = Field(
        default=None, description=f"{class_identifier}.readyNodes: the nodes that have joined the cluster. Read only."
    )
    llmhosts: Optional[int] = Field(
        default=None, description=f"{class_identifier}.llmhosts: the LLMHosts that run on it. Read only."
    )
    message: Optional[str] = Field(
        default=None, description=f"{class_identifier}.message: the result of the last reconcile. Read only."
    )
    lastReconciledAt: Optional[datetime.datetime] = Field(
        default=None, description=f"{class_identifier}.lastReconciledAt: when it was last reconciled. Read only."
    )
