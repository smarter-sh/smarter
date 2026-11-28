"""
The Celery tasks of LLMHosts: launch, destroy, delete, and status checks.

- :func:`launch_llmhost`: launch an LLMHost, and create the DNS record of its Ingress.
- :func:`destroy_llmhost`: destroy an LLMHost's Kubernetes resources, and its DNS record.
- :func:`delete_llmhost`: destroy them, including the model volume, then delete the LLMHost.
- :func:`refresh_llmhost_status`: check the status of one, or every deployed, LLMHost. Celery Beat runs it
  every few minutes, so that status, events and cost stay current.

They manage Kubernetes resources, which can take minutes, so they run in the infrastructure queue, and never
block operational tasks. The tasks are thin: :class:`~smarter.apps.llmhost.services.LLMHostService` does the
work. A failure is recorded on the LLMHost (:func:`record_task_failure`), since whoever queued the change has
already been answered.
"""

from typing import Optional

from smarter.apps.llmhost.const import RECONCILE_INTERVAL_SECONDS, TASK_NAME_PREFIX
from smarter.apps.llmhost.manifest.enum import (
    SAMLLMHostEventType,
    SAMLLMHostStatusEnum,
)
from smarter.apps.llmhost.models import LLMHost
from smarter.apps.llmhost.services import LLMHostService, LLMHostServiceError
from smarter.common.conf import smarter_settings
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.workers.celery import app

from .compute import reconcile_llmhost_compute
from .dns import create_dns_record, destroy_dns_record

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.TASK_LOGGING, SmarterWaffleSwitches.LLM_HOST_LOGGING]
)


def record_task_failure(llmhost: LLMHost, action: str, error: Exception) -> None:
    """
    Record that a queued change to an LLMHost failed, as its status message and an error event.

    The task's caller has already returned, so this is where the owner sees why: describe, and the console.
    The service records the cluster's and the cloud's errors itself, with the LLMHost's status; this records
    the others, e.g. a Secret deleted after the change was queued, without changing the status.

    :param llmhost: The LLMHost.
    :param action: What failed, e.g. ``Launch``.
    :param error: Why.
    """
    message = f"{action} failed: {error}"
    logger.error("%s of %s", message, llmhost)
    llmhost.status_message = message
    llmhost.save(update_fields=["status_message", "updated_at"])
    llmhost.record_event(SAMLLMHostEventType.ERROR.value, message)


@app.task(name=f"{TASK_NAME_PREFIX}.launch_llmhost", queue=smarter_settings.app_infrastructure_tasks_celery_task_queue)
def launch_llmhost(llmhost_id: int) -> Optional[str]:
    """
    Launch an LLMHost, and create the DNS record of its Ingress.

    A failure is recorded on the LLMHost (:func:`record_task_failure`), not raised.

    :returns: The LLMHost's status, or None if it does not exist.
    """
    llmhost = LLMHost.objects.filter(pk=llmhost_id).first()
    if llmhost is None:
        logger.warning("LLMHost %s does not exist.", llmhost_id)
        return None
    try:
        observation = LLMHostService().launch(llmhost)
    except LLMHostServiceError as e:
        record_task_failure(llmhost, "Launch", e)
        return llmhost.status
    create_dns_record(llmhost)
    if llmhost.compute_id:  # type: ignore[attr-defined]
        reconcile_llmhost_compute.apply_async((llmhost.compute_id,), countdown=RECONCILE_INTERVAL_SECONDS)  # type: ignore[attr-defined]
    return observation.status


@app.task(name=f"{TASK_NAME_PREFIX}.destroy_llmhost", queue=smarter_settings.app_infrastructure_tasks_celery_task_queue)
def destroy_llmhost(llmhost_id: int, purge: bool = False) -> Optional[str]:
    """
    Destroy an LLMHost's Kubernetes resources, and the DNS record of its Ingress.

    A failure is recorded on the LLMHost (:func:`record_task_failure`), not raised.

    :returns: The LLMHost's status, or None if it does not exist.
    """
    llmhost = LLMHost.objects.filter(pk=llmhost_id).first()
    if llmhost is None:
        logger.warning("LLMHost %s does not exist.", llmhost_id)
        return None
    try:
        LLMHostService().destroy(llmhost, purge=purge)
    except LLMHostServiceError as e:
        record_task_failure(llmhost, "Undeploy", e)
        return llmhost.status
    destroy_dns_record(llmhost)
    if llmhost.compute_id:  # type: ignore[attr-defined]
        # a node that was still starting when the LLMHost was destroyed is removed once it joins.
        reconcile_llmhost_compute.apply_async((llmhost.compute_id,), countdown=RECONCILE_INTERVAL_SECONDS)  # type: ignore[attr-defined]
    return llmhost.status


@app.task(name=f"{TASK_NAME_PREFIX}.delete_llmhost", queue=smarter_settings.app_infrastructure_tasks_celery_task_queue)
def delete_llmhost(llmhost_id: int) -> bool:
    """
    Destroy an LLMHost's Kubernetes resources, including its model volume, and its DNS record, then delete it.

    The work of :meth:`~smarter.apps.llmhost.services.LLMHostService.delete`, which also deletes the API key
    Secret that Smarter generated. A failure is recorded on the LLMHost, which is kept, so that it can be
    deleted again.

    :param llmhost_id: The LLMHost's id.
    :returns: True if the LLMHost was deleted.
    """
    llmhost = LLMHost.objects.filter(pk=llmhost_id).first()
    if llmhost is None:
        logger.warning("LLMHost %s does not exist.", llmhost_id)
        return False
    compute_id = llmhost.compute_id  # type: ignore[attr-defined]
    destroy_dns_record(llmhost)
    try:
        LLMHostService().delete(llmhost)
    except LLMHostServiceError as e:
        record_task_failure(llmhost, "Delete", e)
        return False
    logger.info("deleted LLMHost %s", llmhost_id)
    if compute_id:
        reconcile_llmhost_compute.apply_async((compute_id,), countdown=RECONCILE_INTERVAL_SECONDS)
    return True


@app.task(
    name=f"{TASK_NAME_PREFIX}.refresh_llmhost_status",
    queue=smarter_settings.app_infrastructure_tasks_celery_task_queue,
)
def refresh_llmhost_status(llmhost_id: Optional[int] = None) -> dict[str, str]:
    """
    Check the status of an LLMHost, or of every deployed LLMHost.

    :returns: The status of each LLMHost checked, by name.
    """
    if llmhost_id is not None:
        llmhosts = LLMHost.objects.filter(pk=llmhost_id)
    else:
        llmhosts = LLMHost.objects.filter(status__in=SAMLLMHostStatusEnum.deployed())
    service = LLMHostService()
    if not service.cluster.ready:
        logger.warning("the Kubernetes cluster is not available.")
        return {}
    retval = {}
    for llmhost in llmhosts.select_related("user_profile", "user_profile__account"):
        try:
            retval[llmhost.name] = service.observe(llmhost).status
        except LLMHostServiceError as e:
            logger.error("failed for %s: %s", llmhost, e)
    return retval


__all__ = [
    "delete_llmhost",
    "destroy_llmhost",
    "launch_llmhost",
    "record_task_failure",
    "refresh_llmhost_status",
]
