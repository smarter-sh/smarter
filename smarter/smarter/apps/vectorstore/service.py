"""
The service layer of vectorstores: their lifecycle, their documents, search, and maintenance.

:class:`VectorstoreService` binds a :class:`~smarter.apps.vectorstore.models.VectorstoreMeta`
to its backend and embeddings model. The manifest broker, the REST API, the Celery tasks and
the management commands all go through it.

**Lifecycle**

- :meth:`~VectorstoreService.deploy`: create the database. A self-hosted Qdrant server takes a
  minute or two to start, so the collection is created by :meth:`~VectorstoreService.reconcile`
  once it is reachable.
- :meth:`~VectorstoreService.reconcile`: Celery Beat runs it every few minutes. It creates a
  missing index or collection, and records the status and statistics.
- :meth:`~VectorstoreService.undeploy`: stop serving. A self-hosted server's volume, and so its
  data, is kept, and a managed index is left as it is.
- :meth:`~VectorstoreService.destroy`: delete the database and its data, unless
  ``deletionProtection`` is enabled.

**Documents** are added with :meth:`~VectorstoreService.add_document`, which extracts and stores
their text, and loaded by :meth:`~VectorstoreService.load_document`, normally in a Celery task.

**Maintenance**: :meth:`~VectorstoreService.maintain`, run hourly by Celery Beat, takes snapshots
on the manifest's schedule, prunes them to its retention, and retries documents whose task was lost.
"""

import hashlib
import secrets
from datetime import timedelta
from typing import Any, Optional

from django.db import transaction
from django.utils import timezone
from langchain_core.embeddings import Embeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from smarter.apps.secret.models import Secret
from smarter.common.exceptions import SmarterException, SmarterValueError
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .backends import (
    SEARCH_TYPES,
    SearchResult,
    SmarterVectorstoreBackend,
    get_backend,
)
from .embeddings import get_embeddings
from .extract import extract_text
from .manifest.models.vectorstore.const import (
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_SNAPSHOT_INTERVAL_HOURS,
    DEFAULT_SNAPSHOT_RETENTION,
)
from .models import (
    VectorstoreDocument,
    VectorstoreDocumentSource,
    VectorstoreDocumentStatus,
    VectorstoreMeta,
    VectorstoreSnapshot,
    VectorstoreSnapshotStatus,
    VectorstoreStatus,
)
from .signals import (
    document_load_failed,
    document_loaded,
    vectorstore_deployed,
    vectorstore_destroyed,
    vectorstore_status_changed,
)

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.VECTORSTORE_LOGGING])
logger_prefix = logging.formatted_text(__name__)

API_KEY_SECRET_NAME = "vectorstore_{name}_api_key"
API_KEY_BYTES = 32
STUCK_AFTER = timedelta(minutes=30)
"""A document that has been pending or loading this long lost its Celery task, and is retried."""


class VectorstoreServiceError(SmarterException):
    """A vectorstore operation is not possible, e.g. destroying a protected database."""


