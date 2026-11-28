"""
The service layer of vectorstores: their lifecycle, their documents, search, and maintenance.

:class:`VectorstoreService` binds a :class:`~smarter.apps.vectorstore.models.VectorstoreMeta`
to its backend and embeddings model. The manifest broker, the REST API, the Celery tasks and
the management commands all go through it.

**Lifecycle**

- :meth:`~VectorstoreService.deploy`: check the api key, and queue the deploy task, which creates
  the database. A Pinecone index takes a minute or two to initialize, and a self-hosted Qdrant
  server needs a volume and a pod, so the task checks again every few seconds, with
  :meth:`~VectorstoreService.deployment_step`, records each condition, retries after errors, and
  fails the deploy after an error that retrying can't fix, or too many checks. See
  :mod:`smarter.apps.vectorstore.deployment`.
- :meth:`~VectorstoreService.reconcile`: Celery Beat runs it every few minutes. It checks deployed
  databases, creates a missing index or collection, records the status and statistics, and takes
  over a deploy whose task was lost.
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
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

from django.db import transaction
from django.utils import timezone
from langchain_core.embeddings import Embeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from smarter.apps.secret.models import Secret
from smarter.common.exceptions import SmarterException, SmarterValueError
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.typing import SmarterDictType

from .backends import (
    SEARCH_TYPES,
    SearchResult,
    SmarterVectorstoreBackend,
    VectorStoreBackendCredentialsError,
    VectorStoreBackendRejectedError,
    get_backend,
)
from .deployment import (
    CREDENTIALS,
    FALSE,
    INDEX,
    TRUE,
    UNKNOWN,
    VectorstoreDeploymentState,
)
from .embeddings import get_embeddings
from .enum import VectorstoreQueuedMessage
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
from .sources import DocumentSource

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.VECTORSTORE_LOGGING])

API_KEY_SECRET_NAME = "vectorstore_{name}_api_key"
API_KEY_BYTES = 32
STUCK_AFTER = timedelta(minutes=30)
"""A document that has been pending or loading this long lost its Celery task, and is retried."""


class VectorstoreServiceError(SmarterException):
    """A vectorstore operation is not possible, e.g. destroying a protected database."""


@dataclass(frozen=True)
class DocumentsAdded:
    """The result of :meth:`VectorstoreService.add_documents`."""

    added: list[VectorstoreDocument]
    duplicates: list[VectorstoreDocument]
    queued: bool


NOT_RETRYABLE = (VectorStoreBackendRejectedError, VectorstoreServiceError)
"""The errors that fail a deploy at once, because retrying wouldn't help, e.g. a refused api key."""


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
        self._deployment: Optional[VectorstoreDeploymentState] = None

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} vectorstore={self.vectorstore.name}>"

    @property
    def backend(self) -> SmarterVectorstoreBackend:
        """The vectorstore's backend, created when it is first used."""
        if self._backend is None:
            self._backend = get_backend(self.vectorstore)
        return self._backend

    @property
    def embeddings(self) -> Embeddings:
        """The vectorstore's embeddings model, created when it is first used."""
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
        """
        Record the vectorstore's status, and send vectorstore_status_changed if it changed.

        :param status: The new status.
        :param message: Why, or an empty string.
        """
        vectorstore = self.vectorstore
        previous = vectorstore.status
        vectorstore.status = status
        vectorstore.status_message = message
        vectorstore.save(update_fields=["status", "status_message", "updated_at"])
        if previous != status:
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
    @property
    def deployment(self) -> VectorstoreDeploymentState:
        """The progress of the vectorstore's last deploy, read when it is first used."""
        if self._deployment is None:
            self._deployment = VectorstoreDeploymentState.of(self.vectorstore)
        return self._deployment

    def save_deployment(self) -> None:
        """Save the progress of the vectorstore's deploy."""
        self.deployment.save_to(self.vectorstore)

    def start_deployment(self) -> VectorstoreDeploymentState:
        """
        Begin a deploy: check what can be checked at once, and record a new deploy, provisioning.

        It doesn't create anything: :meth:`deployment_step` does, in the deploy task. It checks that the
        vectorstore is active, and that its database accepts its api key, so that a refused key is
        an error now, rather than a deploy that fails minutes later. A database that can't be reached
        isn't an error yet: the deploy task tries again.

        :returns: The new deploy's state.
        :raises VectorstoreServiceError: If the vectorstore is inactive.
        :raises VectorStoreBackendRejectedError: If the database refuses its api key, which fails the deploy.
        """
        vectorstore = self.vectorstore
        if not vectorstore.is_active:
            raise VectorstoreServiceError(f"Vectorstore {vectorstore.name} is not active.")
        if not vectorstore.index_name:
            vectorstore.index_name = vectorstore.default_index_name()
        if vectorstore.is_self_hosted:
            self.ensure_api_key()
        state = VectorstoreDeploymentState.start()
        self._deployment = state
        try:
            message = self.backend.check_credentials()
        except NOT_RETRYABLE as e:
            self.record_error(e)
            self.fail_deployment(f"Deploy failed: {e}")
            raise
        except Exception as e:  # pylint: disable=broad-exception-caught
            # e.g. a timeout: the deploy task checks again.
            state.set_condition(CREDENTIALS, UNKNOWN, "Unreachable", str(e))
            state.lastError = str(e)
        else:
            state.set_condition(CREDENTIALS, TRUE, "Accepted", message)
        state.set_condition(INDEX, UNKNOWN, "Pending", "The index is created once the database is ready.")
        vectorstore.deployed_at = timezone.now()
        vectorstore.save(update_fields=["index_name", "deployed_at", "updated_at"])
        self.save_deployment()
        self.set_status(VectorstoreStatus.PROVISIONING, "Deploying.")
        return state

    def deploy(self) -> VectorstoreDeploymentState:
        """
        Deploy the vectorstore: begin a deploy, and queue the deploy task, which creates the database.

        It returns at once, provisioning. The task
        :func:`~smarter.apps.vectorstore.tasks.deploy_vectorstore` is queued once the current
        transaction commits, and checks the database until it is ready, or the deploy fails. Its
        progress is in :attr:`deployment`, which the manifest's status shows.

        :returns: The new deploy's state.
        :raises VectorstoreServiceError: If the vectorstore is inactive.
        :raises VectorStoreBackendRejectedError: If the database refuses its api key.
        """
        # pylint: disable=import-outside-toplevel
        from .tasks import deploy_vectorstore

        state = self.start_deployment()
        vectorstore_id = self.vectorstore.pk
        deployment_id = state.id
        transaction.on_commit(lambda: deploy_vectorstore.delay(vectorstore_id, deployment_id))
        return state

    def record_error(self, error: Exception) -> None:
        """
        Record an error of the vectorstore's deploy, and the condition that it shows, if any.

        :param error: The error.
        """
        state = self.deployment
        state.lastError = str(error)
        state.consecutiveErrors += 1
        if isinstance(error, VectorStoreBackendCredentialsError):
            state.set_condition(CREDENTIALS, FALSE, "Refused", str(error))
        self.save_deployment()

    def fail_deployment(self, message: str) -> None:
        """
        End the vectorstore's deploy, failed.

        :param message: Why, for a person.
        """
        state = self.deployment
        state.finishedAt = timezone.now()
        state.nextRetryAt = None
        self.save_deployment()
        self.set_status(VectorstoreStatus.FAILED, message)

    def finish_deployment(self) -> None:
        """End the vectorstore's deploy, if one is in progress, e.g. when it is undeployed."""
        state = self.deployment
        if not state.in_progress:
            return
        state.finishedAt = timezone.now()
        state.nextRetryAt = None
        self.save_deployment()

    def advance_deployment(self, provision: bool = False) -> str:
        """
        Bring the database one step closer to ready, and record its conditions.

        It creates the infrastructure, if ``provision``, observes it, creates the index or
        collection once the infrastructure is ready, and checks that the index is ready. Nothing in
        it waits: what isn't ready yet is recorded, and checked again by the next call.

        :param provision: Create the infrastructure that Smarter runs, e.g. a self-hosted server.
        :returns: The status: provisioning, or ready.
        :raises Exception: Whatever the backend raises, e.g. a database that can't be reached.
        """
        vectorstore = self.vectorstore
        state = self.deployment
        if provision:
            self.provision()
        infrastructure = self.backend.infrastructure_conditions()
        for condition in infrastructure:
            state.set_condition(condition.type, condition.status, condition.reason, condition.message)
        for condition in infrastructure:
            if condition.status != TRUE:
                self.save_deployment()
                self.set_status(VectorstoreStatus.PROVISIONING, condition.message)
                return vectorstore.status
        exists = self.backend.exists()
        credentials = state.condition(CREDENTIALS)
        if credentials is None or credentials.status != TRUE:
            state.set_condition(CREDENTIALS, TRUE, "Accepted", "The database accepted the api key.")
        if not exists:
            self.backend.create()
            logger.info("created %s of %s", vectorstore.index_name, vectorstore)
        ready, message = self.backend.index_ready()
        if not ready:
            state.set_condition(INDEX, FALSE, "Initializing", message)
            self.save_deployment()
            self.set_status(VectorstoreStatus.PROVISIONING, message)
            return vectorstore.status
        state.set_condition(INDEX, TRUE, "Ready", f"{vectorstore.index_name} is ready.")
        state.consecutiveErrors = 0
        self.save_deployment()
        self.refresh_stats()
        self.set_status(VectorstoreStatus.READY, "")
        return vectorstore.status

    def provision(self) -> None:
        """Create the database's infrastructure, without waiting for it, and record where it is reached."""
        vectorstore = self.vectorstore
        self.backend.provision()
        if vectorstore.is_self_hosted:
            vectorstore.endpoint_url = self.backend.kubernetes.endpoint  # type: ignore[attr-defined]
        elif vectorstore.connection:
            vectorstore.endpoint_url = vectorstore.connection.base_url or ""
        vectorstore.save(update_fields=["endpoint_url", "updated_at"])
        self.deployment.provisioned = True
        self.save_deployment()
        vectorstore_deployed.send(sender=self.__class__, vectorstore=vectorstore)

    def deployment_step(self, deployment_id: str) -> Optional[int]:
        """
        Make one check of a deploy, as the deploy task does, and say when to check again.

        A deploy that another deploy replaced, or that was undeployed, does nothing. An error that
        retrying can't fix, e.g. a refused api key, fails the deploy at once. Any other error is
        recorded, and checked again after a wait that doubles with each error in a row. The deploy
        fails after :data:`~smarter.apps.vectorstore.deployment.DEPLOY_MAX_ATTEMPTS` checks.

        :param deployment_id: The id of the deploy that the task runs.
        :returns: The seconds until the next check, or None if the deploy has ended.
        """
        vectorstore = self.vectorstore
        state = self.deployment
        if state.id != deployment_id or not state.in_progress:
            logger.info("%s: deploy %s was replaced, or has ended.", vectorstore, deployment_id)
            return None
        if vectorstore.status != VectorstoreStatus.PROVISIONING:
            logger.info("%s is %s: deploy %s has ended.", vectorstore, vectorstore.status, deployment_id)
            self.finish_deployment()
            return None
        state.attempt += 1
        state.nextRetryAt = None
        try:
            status = self.advance_deployment(provision=not state.provisioned)
        except NOT_RETRYABLE as e:
            self.record_error(e)
            self.fail_deployment(f"Deploy failed: {e}")
            return None
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning("%s: check %s of %s: %s", vectorstore, state.attempt, state.maxAttempts, e)
            self.record_error(e)
            return self.check_again(str(e))
        if status == VectorstoreStatus.READY:
            self.finish_deployment()
            self.queue_pending_documents()
            return None
        return self.check_again(vectorstore.status_message)

    def check_again(self, reason: str) -> Optional[int]:
        """
        Schedule the deploy's next check, or fail the deploy if it has made all of its checks.

        :param reason: What the deploy waits for, or its last error.
        :returns: The seconds until the next check, or None if the deploy failed.
        """
        state = self.deployment
        if state.attempt >= state.maxAttempts:
            self.fail_deployment(f"Deploy failed after {state.attempt} checks: {reason}")
            return None
        seconds = state.backoff()
        state.nextRetryAt = timezone.now() + timedelta(seconds=seconds)
        self.save_deployment()
        if state.consecutiveErrors:
            message = f"Retrying in {seconds}s, after check {state.attempt} of {state.maxAttempts}: {reason}"
            self.set_status(VectorstoreStatus.PROVISIONING, message)
        return seconds

    def reconcile(self) -> str:
        """
        Check a deployed database, record its status, conditions and statistics, and create a missing index.

        Celery Beat runs it every few minutes, as a safety net. It leaves a deploy in progress to the
        deploy task, unless the deploy lost its task, and then it takes the deploy over. An error
        marks the vectorstore failed, until a later check succeeds. It never raises.

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
        state = self.deployment
        if state.in_progress and not state.is_stalled():
            return vectorstore.status
        try:
            provision = state.in_progress and not state.provisioned
            status = self.advance_deployment(provision=provision)
            if status == VectorstoreStatus.READY and state.in_progress:
                self.finish_deployment()
                self.queue_pending_documents()
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning("%s: %s", vectorstore, e)
            self.record_error(e)
            self.set_status(VectorstoreStatus.FAILED, str(e))
        finally:
            vectorstore.last_checked_at = timezone.now()
            vectorstore.save(update_fields=["last_checked_at", "updated_at"])
        return vectorstore.status

    def refresh_stats(self) -> SmarterDictType:
        """
        Read the database's statistics, and save them, and the vector count, on the vectorstore.

        :returns: The statistics.
        """
        stats = self.backend.stats()
        self.vectorstore.stats = stats
        self.vectorstore.vector_count = int(stats.get("vector_count") or 0)
        self.vectorstore.save(update_fields=["stats", "vector_count", "updated_at"])
        return stats

    def queue_provision(self) -> None:
        """
        Queue :func:`~smarter.apps.vectorstore.tasks.provision_vectorstore`, which applies a self-hosted server's changed spec.

        The manifest broker's ``apply`` calls it when a deployed self-hosted vectorstore's spec changes, e.g. its
        cpu or memory. The web server doesn't write to the cluster (ADR-038, phase 3, issue #1080): the
        infrastructure worker does. The status is unchanged.
        """
        # pylint: disable=import-outside-toplevel
        from .tasks import provision_vectorstore

        vectorstore = self.vectorstore
        vectorstore.status_message = VectorstoreQueuedMessage.PROVISION.value
        vectorstore.save(update_fields=["status_message", "updated_at"])
        vectorstore_id = vectorstore.pk
        transaction.on_commit(lambda: provision_vectorstore.delay(vectorstore_id))

    def queue_undeploy(self) -> None:
        """
        End the deploy in progress, if any, and queue :func:`~smarter.apps.vectorstore.tasks.undeploy_vectorstore`.

        The manifest broker's ``undeploy`` and the api's undeploy view call it. The infrastructure worker stops
        serving (:meth:`undeploy`), e.g. deletes a self-hosted server, keeping its volume.
        """
        # pylint: disable=import-outside-toplevel
        from .tasks import undeploy_vectorstore

        self.finish_deployment()
        self.set_status(self.vectorstore.status, VectorstoreQueuedMessage.UNDEPLOY.value)
        vectorstore_id = self.vectorstore.pk
        transaction.on_commit(lambda: undeploy_vectorstore.delay(vectorstore_id))

    def queue_delete(self) -> bool:
        """
        Delete the vectorstore: at once if it was never deployed, else by queuing :func:`~smarter.apps.vectorstore.tasks.delete_vectorstore`.

        The manifest broker's ``delete`` and the console's delete call it. A deployed vectorstore is kept, deleting,
        with the message :attr:`VectorstoreQueuedMessage.DELETE`, until the infrastructure worker has destroyed its
        database (:meth:`delete`), so that a failure leaves it to delete again. One that was never deployed has no
        database, and is deleted now, with its api key Secret.

        :returns: True if it was deleted now, False if its deletion was queued.
        :raises VectorstoreServiceError: If deletionProtection is enabled.
        """
        # pylint: disable=import-outside-toplevel
        from .tasks import delete_vectorstore

        vectorstore = self.vectorstore
        if vectorstore.deletion_protection:
            raise VectorstoreServiceError(
                f"Vectorstore {vectorstore.name} has deletionProtection. Disable it, and apply, to destroy it."
            )
        if not vectorstore.deployed_at:
            self.delete()
            return True
        self.finish_deployment()
        self.set_status(VectorstoreStatus.DELETING, VectorstoreQueuedMessage.DELETE.value)
        vectorstore_id = vectorstore.pk
        transaction.on_commit(lambda: delete_vectorstore.delay(vectorstore_id))
        return False

    def delete(self) -> None:
        """
        Destroy the vectorstore's database, if it was deployed, then delete the vectorstore and its api key Secret.

        The work of :func:`~smarter.apps.vectorstore.tasks.delete_vectorstore`, and of :meth:`queue_delete` for a
        vectorstore that was never deployed.

        :raises VectorstoreServiceError: If deletionProtection is enabled.
        :raises Exception: Whatever the backend raises when it destroys the database, which :meth:`destroy`
            records as a failed status. The vectorstore is then kept.
        """
        vectorstore = self.vectorstore
        if vectorstore.deployed_at:
            self.destroy()
        secret = vectorstore.api_key_secret
        vectorstore.delete()
        if secret is not None:
            secret.delete()

    def undeploy(self) -> None:
        """Stop serving.

        A self-hosted server is deleted, but its volume and data are kept. The work of
        :func:`~smarter.apps.vectorstore.tasks.undeploy_vectorstore`, which :meth:`queue_undeploy` queues.
        """
        self.backend.stop()
        self.finish_deployment()
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
        self.finish_deployment()
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
        """
        Require that the vectorstore is ready and active.

        :raises VectorstoreServiceError: If it is not.
        """
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
        metadata: Optional[SmarterDictType] = None,
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
        """Return the text splitter of the spec's ``chunkSize`` and ``chunkOverlap``, or the defaults."""
        spec = self.vectorstore.spec or {}
        embeddings_spec = spec.get("embeddings") or {}
        return RecursiveCharacterTextSplitter(
            chunk_size=embeddings_spec.get("chunkSize") or DEFAULT_CHUNK_SIZE,
            chunk_overlap=embeddings_spec.get("chunkOverlap") or DEFAULT_CHUNK_OVERLAP,
        )

    def chunks(self, document: VectorstoreDocument) -> tuple[list[str], list[SmarterDictType]]:
        """A document's chunks, and their metadata: the document's, and where the chunk came from."""
        splitter = self.text_splitter()
        texts: list[str] = []
        metadatas: list[SmarterDictType] = []
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
            spec = self.vectorstore.spec or {}
            embeddings_spec = spec.get("embeddings") or {}
            batch_size = embeddings_spec.get("batchSize") or 64
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

    def add_documents(
        self, sources: Iterable[DocumentSource], metadata: Optional[SmarterDictType] = None
    ) -> DocumentsAdded:
        """
        Add documents, and queue the new ones to be loaded, if the vectorstore is ready.

        A document whose text the vectorstore already has is a duplicate, and is not added again.
        The documents of a vectorstore that isn't ready are loaded once its deploy is ready.

        :param sources: The documents, e.g. from :func:`smarter.apps.vectorstore.sources.request_sources`.
        :param metadata: Stored with every chunk of every document.
        :returns: The documents added, the duplicates, and whether the new ones were queued.
        :raises smarter.apps.vectorstore.extract.VectorstoreExtractionError: If a document's text can't be extracted.
        """
        added: list[VectorstoreDocument] = []
        duplicates: list[VectorstoreDocument] = []
        for source in sources:
            document, created = self.add_document(
                name=source.name,
                data=source.data,
                text=source.text,
                content_type=source.content_type,
                source=source.source,
                metadata=metadata,
            )
            if created:
                added.append(document)
            else:
                duplicates.append(document)
        queued = self.vectorstore.status == VectorstoreStatus.READY
        if queued:
            self.queue_loads(added)
        result = DocumentsAdded(added=added, duplicates=duplicates, queued=queued)
        return result

    @staticmethod
    def queue_loads(documents: Iterable[VectorstoreDocument]) -> int:
        """
        Queue the Celery task that loads each document.

        :param documents: The documents.
        :returns: The number queued.
        """
        # pylint: disable=import-outside-toplevel
        from .tasks import load_vectorstore_document

        count = 0
        for document in documents:
            load_vectorstore_document.delay(document.pk)
            count += 1
        return count

    def queue_pending_documents(self) -> int:
        """
        Queue the documents that wait to be loaded, e.g. those added before the vectorstore was deployed.

        :returns: The number queued.
        """
        pending = self.vectorstore.documents.filter(status=VectorstoreDocumentStatus.PENDING)  # type: ignore[attr-defined]
        count = self.queue_loads(pending)
        if count:
            logger.info("%s: queued %s pending documents.", self.vectorstore, count)
        return count

    def find_document(self, reference: str) -> VectorstoreDocument:
        """
        Find one of the vectorstore's documents, by its id, or its name.

        :param reference: The document's id, or its name, e.g. a file name or url.
        :returns: The document.
        :raises VectorstoreServiceError: If no document, or more than one, has that name.
        """
        documents = self.vectorstore.documents.all()  # type: ignore[attr-defined]
        if reference.isdigit():
            document = documents.filter(pk=int(reference)).first()
            if document is not None:
                return document
        named = list(documents.filter(name=reference)[:2])
        if not named:
            raise VectorstoreServiceError(f"Vectorstore {self.vectorstore.name} has no document {reference}.")
        if len(named) > 1:
            raise VectorstoreServiceError(
                f"Vectorstore {self.vectorstore.name} has several documents named {reference}. Name one by its id."
            )
        return named[0]

    def remove_document(self, document: VectorstoreDocument) -> VectorstoreDocument:
        """
        Mark a document deleting, and queue the Celery task that removes it and its chunks.

        :param document: The document.
        :returns: The document, deleting.
        """
        # pylint: disable=import-outside-toplevel
        from .tasks import delete_vectorstore_document

        document.status = VectorstoreDocumentStatus.DELETING
        document.save(update_fields=["status", "updated_at"])
        delete_vectorstore_document.delay(document.pk)
        return document

    def search(  # pylint: disable=too-many-positional-arguments,too-many-arguments
        self,
        query: str,
        k: int = 4,
        search_type: str = "similarity",
        score_threshold: Optional[float] = None,
        fetch_k: Optional[int] = None,
        lambda_mult: Optional[float] = None,
        metadata_filter: Optional[SmarterDictType] = None,
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
        if not retention:
            retention = self.vectorstore.maintenance.get("snapshotRetention")
        if not retention:
            retention = DEFAULT_SNAPSHOT_RETENTION
        snapshots = self.vectorstore.snapshots  # type: ignore[attr-defined]
        removed = 0
        for snapshot in snapshots.filter(status=VectorstoreSnapshotStatus.FAILED):
            snapshot.delete()
            removed += 1
        for snapshot in snapshots.exclude(status=VectorstoreSnapshotStatus.FAILED).order_by("-created_at")[retention:]:
            try:
                self.backend.delete_snapshot(snapshot.name)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning("%s: %s", snapshot, e)
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
        """
        Whether a scheduled snapshot is due: snapshots are enabled, and none was taken within the interval.

        :param now: The time, or None for now.
        :returns: True if one is due.
        """
        maintenance = self.vectorstore.maintenance
        if not maintenance.get("snapshots", True):
            return False
        last = self.vectorstore.last_snapshot_at
        hours = maintenance.get("snapshotIntervalHours") or DEFAULT_SNAPSHOT_INTERVAL_HOURS
        if last is None:
            return True
        if now is None:
            now = timezone.now()
        due = now - last >= timedelta(hours=hours)
        return due

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

    def maintain(self, now=None) -> SmarterDictType:
        """
        The scheduled maintenance of a ready database.

        Refresh its status and statistics, take a snapshot if one is due, prune old snapshots,
        and return the documents whose task was lost, so that the caller can queue them again.

        :returns: what was done.
        """
        now = now or timezone.now()
        result: SmarterDictType = {"status": self.reconcile(), "snapshot": None, "pruned": 0, "retry": []}
        if result["status"] != VectorstoreStatus.READY or not self.vectorstore.is_active:
            return result
        if self.snapshot_due(now):
            try:
                result["snapshot"] = self.snapshot(scheduled=True).name
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning("snapshot of %s failed: %s", self.vectorstore, e)
        result["pruned"] = self.prune_snapshots()
        result["retry"] = list(self.stuck_documents(now).values_list("pk", flat=True))
        with transaction.atomic():
            self.vectorstore.last_maintenance_at = now
            self.vectorstore.save(update_fields=["last_maintenance_at", "updated_at"])
        return result


__all__ = ["API_KEY_SECRET_NAME", "VectorstoreService", "VectorstoreServiceError"]
