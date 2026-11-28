"""
The Celery tasks of LLMHostComputes: their node groups, and the charges for their nodes.

- :func:`reconcile_llmhost_compute`: give a compute's node group the nodes that its LLMHosts need. It runs
  again every 30 seconds until the node group is settled, i.e. while a node starts or is removed, and checks
  the status of the compute's LLMHosts each time.
- :func:`reconcile_llmhost_computes`: reconcile every compute. Celery Beat runs it every few minutes, so that
  a node that is no longer needed is removed even if a reconcile failed.
- :func:`delete_llmhost_nodegroup`: delete a deleted compute's node group, by name.
- :func:`charge_llmhost_computes`: charge an hour of each compute's running nodes, so that budgets attached to
  a compute, its owner, or their account see the cost of the infrastructure. It is operational, so it runs in
  the queue of the other operational tasks, such as charges and budgets; the others call the cloud, and run in
  the infrastructure queue.
"""

from dataclasses import asdict
from typing import Optional

from django.db.models import Q

from smarter.apps.llmhost.const import (
    RECONCILE_INTERVAL_SECONDS,
    RECONCILE_MAX_ATTEMPTS,
    TASK_NAME_PREFIX,
)
from smarter.apps.llmhost.manifest.enum import SAMLLMHostStatusEnum
from smarter.apps.llmhost.models import LLMHostCompute
from smarter.apps.llmhost.services import LLMHostService, LLMHostServiceError
from smarter.apps.llmhost.services.compute import ComputeProvisioner
from smarter.apps.llmhost.services.exceptions import LLMHostComputeError
from smarter.apps.llmhost.services.nodegroups import get_nodegroups
from smarter.common.conf import smarter_settings
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.typing import SmarterDictType
from smarter.workers.celery import app

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.TASK_LOGGING, SmarterWaffleSwitches.LLM_HOST_LOGGING]
)


@app.task(
    name=f"{TASK_NAME_PREFIX}.reconcile_llmhost_compute",
    queue=smarter_settings.app_infrastructure_tasks_celery_task_queue,
)
def reconcile_llmhost_compute(compute_id: int, attempt: int = 1) -> Optional[SmarterDictType]:
    """
    Reconcile a compute's node group with its LLMHosts, and check their status.

    Runs again in
    30 seconds, until the node group is settled, or after RECONCILE_MAX_ATTEMPTS.

    :returns: The compute's state, or None if it does not exist.
    """
    compute = LLMHostCompute.objects.filter(pk=compute_id).first()
    if compute is None:
        logger.warning("LLMHostCompute %s does not exist.", compute_id)
        return None
    service = LLMHostService()
    state = None
    try:
        state = ComputeProvisioner(cluster=service.cluster).reconcile(compute)
    except LLMHostComputeError as e:
        logger.error("failed for %s: %s", compute, e)
    if service.cluster.ready:
        for llmhost in compute.llmhosts.filter(status__in=SAMLLMHostStatusEnum.deployed()):  # type: ignore[attr-defined]
            try:
                service.observe(llmhost, probe=False)
            except LLMHostServiceError as e:
                logger.error(
                    "status check of %s failed: %s",
                    llmhost,
                    e,
                )
    if (state is None or not state.settled) and attempt < RECONCILE_MAX_ATTEMPTS:
        reconcile_llmhost_compute.apply_async((compute_id, attempt + 1), countdown=RECONCILE_INTERVAL_SECONDS)
    return asdict(state) if state is not None else None


@app.task(
    name=f"{TASK_NAME_PREFIX}.reconcile_llmhost_computes",
    queue=smarter_settings.app_infrastructure_tasks_celery_task_queue,
)
def reconcile_llmhost_computes() -> dict[str, str]:
    """
    Reconcile every compute that has nodes, or deployed LLMHosts.

    :returns: Each compute's status message, by name.
    """
    computes = LLMHostCompute.objects.filter(
        Q(desired_nodes__gt=0) | Q(llmhosts__status__in=SAMLLMHostStatusEnum.deployed())
    ).distinct()
    provisioner = ComputeProvisioner()
    retval = {}
    for compute in computes:
        try:
            retval[compute.name] = provisioner.reconcile(compute).message
        except LLMHostComputeError as e:
            logger.error("failed for %s: %s", compute, e)
            retval[compute.name] = str(e)
    return retval


@app.task(
    name=f"{TASK_NAME_PREFIX}.delete_llmhost_nodegroup",
    queue=smarter_settings.app_infrastructure_tasks_celery_task_queue,
)
def delete_llmhost_nodegroup(nodegroup_name: str) -> bool:
    """
    Delete a deleted LLMHostCompute's node group, and its nodes.

    Queued by :func:`~smarter.apps.llmhost.tasks.queue.queue_nodegroup_deletion`, with the node group's name,
    because the compute is gone. The foreign key keeps a compute that LLMHosts use from being deleted, so no
    LLMHost runs on it.

    :param nodegroup_name: The node group's name, e.g. ``smarter-alpha-12-gpu-l4-1x``.
    :returns: True if the node group was deleted, or didn't exist.
    """
    try:
        get_nodegroups().delete(nodegroup_name)
    except LLMHostComputeError as e:
        logger.error("the node group %s was not deleted: %s", nodegroup_name, e)
        return False
    logger.info("deleted the node group %s", nodegroup_name)
    return True


@app.task(
    name=f"{TASK_NAME_PREFIX}.charge_llmhost_computes",
    queue=smarter_settings.app_llmclient_tasks_celery_task_queue,
)
def charge_llmhost_computes() -> dict[str, str]:
    """
    Charge an hour of each compute's ready nodes, at its price_per_hour, to the compute, its owner, and their account.

    Celery Beat runs it hourly, so each charge is the hour that is beginning, at the number of
    nodes that are ready now. A compute without a price is not charged.

    :returns: Each charged compute's cost, by name.
    """
    # pylint: disable=C0415
    from smarter.apps.account.models import Charge, ChargeTypes

    computes = LLMHostCompute.objects.filter(ready_nodes__gt=0, price_per_hour__isnull=False).select_related(
        "user_profile", "user_profile__account"
    )
    retval = {}
    for compute in computes:
        cost = compute.price_per_hour * compute.ready_nodes  # type: ignore[operator]
        for resource in (compute, compute.user_profile, compute.user_profile.account):
            try:
                Charge.objects.create(
                    resource_locator=resource.record_locator,
                    charge_type=ChargeTypes.COMPUTE.value,
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                    total_cost=cost,
                )
            # pylint: disable=broad-except
            except Exception as e:
                logger.error("failed to charge %s: %s", resource, e)
        retval[compute.name] = str(cost)
    return retval


__all__ = [
    "charge_llmhost_computes",
    "delete_llmhost_nodegroup",
    "reconcile_llmhost_compute",
    "reconcile_llmhost_computes",
]
