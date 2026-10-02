"""The Vectorstore model: a vector database, its embeddings, and its state."""

import re
from typing import Any, Optional

from django.db import models

from smarter.apps.account.models import (
    MetaDataWithOwnershipModel,
    MetaDataWithOwnershipModelManager,
    User,
)
from smarter.apps.connection.models import ApiConnection
from smarter.apps.provider.models import Provider
from smarter.apps.secret.models import Secret
from smarter.apps.vectorstore.enum import (
    SmarterVectorStoreBackends,
    VectorstoreHosting,
    VectorstoreMetric,
)
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib import logging
from smarter.lib.cache import cache_results
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.VECTORSTORE_LOGGING])

PINECONE_INDEX_NAME_MAX_LENGTH = 45
"""Pinecone index names are at most 45 lowercase alphanumeric characters and hyphens."""


class VectorstoreBackendKind(models.TextChoices):
    """The vector database products that Smarter supports."""

    QDRANT = SmarterVectorStoreBackends.QDRANT.value, "Qdrant"
    PINECONE = SmarterVectorStoreBackends.PINECONE.value, "Pinecone"


class VectorstoreHostingKind(models.TextChoices):
    """Who runs the vector database."""

    SELF_HOSTED = VectorstoreHosting.SELF_HOSTED.value, "Self-hosted on Kubernetes"
    MANAGED = VectorstoreHosting.MANAGED.value, "Managed service"


class VectorstoreMetricKind(models.TextChoices):
    """The distance metric of similarity search."""

    COSINE = VectorstoreMetric.COSINE.value, "Cosine"
    EUCLIDEAN = VectorstoreMetric.EUCLIDEAN.value, "Euclidean"
    DOTPRODUCT = VectorstoreMetric.DOTPRODUCT.value, "Dot product"


class VectorstoreStatus(models.TextChoices):
    """
    The lifecycle of a vector database.

    - pending: applied, but not deployed.
    - provisioning: deployed, waiting for the database to be created and to become reachable.
    - ready: serving.
    - stopped: undeployed. A self-hosted database's data is kept on its volume.
    - failed: see status_message.
    - deleting: its database is being destroyed.
    """

    PENDING = "pending", "Pending"
    PROVISIONING = "provisioning", "Provisioning"
    READY = "ready", "Ready"
    STOPPED = "stopped", "Stopped"
    FAILED = "failed", "Failed"
    DELETING = "deleting", "Deleting"


