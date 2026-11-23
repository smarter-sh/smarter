"""Smarter API Manifest - Vectorstore.status."""

import datetime
import os
from typing import ClassVar, List, Literal, Optional

from pydantic import BaseModel, Field

from smarter.lib.manifest.models import AbstractSAMStatusBase

from .const import MANIFEST_KIND

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"

VectorstoreConditionTypeValue = Literal["Credentials", "Volume", "Server", "Index"]
VectorstoreConditionStatusValue = Literal["True", "False", "Unknown"]


class SAMVectorstoreCondition(BaseModel):
    """
    One of the things that a Vectorstore's database needs before it is ready, and whether it has it.

    A deploy has several independent points of failure, e.g. a refused api key, a volume that isn't
    bound, or a server whose image can't be pulled. Each is a condition, as in Kubernetes: its
    ``status`` is ``True`` when it is met, ``False`` when it isn't, and ``Unknown`` before it is
    checked. A Pinecone or Qdrant Cloud Vectorstore has the conditions ``Credentials`` and ``Index``,
    and a self-hosted one also ``Volume`` and ``Server``.

    Read only.
    """

    class_identifier: ClassVar[str] = f"{MODULE_IDENTIFIER}.condition"

    type: VectorstoreConditionTypeValue = Field(
        description=f"{class_identifier}.type: Credentials, Volume, Server or Index."
    )
    status: VectorstoreConditionStatusValue = Field(
        description=f"{class_identifier}.status: True if it is met, False if it isn't, Unknown before it is checked."
    )
    reason: str = Field(default="", description=f"{class_identifier}.reason: one word, e.g. Bound or ImagePullBackOff.")
    message: str = Field(default="", description=f"{class_identifier}.message: what was found, for a person.")
    lastTransitionTime: Optional[datetime.datetime] = Field(
        default=None, description=f"{class_identifier}.lastTransitionTime: when its status last changed."
    )


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
    message: Optional[str] = Field(
        default=None,
        description=f"{class_identifier}.message: what is happening, e.g. what a deploy waits for, or why it failed.",
    )
    conditions: List[SAMVectorstoreCondition] = Field(
        default_factory=list,
        description=f"{class_identifier}.conditions: what its database needs to be ready, as of its last deploy or check.",
    )
    attempt: Optional[int] = Field(
        default=None, description=f"{class_identifier}.attempt: the number of checks that its last deploy has made."
    )
    maxAttempts: Optional[int] = Field(
        default=None, description=f"{class_identifier}.maxAttempts: the checks that a deploy makes before it fails."
    )
    nextRetryAt: Optional[datetime.datetime] = Field(
        default=None, description=f"{class_identifier}.nextRetryAt: when a deploy in progress checks again."
    )
    lastError: Optional[str] = Field(
        default=None,
        description=f"{class_identifier}.lastError: the last error of its last deploy, which may have been retried since.",
    )
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
    deployedAt: Optional[datetime.datetime] = Field(
        default=None, description=f"{class_identifier}.deployedAt: when it was deployed. Read only."
    )
    lastCheckedAt: Optional[datetime.datetime] = Field(
        default=None, description=f"{class_identifier}.lastCheckedAt: when its status was last checked. Read only."
    )
    lastSnapshotAt: Optional[datetime.datetime] = Field(
        default=None, description=f"{class_identifier}.lastSnapshotAt: when its last snapshot was taken. Read only."
    )
    lastMaintenanceAt: Optional[datetime.datetime] = Field(
        default=None, description=f"{class_identifier}.lastMaintenanceAt: when its maintenance last ran. Read only."
    )


__all__ = [
    "SAMVectorstoreCondition",
    "SAMVectorstoreStatus",
    "VectorstoreConditionStatusValue",
    "VectorstoreConditionTypeValue",
]
