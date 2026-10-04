"""
Celery tasks of the vectorstore app.

- :func:`load_vectorstore_document`: split, embed and load a document. Queued when a document
  is added.
- :func:`delete_vectorstore_document`: remove a document's chunks, then the document.
- :func:`snapshot_vectorstore`: take a snapshot, or backup, on request.
- :func:`reconcile_vectorstores`: Celery Beat, every few minutes. Bring deployed vectorstores to
  ready, e.g. create a self-hosted server's collection once it has started, and record their
  status and statistics.
- :func:`maintain_vectorstores`: Celery Beat, hourly. Take snapshots on each manifest's schedule,
  prune them to its retention, and queue documents whose task was lost again.
"""

from typing import Any, Optional

from smarter.common.conf import smarter_settings
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.workers.celery import app

from .models import (
    VectorstoreDocument,
    VectorstoreDocumentStatus,
    VectorstoreMeta,
    VectorstoreStatus,
)
from .service import VectorstoreService

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.TASK_LOGGING, SmarterWaffleSwitches.VECTORSTORE_LOGGING]
)
logger_prefix = logging.formatted_text(__name__)
QUEUE = smarter_settings.llmclient_tasks_celery_task_queue
# snapshots and reconciliation manage vector databases, which can take minutes, so they run
# in the infrastructure queue, and never block the operational tasks of QUEUE.
INFRASTRUCTURE_QUEUE = smarter_settings.infrastructure_tasks_celery_task_queue


@app.task(queue=QUEUE)
def load_vectorstore_document(document_id: int) -> Optional[int]:
    """
    Split, embed and load a document.

    :returns: the number of chunks, or None if the document does not exist or failed to load.
    """
    document = VectorstoreDocument.objects.select_related("vectorstore").filter(pk=document_id).first()
    if document is None:
        return None
    try:
        return VectorstoreService(document.vectorstore).load_document(document)
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.warning("%s.load_vectorstore_document() %s: %s", logger_prefix, document, e)
        return None


@app.task(queue=QUEUE)
def delete_vectorstore_document(document_id: int) -> bool:
    """Remove a document's chunks from its vectorstore, then the document."""
    document = VectorstoreDocument.objects.select_related("vectorstore").filter(pk=document_id).first()
    if document is None:
        return False
    VectorstoreService(document.vectorstore).delete_document(document)
    return True


@app.task(queue=INFRASTRUCTURE_QUEUE)
def snapshot_vectorstore(vectorstore_id: int) -> Optional[str]:
    """Take a snapshot, or backup, of a vectorstore.

    :returns: its name.
    """
    vectorstore = VectorstoreMeta.objects.filter(pk=vectorstore_id).first()
    if vectorstore is None:
        return None
    service = VectorstoreService(vectorstore)
    snapshot = service.snapshot(scheduled=False)
    service.prune_snapshots()
    return snapshot.name


@app.task(queue=INFRASTRUCTURE_QUEUE)
def reconcile_vectorstores() -> dict[str, str]:
    """Bring every deployed vectorstore to ready, and record its status.

    :returns: each one's status, by name.
    """
    vectorstores = VectorstoreMeta.objects.filter(
        status__in=[VectorstoreStatus.PROVISIONING, VectorstoreStatus.READY, VectorstoreStatus.FAILED],
        deployed_at__isnull=False,
    ).select_related("user_profile", "connection", "api_key_secret")
    return {str(vectorstore): VectorstoreService(vectorstore).reconcile() for vectorstore in vectorstores}


def _requeue(document_ids: list[int]) -> None:
    for document in VectorstoreDocument.objects.filter(pk__in=document_ids):
        if document.status == VectorstoreDocumentStatus.DELETING:
            delete_vectorstore_document.delay(document.pk)
        else:
            load_vectorstore_document.delay(document.pk)


@app.task(queue=INFRASTRUCTURE_QUEUE)
def maintain_vectorstores() -> dict[str, Any]:
    """The scheduled maintenance of every ready vectorstore.

    :returns: what was done, by name.
    """
    results: dict[str, Any] = {}
    vectorstores = VectorstoreMeta.objects.filter(status=VectorstoreStatus.READY, is_active=True).select_related(
        "user_profile", "connection", "api_key_secret"
    )
    for vectorstore in vectorstores:
        try:
            result = VectorstoreService(vectorstore).maintain()
            _requeue(result["retry"])
            results[str(vectorstore)] = result
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("%s.maintain_vectorstores() %s: %s", logger_prefix, vectorstore, e)
            results[str(vectorstore)] = {"error": str(e)}
    return results


__all__ = [
    "delete_vectorstore_document",
    "load_vectorstore_document",
    "maintain_vectorstores",
    "reconcile_vectorstores",
    "snapshot_vectorstore",
]