class VectorstoreMeta(MetaDataWithOwnershipModel):
    """
    A vector database, for retrieval-augmented generation (RAG).

    It is created by applying a Vectorstore manifest, whose spec is kept in :attr:`spec`.
    The fields that are queried or displayed are also columns. Its documents are
    :class:`~smarter.apps.vectorstore.models.VectorstoreDocument`, and its dumps
    :class:`~smarter.apps.vectorstore.models.VectorstoreSnapshot`.
    """

    # pylint: disable=C0115
    class Meta:
        verbose_name = "Vectorstore"
        verbose_name_plural = "Vectorstores"
        unique_together = ("user_profile", "name")

    objects: MetaDataWithOwnershipModelManager["VectorstoreMeta"] = MetaDataWithOwnershipModelManager()

    # --- the manifest ---------------------------------------------------------
    spec = models.JSONField(default=dict, blank=True, help_text="The manifest's spec, as it was applied.")
    backend = models.CharField(
        max_length=50, choices=VectorstoreBackendKind.choices, help_text="The vector database product."
    )
    hosting = models.CharField(
        max_length=20,
        choices=VectorstoreHostingKind.choices,
        default=VectorstoreHostingKind.MANAGED,
        help_text="self_hosted: Smarter runs it on Kubernetes. managed: a service such as Pinecone or Qdrant Cloud.",
    )
    connection = models.ForeignKey(
        ApiConnection,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vector_databases",
        help_text="The ApiConnection of a managed database: its URL, and its API key Secret.",
    )
    is_active = models.BooleanField(default=True, help_text="Whether the vector database may be used.")
    dimension = models.PositiveIntegerField(default=1536, help_text="The number of dimensions of its vectors.")
    metric = models.CharField(
        max_length=20, choices=VectorstoreMetricKind.choices, default=VectorstoreMetricKind.COSINE
    )
    deletion_protection = models.BooleanField(
        default=False, help_text="Refuse to destroy the database while it is enabled."
    )
    embeddings_provider = models.ForeignKey(
        Provider,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vector_databases",
        help_text="The Provider whose embeddings model turns text into vectors.",
    )
    embeddings_model = models.CharField(max_length=255, blank=True, default="", help_text="e.g. text-embedding-3-small")

    # --- state ------------------------------------------------------------------
    status = models.CharField(max_length=20, choices=VectorstoreStatus.choices, default=VectorstoreStatus.PENDING)
    status_message = models.TextField(blank=True, default="")
    index_name = models.CharField(
        max_length=255, blank=True, default="", help_text="The Pinecone index, or Qdrant collection, of the database."
    )
    endpoint_url = models.CharField(max_length=255, blank=True, default="", help_text="Where the database is reached.")
    api_key_secret = models.ForeignKey(
        Secret,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vectorstores",
        help_text="The API key of a self-hosted database, generated by Smarter.",
    )
    vector_count = models.BigIntegerField(default=0, help_text="The number of vectors, as of last_checked_at.")
    stats = models.JSONField(default=dict, blank=True, help_text="The database's own statistics.")
    deployed_at = models.DateTimeField(null=True, blank=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)
    last_snapshot_at = models.DateTimeField(null=True, blank=True)
    last_maintenance_at = models.DateTimeField(null=True, blank=True)

    @property
    def is_billable_resource(self) -> bool:
        return True

    @property
    def is_self_hosted(self) -> bool:
        return self.hosting == VectorstoreHostingKind.SELF_HOSTED

    @property
    def is_deployed(self) -> bool:
        return self.status in (VectorstoreStatus.PROVISIONING, VectorstoreStatus.READY)

    @property
    def maintenance(self) -> dict[str, Any]:
        """The manifest's spec.maintenance."""
        return (self.spec or {}).get("maintenance") or {}

    @property
    def kubernetes_name(self) -> str:
        """
        The name of a self-hosted database's Kubernetes resources, e.g. vectorstore-12.

        It is derived from the primary key, rather than the name, so that renaming a vectorstore
        does not lose its server.
        """
        return f"vectorstore-{self.pk}"

    def default_index_name(self) -> str:
        """
        A name for the database's index or collection that is unique on a shared service.

        A managed Pinecone project, or Qdrant Cloud cluster, may be shared by many accounts,
        so the name includes the account number.
        """
        account = re.sub(r"[^0-9]", "", self.user_profile.account.account_number)  # type: ignore[union-attr]
        name = re.sub(r"[^a-z0-9-]+", "-", str(self.name).lower()).strip("-")
        if self.backend == VectorstoreBackendKind.PINECONE:
            return f"{name[: PINECONE_INDEX_NAME_MAX_LENGTH - len(account) - 1]}-{account}".strip("-")
        if self.is_self_hosted:
            return name
        return f"{name}-{account}"

    @classmethod
    def get_cached_object(cls, *args, backend: Optional[str] = None, **kwargs) -> "VectorstoreMeta":
        """Retrieve a cached VectorstoreMeta, by name and backend, or by the parent class's arguments."""

        @cache_results(cls.cache_expiration)
        def _get_object_by_name_and_backend(name: str, backend: str) -> "VectorstoreMeta":
            return (
                cls.objects.prefetch_related("tags")
                .select_related("user_profile", "user_profile__account", "user_profile__user")
                .get(name=name, backend=backend)
            )

        invalidate = kwargs.get("invalidate", False)
        name = kwargs.get("name")
        if name is not None and backend is not None:
            if invalidate:
                _get_object_by_name_and_backend.invalidate(name=name, backend=backend)
            return _get_object_by_name_and_backend(name=name, backend=backend)
        return super().get_cached_object(*args, **kwargs)  # type: ignore

    @classmethod
    def get_cached_vectorstores_for_user(cls, user: User, invalidate: bool = False) -> list["VectorstoreMeta"]:
        """The vectorstores that the user may read."""
        if user is None:
            return []

        # pylint: disable=unused-argument
        @cache_results()
        def get_cached_vectorstores_for_user_id(
            user_id: int,
        ) -> list["VectorstoreMeta"]:
            return list(VectorstoreMeta.objects.with_read_permission_for(user))

        if invalidate:
            get_cached_vectorstores_for_user_id.invalidate(user_id=user.id)  # type: ignore
        logger.debug("%s for %s", formatted_text(f"{__name__}.get_cached_vectorstores_for_user()"), user)
        return get_cached_vectorstores_for_user_id(user_id=user.id)  # type: ignore

    def __str__(self):
        return f"{self.name} ({self.backend}, {self.hosting})"


__all__ = [
    "VectorstoreMeta",
    "VectorstoreBackendKind",
    "VectorstoreHostingKind",
    "VectorstoreMetricKind",
    "VectorstoreStatus",
]
