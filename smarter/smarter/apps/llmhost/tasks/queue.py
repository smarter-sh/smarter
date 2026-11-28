"""
How the web server changes LLMHosts and their computes: it checks, then queues a task.

The manifest brokers, the api, the admin and the receivers call these functions, never the service's launch,
destroy or delete, nor the compute's provisioner. Each checks what can be checked at once, so that an error is
an error now, records what was queued as the status message (:class:`~smarter.apps.llmhost.enum.SAMLLMHostQueuedMessage`),
and queues a task once the current transaction commits. Only the infrastructure worker writes to the cluster
and the cloud, so the app needs no more than a read-only Kubernetes Role (ADR-038, phase 3, issue #1080).
"""

from typing import Optional

from django.db import transaction

from smarter.apps.llmhost.manifest.enum import SAMLLMHostQueuedMessage
from smarter.apps.llmhost.models import LLMHost, LLMHostCompute
from smarter.apps.llmhost.services import LLMHostService
from smarter.apps.llmhost.services.exceptions import LLMHostClusterError
from smarter.apps.llmhost.services.observability import LLMHostObservation

from .compute import delete_llmhost_nodegroup, reconcile_llmhost_compute
from .llmhost import delete_llmhost, destroy_llmhost, launch_llmhost


def queue_launch(llmhost: LLMHost, service: Optional[LLMHostService] = None) -> LLMHostObservation:
    """
    Check that the LLMHost can be launched, then queue :func:`~smarter.apps.llmhost.tasks.llmhost.launch_llmhost`.

    The manifest broker's ``deploy`` and the api's deploy view call it. They only read the cluster: the
    infrastructure worker, which holds the Kubernetes write Role and the IAM role, makes every change.

    :param llmhost: The LLMHost.
    :param service: The LLMHost service. A new one by default.
    :returns: What is known of the LLMHost now, with the message :attr:`SAMLLMHostQueuedMessage.LAUNCH`.
    :raises LLMHostServiceError: if :meth:`~smarter.apps.llmhost.services.LLMHostService.check_launch` refuses.
    """
    service = service or LLMHostService()
    service.check_launch(llmhost)
    observation = service.queued(llmhost, SAMLLMHostQueuedMessage.LAUNCH.value)
    llmhost_id = llmhost.pk
    transaction.on_commit(lambda: launch_llmhost.delay(llmhost_id))
    return observation


def queue_destroy(llmhost: LLMHost, purge: bool = False, service: Optional[LLMHostService] = None) -> None:
    """
    Queue :func:`~smarter.apps.llmhost.tasks.llmhost.destroy_llmhost`, which destroys the LLMHost's Kubernetes resources.

    The manifest broker's ``undeploy`` and the api's undeploy view call it.

    :param llmhost: The LLMHost.
    :param purge: Also delete its model volume.
    :param service: The LLMHost service. A new one by default.
    :raises LLMHostClusterError: if the cluster is unavailable, as the task would find it.
    """
    service = service or LLMHostService()
    if not service.cluster.ready:
        raise LLMHostClusterError("The Kubernetes cluster is not available.")
    service.queued(llmhost, SAMLLMHostQueuedMessage.UNDEPLOY.value)
    llmhost_id = llmhost.pk
    transaction.on_commit(lambda: destroy_llmhost.delay(llmhost_id, purge=purge))


def queue_delete(llmhost: LLMHost, service: Optional[LLMHostService] = None) -> None:
    """
    Queue :func:`~smarter.apps.llmhost.tasks.llmhost.delete_llmhost`, which destroys the LLMHost's resources, then deletes it.

    The LLMHost stays, with the message :attr:`SAMLLMHostQueuedMessage.DELETE`, until the task has destroyed what
    it deployed, so that a failure leaves it to delete again rather than resources that nothing tracks. The
    manifest broker's ``delete`` and the api's delete view call it.

    :param llmhost: The LLMHost.
    :param service: The LLMHost service. A new one by default.
    :raises LLMHostClusterError: if the LLMHost is deployed and the cluster is unavailable, as
        :meth:`~smarter.apps.llmhost.services.LLMHostService.delete` would.
    """
    service = service or LLMHostService()
    if llmhost.is_deployed and not service.cluster.ready:
        raise LLMHostClusterError(
            f"LLMHost {llmhost.name} is deployed, and the Kubernetes cluster is not available to destroy it."
        )
    service.queued(llmhost, SAMLLMHostQueuedMessage.DELETE.value)
    llmhost_id = llmhost.pk
    transaction.on_commit(lambda: delete_llmhost.delay(llmhost_id))


def queue_reconcile(compute: LLMHostCompute) -> None:
    """
    Queue :func:`~smarter.apps.llmhost.tasks.compute.reconcile_llmhost_compute`, which gives the node group the nodes it needs.

    The manifest broker's ``deploy`` and the admin's reconcile action call it.

    :param compute: The LLMHostCompute.
    """
    compute.status_message = SAMLLMHostQueuedMessage.RECONCILE.value
    compute.save(update_fields=["status_message", "updated_at"])
    compute_id = compute.pk
    transaction.on_commit(lambda: reconcile_llmhost_compute.delay(compute_id))


def queue_nodegroup_deletion(compute: LLMHostCompute) -> None:
    """
    Queue :func:`~smarter.apps.llmhost.tasks.compute.delete_llmhost_nodegroup`, which deletes the compute's node group.

    The ``pre_delete`` receiver of LLMHostCompute calls it, however the compute is deleted: the manifest
    broker, the admin, or the deletion of its owner. The task is given the node group's name, which is all
    that the cloud needs, because the compute no longer exists when it runs.

    :param compute: The LLMHostCompute, about to be deleted.
    """
    nodegroup_name = compute.nodegroup_name
    transaction.on_commit(lambda: delete_llmhost_nodegroup.delay(nodegroup_name))


__all__ = [
    "queue_delete",
    "queue_destroy",
    "queue_launch",
    "queue_nodegroup_deletion",
    "queue_reconcile",
]
