"""Smarter API Manifest - Vectorstore.status."""

import datetime
import os
from typing import ClassVar, Optional

from pydantic import Field

from smarter.lib.manifest.models import AbstractSAMStatusBase

from .const import MANIFEST_KIND

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMVectorstoreStatus(AbstractSAMStatusBase):
    """Smarter API Vectorstore Manifest - Status class.

    Read only.
    """

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    accountNumber: str = Field(description=f"{class_identifier}.accountNumber: the owner's account. Read only.")
    username: str = Field(description=f"{class_identifier}.username: the owner. Read only.")
    vectorstoreStatus: str = Field(
        description=f"{class_identifier}.vectorstoreStatus: pending, provisioning, ready, stopped, failed or deleting."
    )
    message: Optional[str] = Field(default=None, description=f"{class_identifier}.message: why, if it failed.")
    indexName: Optional[str] = Field(
        default=None, description=f"{class_identifier}.indexName: the Pinecone index, or Qdrant collection."
    )
    endpoint: Optional[str] = Field(default=None, description=f"{class_identifier}.endpoint: where it is reached.")
    apiKeySecret: Optional[str] = Field(
        default=None, description=f"{class_identifier}.apiKeySecret: the Secret with a self-hosted database's API key."
    )
    vectorCount: int = Field(default=0, description=f"{class_identifier}.vectorCount: as of lastCheckedAt.")
    documentCount: int = Field(default=0, description=f"{class_identifier}.documentCount: its documents.")
    snapshotCount: int = Field(default=0, description=f"{class_identifier}.snapshotCount: its snapshots, or backups.")
    deployedAt: Optional[datetime.datetime] = Field(default=None)
    lastCheckedAt: Optional[datetime.datetime] = Field(default=None)
    lastSnapshotAt: Optional[datetime.datetime] = Field(default=None)
    lastMaintenanceAt: Optional[datetime.datetime] = Field(default=None)


__all__ = ["SAMVectorstoreStatus"]
