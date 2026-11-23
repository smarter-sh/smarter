"""
Celery tasks of the vectorstore app.

- :func:`deploy_vectorstore`: create a vectorstore's database, and check it until it is ready.
  Queued by ``deploy``. Each run checks once, and queues itself again, rather than waiting.
- :func:`load_vectorstore_document`: split, embed and load a document. Queued when a document
  is added.
- :func:`delete_vectorstore_document`: remove a document's chunks, then the document.
- :func:`snapshot_vectorstore`: take a snapshot, or backup, on request.
- :func:`reconcile_vectorstores`: Celery Beat, every few minutes. Check deployed vectorstores,
  record their status, conditions and statistics, and take over a deploy whose task was lost.
- :func:`maintain_vectorstores`: Celery Beat, hourly. Take snapshots on each manifest's schedule,
  prune them to its retention, and queue documents whose task was lost again.
"""

from typing import Optional

from smarter.common.conf import smarter_settings
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.typing import SmarterDictType
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
QUEUE = smarter_settings.app_llmclient_tasks_celery_task_queue
# snapshots and reconciliation manage vector databases, which can take minutes, so they run
# in the infrastructure queue, and never block the operational tasks of QUEUE.
INFRASTRUCTURE_QUEUE = smarter_settings.app_infrastructure_tasks_celery_task_queue


@app.task(queue=INFRASTRUCTURE_QUEUE)
def deploy_vectorstore(vectorstore_id: int, deployment_id: str) -> Optional[str]:
    """
    Make one check of a vectorstore's deploy, and queue the next one, until the deploy ends.

    The first check creates the database's infrastructure, e.g. a self-hosted server, and each
    check records the deploy's conditions, creates the index once the infrastructure is ready, and
    says when to check again: every few seconds while it waits, and later after each error in a
    row. A check never waits, so a deploy that takes many minutes never holds a worker. See
    :meth:`smarter.apps.vectorstore.service.VectorstoreService.deployment_step`.

    :param vectorstore_id: The vectorstore's id.
    :param deployment_id: The deploy's id. A deploy that another deploy replaced stops.
    :returns: The vectorstore's status after the check, or None if it does not exist.
    """
    vectorstore = (
        VectorstoreMeta.objects.select_related("user_profile", "connection", "api_key_secret")
        .filter(pk=vectorstore_id)
        .first()
    )
    if vectorstore is None:
        logger.warning("vectorstore %s does not exist.", vectorstore_id)
        return None
    service = VectorstoreService(vectorstore)
    countdown = service.deployment_step(deployment_id)
    if countdown is not None:
        deploy_vectorstore.apply_async(
            kwargs={"vectorstore_id": vectorstore_id, "deployment_id": deployment_id}, countdown=countdown
        )
    return service.vectorstore.status


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
        logger.warning("%s: %s", document, e)
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
def maintain_vectorstores() -> SmarterDictType:
    """The scheduled maintenance of every ready vectorstore.

    :returns: what was done, by name.
    """
    results: SmarterDictType = {}
    vectorstores = VectorstoreMeta.objects.filter(status=VectorstoreStatus.READY, is_active=True).select_related(
        "user_profile", "connection", "api_key_secret"
    )
    for vectorstore in vectorstores:
        try:
            result = VectorstoreService(vectorstore).maintain()
            _requeue(result["retry"])
            results[str(vectorstore)] = result
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("%s: %s", vectorstore, e)
            results[str(vectorstore)] = {"error": str(e)}
    return results


__all__ = [
    "delete_vectorstore_document",
    "deploy_vectorstore",
    "load_vectorstore_document",
    "maintain_vectorstores",
    "reconcile_vectorstores",
    "snapshot_vectorstore",
]
