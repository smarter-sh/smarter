"""
Smarter API Manifest - Vectorstore.spec.

A Vectorstore is a vector database for retrieval-augmented generation (RAG): documents are
split into chunks, embedded with a Provider's embeddings model, and loaded into it, and
searched by meaning. It is either self-hosted, by Smarter on its Kubernetes cluster, or a
managed service reached through an ApiConnection.

.. code-block:: yaml

    spec:
      backend: qdrant            # qdrant or pinecone
      hosting: self_hosted       # self_hosted (qdrant only), or managed
      connection: null           # managed only: an ApiConnection with the service's URL and API key
      isActive: true
      index:
        dimension: 1536          # must be the embeddings model's
        metric: cosine           # cosine, euclidean or dotproduct
        deletionProtection: false
      embeddings:
        provider: openai         # a Provider with an OpenAI-compatible embeddings API
        model: text-embedding-3-small
        chunkSize: 1000          # characters per chunk
        chunkOverlap: 200
      selfHosted:                # self_hosted only
        storage: 10Gi
        cpu: 500m
        memory: 1Gi
      pinecone:                  # pinecone only
        cloud: aws
        region: us-east-1
      maintenance:
        snapshots: true          # Qdrant snapshots, or Pinecone backups, taken by Celery Beat
        snapshotIntervalHours: 24
        snapshotRetention: 7
"""

import os
import re
from typing import ClassVar, Literal, Optional

from pydantic import Field, field_validator, model_validator

from smarter.apps.vectorstore.enum import (
    SmarterVectorStoreBackends,
    VectorstoreHosting,
    VectorstoreMetric,
)
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.models import AbstractSAMSpecBase, SmarterBasePydanticModel

from ..const import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_CPU,
    DEFAULT_MEMORY,
    DEFAULT_QDRANT_IMAGE,
    DEFAULT_SNAPSHOT_INTERVAL_HOURS,
    DEFAULT_SNAPSHOT_RETENTION,
    DEFAULT_STORAGE,
    MANIFEST_KIND,
    MAX_DIMENSION,
)

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"

QUANTITY = re.compile(r"^[0-9]+(\.[0-9]+)?(m|k|M|G|T|Ki|Mi|Gi|Ti)?$")
"""A Kubernetes resource quantity, e.g. 500m, 1Gi or 10Gi."""
IMAGE = re.compile(r"^[a-z0-9][a-z0-9._/:@-]*$")
INDEX_NAME = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")


class SAMVectorstoreIndex(SmarterBasePydanticModel):
    """Vectorstore.spec.index: the index (Pinecone), or collection (Qdrant), of the database."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".index"

    name: Optional[str] = Field(
        default=None,
        max_length=45,
        description=(
            f"{class_identifier}.name: the index or collection's name, in lowercase letters, digits and hyphens. "
            "Defaults to the manifest's name, with the account number for a managed service."
        ),
    )
    dimension: int = Field(
        ..., ge=1, le=MAX_DIMENSION, description=f"{class_identifier}.dimension: of the embeddings model's vectors."
    )
    metric: Literal["cosine", "euclidean", "dotproduct"] = Field(
        default=VectorstoreMetric.COSINE.value, description=f"{class_identifier}.metric: the distance metric."
    )
    deletionProtection: bool = Field(
        default=False, description=f"{class_identifier}.deletionProtection: refuse to destroy the database."
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not INDEX_NAME.match(v):
            raise SAMValidationError(f"index.name: '{v}' must be lowercase letters, digits and hyphens.")
        return v


class SAMVectorstoreEmbeddings(SmarterBasePydanticModel):
    """Vectorstore.spec.embeddings: how documents and queries are turned into vectors."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".embeddings"

    provider: str = Field(
        ...,
        min_length=1,
        description=f"{class_identifier}.provider: a Provider with an OpenAI-compatible embeddings API, e.g. openai.",
    )
    model: str = Field(
        ..., min_length=1, description=f"{class_identifier}.model: the embeddings model, e.g. text-embedding-3-small."
    )
    dimensions: Optional[int] = Field(
        default=None,
        ge=1,
        le=MAX_DIMENSION,
        description=(
            f"{class_identifier}.dimensions: ask the model for vectors of this size, if it supports it, e.g. "
            "text-embedding-3. It must equal index.dimension."
        ),
    )
    chunkSize: int = Field(
        default=DEFAULT_CHUNK_SIZE, ge=100, le=8000, description=f"{class_identifier}.chunkSize: characters per chunk."
    )
    chunkOverlap: int = Field(
        default=DEFAULT_CHUNK_OVERLAP,
        ge=0,
        le=2000,
        description=f"{class_identifier}.chunkOverlap: characters shared by consecutive chunks.",
    )
    batchSize: int = Field(
        default=DEFAULT_BATCH_SIZE,
        ge=1,
        le=1000,
        description=f"{class_identifier}.batchSize: chunks per embeddings request and upsert.",
    )

    @model_validator(mode="after")
    def validate_overlap(self) -> "SAMVectorstoreEmbeddings":
        if self.chunkOverlap >= self.chunkSize:
            raise SAMValidationError("embeddings.chunkOverlap: must be smaller than chunkSize.")
        return self