class VectorstoreService:  # pylint: disable=too-many-public-methods
    """
    The operations of one vectorstore.

    :param vectorstore: The vectorstore.
    :param backend: Its backend, e.g. one with an in-memory Qdrant client in tests. By default,
        :func:`~smarter.apps.vectorstore.backends.get_backend`.
    :param embeddings: Its embeddings model, e.g. a deterministic fake in tests. By default,
        :func:`~smarter.apps.vectorstore.embeddings.get_embeddings`, created when first needed.
    """

    def __init__(
        self,
        vectorstore: VectorstoreMeta,
        backend: Optional[SmarterVectorstoreBackend] = None,
        embeddings: Optional[Embeddings] = None,
    ):
        self.vectorstore = vectorstore
        self._embeddings = embeddings
        self._backend = backend

    @property
    def backend(self) -> SmarterVectorstoreBackend:
        if self._backend is None:
            self._backend = get_backend(self.vectorstore)
        return self._backend

    @property
    def embeddings(self) -> Embeddings:
        if self._embeddings is None:
            self._embeddings = get_embeddings(self.vectorstore)
        return self._embeddings

    def _with_embeddings(self) -> SmarterVectorstoreBackend:
        backend = self.backend
        if backend._embeddings is None:  # pylint: disable=protected-access
            backend._embeddings = self.embeddings  # pylint: disable=protected-access
        return backend

    # -------------------------------------------------------------------------
    # state
    # -------------------------------------------------------------------------
    def set_status(self, status: str, message: str = "") -> None:
        """Record the vectorstore's status, and send vectorstore_status_changed if it changed."""
        vectorstore = self.vectorstore
        previous = vectorstore.status
        vectorstore.status = status
        vectorstore.status_message = message
        vectorstore.save(update_fields=["status", "status_message", "updated_at"])
        if previous != status:
            logger.info("%s %s: %s -> %s %s", logger_prefix, vectorstore, previous, status, message)
            vectorstore_status_changed.send(
                sender=self.__class__, vectorstore=vectorstore, previous=previous, status=status, message=message
            )

    def ensure_api_key(self) -> Secret:
        """The Secret with a self-hosted database's API key, created with a random key the first time."""
        vectorstore = self.vectorstore
        if vectorstore.api_key_secret:
            return vectorstore.api_key_secret
        name = API_KEY_SECRET_NAME.format(name=vectorstore.name)
        secret = Secret.objects.filter(user_profile=vectorstore.user_profile, name=name).first()
        if secret is None:
            secret = Secret(
                name=name,
                user_profile=vectorstore.user_profile,
                description=f"The API key of self-hosted Vectorstore {vectorstore.name}. Generated by Smarter.",
                encrypted_value=Secret.encrypt(secrets.token_urlsafe(API_KEY_BYTES)),
            )
            secret.save()
        vectorstore.api_key_secret = secret
        vectorstore.save(update_fields=["api_key_secret", "updated_at"])
        return secret

    # -------------------------------------------------------------------------
    # lifecycle
    # -------------------------------------------------------------------------
    def deploy(self) -> None:
        """
        Create the database.

        A self-hosted server is created now, and its collection once it is reachable.

        :raises VectorstoreServiceError: if the vectorstore is inactive.
        """
        vectorstore = self.vectorstore
        if not vectorstore.is_active:
            raise VectorstoreServiceError(f"Vectorstore {vectorstore.name} is not active.")
        if not vectorstore.index_name:
            vectorstore.index_name = vectorstore.default_index_name()
        if vectorstore.is_self_hosted:
            self.ensure_api_key()
        try:
            self.backend.provision()
        except Exception as e:
            self.set_status(VectorstoreStatus.FAILED, f"Deploy failed: {e}")
            raise
        if vectorstore.is_self_hosted:
            vectorstore.endpoint_url = self.backend.kubernetes.endpoint  # type: ignore[attr-defined]
        elif vectorstore.connection:
            vectorstore.endpoint_url = vectorstore.connection.base_url or ""
        vectorstore.deployed_at = timezone.now()
        vectorstore.save(update_fields=["index_name", "endpoint_url", "deployed_at", "updated_at"])
        self.set_status(VectorstoreStatus.PROVISIONING, "Deployed. Waiting for the database.")
        vectorstore_deployed.send(sender=self.__class__, vectorstore=vectorstore)
        self.reconcile()

    def reconcile(self) -> str:
        """
        Bring a deployed database to ready: create its index or collection once it is reachable.

        It records the status, and the database's statistics. It never raises.

        :returns: the status.
        """
        vectorstore = self.vectorstore
        if vectorstore.status not in (
            VectorstoreStatus.PROVISIONING,
            VectorstoreStatus.READY,
            VectorstoreStatus.FAILED,
        ):
            return vectorstore.status
        if vectorstore.status == VectorstoreStatus.FAILED and not vectorstore.deployed_at:
            return vectorstore.status
        try:
            ready, message = self.backend.infrastructure_ready()
            if not ready:
                self.set_status(VectorstoreStatus.PROVISIONING, message)
                return vectorstore.status
            if not self.backend.exists():
                self.backend.create()
                logger.info("%s created %s of %s", logger_prefix, vectorstore.index_name, vectorstore)
            self.refresh_stats()
            self.set_status(VectorstoreStatus.READY, "")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning("%s.reconcile() %s: %s", logger_prefix, vectorstore, e)
            self.set_status(VectorstoreStatus.FAILED, str(e))
        finally:
            vectorstore.last_checked_at = timezone.now()
            vectorstore.save(update_fields=["last_checked_at", "updated_at"])
        return vectorstore.status

    def refresh_stats(self) -> dict[str, Any]:
        stats = self.backend.stats()
        self.vectorstore.stats = stats
        self.vectorstore.vector_count = int(stats.get("vector_count") or 0)
        self.vectorstore.save(update_fields=["stats", "vector_count", "updated_at"])
        return stats

    def undeploy(self) -> None:
        """Stop serving.

        A self-hosted server is deleted, but its volume and data are kept.
        """
        self.backend.stop()
        self.set_status(VectorstoreStatus.STOPPED, "Undeployed. Its data is kept. Deploy it again to resume.")

    def destroy(self) -> None:
        """
        Delete the database and all of its data.

        :raises VectorstoreServiceError: if deletionProtection is enabled.
        """
        vectorstore = self.vectorstore
        if vectorstore.deletion_protection:
            raise VectorstoreServiceError(
                f"Vectorstore {vectorstore.name} has deletionProtection. Disable it, and apply, to destroy it."
            )
        self.set_status(VectorstoreStatus.DELETING, "Destroying the database.")
        try:
            self.backend.destroy()
        except Exception as e:
            self.set_status(VectorstoreStatus.FAILED, f"Destroy failed: {e}")
            raise
        vectorstore.vector_count = 0
        vectorstore.stats = {}
        vectorstore.save(update_fields=["vector_count", "stats", "updated_at"])
        vectorstore.documents.update(  # type: ignore[attr-defined]
            status=VectorstoreDocumentStatus.PENDING, chunk_count=0, loaded_at=None
        )
        vectorstore.snapshots.all().delete()  # type: ignore[attr-defined]
        self.set_status(VectorstoreStatus.PENDING, "Destroyed. Deploy it again to create an empty database.")
        vectorstore_destroyed.send(sender=self.__class__, vectorstore=vectorstore)

    def require_ready(self) -> None:
        if self.vectorstore.status != VectorstoreStatus.READY or not self.vectorstore.is_active:
            raise VectorstoreServiceError(
                f"Vectorstore {self.vectorstore.name} is {self.vectorstore.status}, not ready. Deploy it first."
            )

    # -------------------------------------------------------------------------
    # documents
    # -------------------------------------------------------------------------
    def add_document(  # pylint: disable=too-many-positional-arguments,too-many-arguments
        self,
        name: str,
        data: Optional[bytes] = None,
        text: Optional[str] = None,
        content_type: Optional[str] = None,
        source: str = VectorstoreDocumentSource.UPLOAD,
        metadata: Optional[dict[str, Any]] = None,
    ) -> tuple[VectorstoreDocument, bool]:
        """
        Extract and store a document's text.

        It is loaded by :meth:`load_document`.

        :param data: The file's bytes, e.g. a PDF. Or text.
        :returns: the document, and whether it is new. A document with the same text is not added again.
        :raises VectorstoreExtractionError: if its text cannot be extracted.
        """
        if text is None:
            if data is None:
                raise SmarterValueError("A document requires data or text.")
            text, content_type = extract_text(name, data, content_type)
            size = len(data)
        else:
            content_type = content_type or "text/plain"
            size = len(text.encode("utf-8"))
        sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
        existing = VectorstoreDocument.objects.filter(vectorstore=self.vectorstore, sha256=sha256).first()
        if existing:
            return existing, False
        document = VectorstoreDocument.objects.create(
            vectorstore=self.vectorstore,
            name=name[:255],
            source=source,
            content_type=content_type or "",
            content=text,
            sha256=sha256,
            size_bytes=size,
            metadata=metadata or {},
        )
        return document, True

    def text_splitter(self) -> RecursiveCharacterTextSplitter:
        embeddings_spec = (self.vectorstore.spec or {}).get("embeddings") or {}
        return RecursiveCharacterTextSplitter(
            chunk_size=embeddings_spec.get("chunkSize") or DEFAULT_CHUNK_SIZE,
            chunk_overlap=embeddings_spec.get("chunkOverlap") or DEFAULT_CHUNK_OVERLAP,
        )

    def chunks(self, document: VectorstoreDocument) -> tuple[list[str], list[dict[str, Any]]]:
        """A document's chunks, and their metadata: the document's, and where the chunk came from."""
        splitter = self.text_splitter()
        texts: list[str] = []
        metadatas: list[dict[str, Any]] = []
        pages = document.pages
        for page_number, page in enumerate(pages, start=1):
            for text in splitter.split_text(page):
                metadata = {
                    **(document.metadata or {}),
                    "document_id": document.pk,
                    "document": document.name,
                    "source": document.source,
                    "chunk": len(texts),
                }
                if len(pages) > 1:
                    metadata["page"] = page_number
                texts.append(text)
                metadatas.append(metadata)
        return texts, metadatas

    def load_document(self, document: VectorstoreDocument) -> int:
        """
        Split, embed and load a document's chunks, replacing any that it had.

        :returns: the number of chunks.
        """
        self.require_ready()
        document.status = VectorstoreDocumentStatus.LOADING
        document.status_message = ""
        document.save(update_fields=["status", "status_message", "updated_at"])
        try:
            texts, metadatas = self.chunks(document)
            if not texts:
                raise VectorstoreServiceError(f"{document.name} has no text to load.")
            backend = self._with_embeddings()
            batch_size = ((self.vectorstore.spec or {}).get("embeddings") or {}).get("batchSize") or 64
            ids = document.chunk_ids(len(texts))
            backend.upsert(ids=ids, texts=texts, metadatas=metadatas, batch_size=batch_size)
            if document.chunk_count > len(texts):
                # it had more chunks before, e.g. with a smaller chunkSize.
                backend.delete(document.chunk_ids(document.chunk_count)[len(texts) :])
        except Exception as e:
            document.status = VectorstoreDocumentStatus.FAILED
            document.status_message = str(e)
            document.save(update_fields=["status", "status_message", "updated_at"])
            document_load_failed.send(sender=self.__class__, document=document, error=str(e))
            raise
        document.status = VectorstoreDocumentStatus.LOADED
        document.chunk_count = len(texts)
        document.loaded_at = timezone.now()
        document.save(update_fields=["status", "chunk_count", "loaded_at", "updated_at"])
        document_loaded.send(sender=self.__class__, document=document)
        return len(texts)

    def delete_document(self, document: VectorstoreDocument) -> None:
        """Remove a document's chunks from the database, then the document."""
        if document.chunk_count and self.vectorstore.status == VectorstoreStatus.READY:
            self.backend.delete(document.chunk_ids())
        document.delete()

    def search(  # pylint: disable=too-many-positional-arguments,too-many-arguments
        self,
        query: str,
        k: int = 4,
        search_type: str = "similarity",
        score_threshold: Optional[float] = None,
        fetch_k: Optional[int] = None,
        lambda_mult: Optional[float] = None,
        metadata_filter: Optional[dict[str, Any]] = None,
    ) -> list[SearchResult]:
        """Find the chunks closest in meaning to a query.

        See :meth:`SmarterVectorstoreBackend.search`.
        """
        self.require_ready()
        if not query or not query.strip():
            raise SmarterValueError("A search requires a query.")
        if search_type not in SEARCH_TYPES:
            raise SmarterValueError(f"search_type must be one of {SEARCH_TYPES}.")
        if search_type == "similarity_score_threshold" and score_threshold is None:
            raise SmarterValueError("score_threshold is required when search_type is similarity_score_threshold.")
        return self._with_embeddings().search(
            query,
            k=k,
            search_type=search_type,
            score_threshold=score_threshold,
            fetch_k=fetch_k,
            lambda_mult=lambda_mult,
            metadata_filter=metadata_filter,
        )

    # -------------------------------------------------------------------------
    # dumps
    # -------------------------------------------------------------------------
    def snapshot(self, scheduled: bool = False) -> VectorstoreSnapshot:
        """Take a Qdrant snapshot, or a Pinecone backup."""
        self.require_ready()
        vectorstore = self.vectorstore
        name = f"{vectorstore.index_name}-{timezone.now():%Y%m%d-%H%M%S}"
        snapshot = VectorstoreSnapshot.objects.create(
            vectorstore=vectorstore, name=name, scheduled=scheduled, vector_count=vectorstore.vector_count
        )
        try:
            info = self.backend.create_snapshot(name)
        except Exception as e:
            snapshot.status = VectorstoreSnapshotStatus.FAILED
            snapshot.status_message = str(e)
            snapshot.save(update_fields=["status", "status_message", "updated_at"])
            raise
        snapshot.name = info.name
        snapshot.size_bytes = info.size_bytes
        snapshot.status = VectorstoreSnapshotStatus.READY if info.ready else VectorstoreSnapshotStatus.CREATING
        snapshot.save(update_fields=["name", "size_bytes", "status", "updated_at"])
        vectorstore.last_snapshot_at = timezone.now()
        vectorstore.save(update_fields=["last_snapshot_at", "updated_at"])
        return snapshot

    def prune_snapshots(self, retention: Optional[int] = None) -> int:
        """Delete the oldest snapshots beyond the retention.

        Failed snapshots are removed too.
        """
        retention = retention or self.vectorstore.maintenance.get("snapshotRetention") or DEFAULT_SNAPSHOT_RETENTION
        snapshots = self.vectorstore.snapshots  # type: ignore[attr-defined]
        removed = 0
        for snapshot in snapshots.filter(status=VectorstoreSnapshotStatus.FAILED):
            snapshot.delete()
            removed += 1
        for snapshot in snapshots.exclude(status=VectorstoreSnapshotStatus.FAILED).order_by("-created_at")[retention:]:
            try:
                self.backend.delete_snapshot(snapshot.name)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning("%s.prune_snapshots() %s: %s", logger_prefix, snapshot, e)
                continue
            snapshot.delete()
            removed += 1
        return removed

    def restore(self, snapshot: VectorstoreSnapshot) -> None:
        """
        Replace the database's data with a snapshot's.

        Documents are not changed: those loaded after the snapshot are no longer in the database.
        """
        self.require_ready()
        if snapshot.vectorstore_id != self.vectorstore.pk:  # type: ignore[attr-defined]
            raise SmarterValueError("The snapshot is not one of this vectorstore's.")
        self.backend.restore_snapshot(snapshot.name)
        self.refresh_stats()

    # -------------------------------------------------------------------------
    # maintenance
    # -------------------------------------------------------------------------
    def snapshot_due(self, now=None) -> bool:
        maintenance = self.vectorstore.maintenance
        if not maintenance.get("snapshots", True):
            return False
        last = self.vectorstore.last_snapshot_at
        hours = maintenance.get("snapshotIntervalHours") or DEFAULT_SNAPSHOT_INTERVAL_HOURS
        return last is None or (now or timezone.now()) - last >= timedelta(hours=hours)

    def stuck_documents(self, now=None):
        """Documents whose Celery task was lost: pending, loading or deleting for a while."""
        cutoff = (now or timezone.now()) - STUCK_AFTER
        return self.vectorstore.documents.filter(  # type: ignore[attr-defined]
            status__in=[
                VectorstoreDocumentStatus.PENDING,
                VectorstoreDocumentStatus.LOADING,
                VectorstoreDocumentStatus.DELETING,
            ],
            updated_at__lt=cutoff,
        )

    def maintain(self, now=None) -> dict[str, Any]:
        """
        The scheduled maintenance of a ready database.

        Refresh its status and statistics, take a snapshot if one is due, prune old snapshots,
        and return the documents whose task was lost, so that the caller can queue them again.

        :returns: what was done.
        """
        now = now or timezone.now()
        result: dict[str, Any] = {"status": self.reconcile(), "snapshot": None, "pruned": 0, "retry": []}
        if result["status"] != VectorstoreStatus.READY or not self.vectorstore.is_active:
            return result
        if self.snapshot_due(now):
            try:
                result["snapshot"] = self.snapshot(scheduled=True).name
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning("%s.maintain() snapshot of %s failed: %s", logger_prefix, self.vectorstore, e)
        result["pruned"] = self.prune_snapshots()
        result["retry"] = list(self.stuck_documents(now).values_list("pk", flat=True))
        with transaction.atomic():
            self.vectorstore.last_maintenance_at = now
            self.vectorstore.save(update_fields=["last_maintenance_at", "updated_at"])
        return result


__all__ = ["API_KEY_SECRET_NAME", "VectorstoreService", "VectorstoreServiceError"]