class SAMVectorstoreSelfHosted(SmarterBasePydanticModel):
    """Vectorstore.spec.selfHosted: the Qdrant server that Smarter runs on Kubernetes."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".selfHosted"

    image: str = Field(default=DEFAULT_QDRANT_IMAGE, description=f"{class_identifier}.image: the Qdrant image.")
    storage: str = Field(
        default=DEFAULT_STORAGE, description=f"{class_identifier}.storage: the size of its volume, e.g. 10Gi."
    )
    storageClass: Optional[str] = Field(
        default=None, description=f"{class_identifier}.storageClass: of its volume. Defaults to the cluster's."
    )
    cpu: str = Field(default=DEFAULT_CPU, description=f"{class_identifier}.cpu: requested, e.g. 500m.")
    memory: str = Field(default=DEFAULT_MEMORY, description=f"{class_identifier}.memory: requested, e.g. 1Gi.")

    @field_validator("storage", "cpu", "memory")
    @classmethod
    def validate_quantity(cls, v: str) -> str:
        if not QUANTITY.match(v):
            raise SAMValidationError(f"selfHosted: '{v}' is not a Kubernetes quantity, e.g. 500m, 1Gi or 10Gi.")
        return v

    @field_validator("image")
    @classmethod
    def validate_image(cls, v: str) -> str:
        if not IMAGE.match(v):
            raise SAMValidationError(f"selfHosted.image: '{v}' is not a container image reference.")
        return v


class SAMVectorstorePinecone(SmarterBasePydanticModel):
    """Vectorstore.spec.pinecone: where Pinecone runs a serverless index."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".pinecone"

    cloud: Literal["aws", "gcp", "azure"] = Field(default="aws", description=f"{class_identifier}.cloud")
    region: str = Field(default="us-east-1", min_length=1, description=f"{class_identifier}.region")


class SAMVectorstoreMaintenance(SmarterBasePydanticModel):
    """Vectorstore.spec.maintenance: what Celery Beat does, besides checking its status."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".maintenance"

    snapshots: bool = Field(
        default=True, description=f"{class_identifier}.snapshots: take Qdrant snapshots, or Pinecone backups."
    )
    snapshotIntervalHours: int = Field(
        default=DEFAULT_SNAPSHOT_INTERVAL_HOURS,
        ge=1,
        le=24 * 30,
        description=f"{class_identifier}.snapshotIntervalHours: how often.",
    )
    snapshotRetention: int = Field(
        default=DEFAULT_SNAPSHOT_RETENTION,
        ge=1,
        le=100,
        description=f"{class_identifier}.snapshotRetention: how many are kept. Older ones are deleted.",
    )


class SAMVectorstoreSpec(AbstractSAMSpecBase):
    """Smarter API Vectorstore Manifest Vectorstore.spec."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    backend: Literal["qdrant", "pinecone"] = Field(..., description=f"{class_identifier}.backend: qdrant or pinecone.")
    hosting: Literal["self_hosted", "managed"] = Field(
        default=VectorstoreHosting.MANAGED.value,
        description=(
            f"{class_identifier}.hosting: self_hosted, run by Smarter on Kubernetes (qdrant only), or managed, "
            "a service reached through the ApiConnection in connection."
        ),
    )
    connection: Optional[str] = Field(
        default=None,
        description=(
            f"{class_identifier}.connection: managed only. The name of an ApiConnection with the service's URL and "
            "API key Secret, e.g. https://api.pinecone.io, or a Qdrant Cloud cluster's URL."
        ),
    )
    isActive: bool = Field(default=True, description=f"{class_identifier}.isActive: whether it may be used.")
    index: SAMVectorstoreIndex = Field(..., description=f"{class_identifier}.index")
    embeddings: SAMVectorstoreEmbeddings = Field(..., description=f"{class_identifier}.embeddings")
    selfHosted: Optional[SAMVectorstoreSelfHosted] = Field(
        default=None, description=f"{class_identifier}.selfHosted: self_hosted only."
    )
    pinecone: Optional[SAMVectorstorePinecone] = Field(
        default=None, description=f"{class_identifier}.pinecone: pinecone only."
    )
    maintenance: SAMVectorstoreMaintenance = Field(
        default_factory=SAMVectorstoreMaintenance, description=f"{class_identifier}.maintenance"
    )

    @model_validator(mode="after")
    def validate_hosting(self) -> "SAMVectorstoreSpec":
        """Validate the combination of backend, hosting, connection, selfHosted and pinecone."""
        self_hosted = self.hosting == VectorstoreHosting.SELF_HOSTED.value
        if self_hosted and self.backend != SmarterVectorStoreBackends.QDRANT.value:
            raise SAMValidationError(f"hosting: {self.backend} cannot be self_hosted. Use managed.")
        if self_hosted and self.connection:
            raise SAMValidationError("connection: only a managed database has one. Smarter runs a self_hosted one.")
        if not self_hosted and not self.connection:
            raise SAMValidationError("connection: a managed database requires an ApiConnection.")
        if self.selfHosted is not None and not self_hosted:
            raise SAMValidationError("selfHosted: applies only when hosting is self_hosted.")
        if self.pinecone is not None and self.backend != SmarterVectorStoreBackends.PINECONE.value:
            raise SAMValidationError("pinecone: applies only when backend is pinecone.")
        if self.embeddings.dimensions is not None and self.embeddings.dimensions != self.index.dimension:
            raise SAMValidationError(
                f"embeddings.dimensions: {self.embeddings.dimensions} must equal index.dimension, {self.index.dimension}."
            )
        return self


__all__ = [
    "SAMVectorstoreEmbeddings",
    "SAMVectorstoreIndex",
    "SAMVectorstoreMaintenance",
    "SAMVectorstorePinecone",
    "SAMVectorstoreSelfHosted",
    "SAMVectorstoreSpec",
]
