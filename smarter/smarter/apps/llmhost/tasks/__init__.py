"""
Celery tasks for the llmhost app.

- :func:`launch_llmhost`: launch an LLMHost, and create the DNS record of its Ingress.
- :func:`destroy_llmhost`: destroy an LLMHost's Kubernetes resources, and its DNS record.
- :func:`refresh_llmhost_status`: check the status of one, or every deployed, LLMHost.
  Celery Beat runs it every few minutes, so that status, events and cost stay current.
- :func:`reconcile_llmhost_compute`: give a compute's node group the nodes that its LLMHosts
  need. It runs again every 30 seconds until the node group is settled, i.e. while a node
  starts or is removed, and checks the status of the compute's LLMHosts each time.
- :func:`charge_llmhost_computes`: charge an hour of each compute's running nodes, so that budgets
  attached to a compute, its owner, or their account see the cost of the infrastructure.
- :func:`reconcile_llmhost_computes`: reconcile every compute. Celery Beat runs it every few
  minutes, so that a node that is no longer needed is removed even if a reconcile failed.

The tasks are thin: :class:`~smarter.apps.llmhost.services.LLMHostService` does the work.

Every task except :func:`charge_llmhost_computes` manages Kubernetes resources, which can take
minutes, so they run in the infrastructure queue, and never block operational tasks. The charge
is operational: it runs in the queue of the other operational tasks, such as charges and budgets.
"""

from dataclasses import asdict
from typing import Any, Optional

from django.db.models import Q

from smarter.apps.llmhost.const import (
    RECONCILE_INTERVAL_SECONDS,
    RECONCILE_MAX_ATTEMPTS,
)
from smarter.apps.llmhost.manifest.enum import SAMLLMHostStatusEnum
from smarter.apps.llmhost.models import LLMHost, LLMHostCompute
from smarter.apps.llmhost.services import LLMHostService, LLMHostServiceError
from smarter.apps.llmhost.services.compute import ComputeProvisioner
from smarter.apps.llmhost.services.exceptions import LLMHostComputeError
from smarter.common.conf import smarter_settings
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.workers.celery import app

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.TASK_LOGGING, SmarterWaffleSwitches.LLM_HOST_LOGGING]
)
logger_prefix = formatted_text(__name__)


def managed_hostname(llmhost: LLMHost) -> Optional[str]:
    """The Ingress hostname, if Smarter chose it, and so manages its DNS record."""
    service = LLMHostService()
    try:
        spec = service.spec_of(llmhost)
    except LLMHostServiceError:
        return None
    if not spec.network.ingress or spec.network.hostname:
        return None
    return service.default_hostname(llmhost, service.base_name(llmhost))


def dns_enabled() -> bool:
    """Whether LLMHost tasks manage DNS records, like LLMClient tasks."""
    # pylint: disable=import-outside-toplevel
    from smarter.common.helpers.aws_helpers import aws_helper

    return bool(smarter_settings.llmclient_tasks_create_dns_record and aws_helper.route53)


def create_dns_record(llmhost: LLMHost) -> None:
    hostname = managed_hostname(llmhost)
    if not hostname or not dns_enabled():
        return
    # pylint: disable=import-outside-toplevel
    from smarter.common.helpers.aws_helpers import aws_helper

    try:
        aws_helper.route53.create_domain_a_record(  # type: ignore[union-attr]
            hostname=hostname, api_host_domain=smarter_settings.environment_api_domain
        )
        logger.info("%s created the DNS record %s for %s", logger_prefix, hostname, llmhost)
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("%s failed to create the DNS record %s for %s: %s", logger_prefix, hostname, llmhost, e)


def destroy_dns_record(llmhost: LLMHost) -> None:
    hostname = managed_hostname(llmhost)
    if not hostname or not dns_enabled():
        return
    # pylint: disable=import-outside-toplevel
    from smarter.apps.llmclient.tasks.destroy_domain_a_record import (
        destroy_domain_A_record,
    )

    destroy_domain_A_record.delay(hostname=hostname, api_host_domain=smarter_settings.environment_api_domain)


@app.task(queue=smarter_settings.infrastructure_tasks_celery_task_queue)
def launch_llmhost(llmhost_id: int) -> Optional[str]:
    """
    Launch an LLMHost, and create the DNS record of its Ingress.

    :returns: The LLMHost's status, or None if it does not exist.
    """
    llmhost = LLMHost.objects.filter(pk=llmhost_id).first()
    if llmhost is None:
        logger.warning("%s.launch_llmhost() LLMHost %s does not exist.", logger_prefix, llmhost_id)
        return None
    observation = LLMHostService().launch(llmhost)
    create_dns_record(llmhost)
    if llmhost.compute_id:  # type: ignore[attr-defined]
        reconcile_llmhost_compute.apply_async((llmhost.compute_id,), countdown=RECONCILE_INTERVAL_SECONDS)  # type: ignore[attr-defined]
    return observation.status


@app.task(queue=smarter_settings.infrastructure_tasks_celery_task_queue)
def destroy_llmhost(llmhost_id: int, purge: bool = False) -> Optional[str]:
    """
    Destroy an LLMHost's Kubernetes resources, and the DNS record of its Ingress.

    :returns: The LLMHost's status, or None if it does not exist.
    """
    llmhost = LLMHost.objects.filter(pk=llmhost_id).first()
    if llmhost is None:
        logger.warning("%s.destroy_llmhost() LLMHost %s does not exist.", logger_prefix, llmhost_id)
        return None
    LLMHostService().destroy(llmhost, purge=purge)
    destroy_dns_record(llmhost)
    if llmhost.compute_id:  # type: ignore[attr-defined]
        # a node that was still starting when the LLMHost was destroyed is removed once it joins.
        reconcile_llmhost_compute.apply_async((llmhost.compute_id,), countdown=RECONCILE_INTERVAL_SECONDS)  # type: ignore[attr-defined]
    return llmhost.status


@app.task(queue=smarter_settings.infrastructure_tasks_celery_task_queue)
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
        logger.warning("%s.refresh_llmhost_status() the Kubernetes cluster is not available.", logger_prefix)
        return {}
    retval = {}
    for llmhost in llmhosts.select_related("user_profile", "user_profile__account"):
        try:
            retval[llmhost.name] = service.observe(llmhost).status
        except LLMHostServiceError as e:
            logger.error("%s.refresh_llmhost_status() failed for %s: %s", logger_prefix, llmhost, e)
    return retval


@app.task(queue=smarter_settings.infrastructure_tasks_celery_task_queue)
def reconcile_llmhost_compute(compute_id: int, attempt: int = 1) -> Optional[dict[str, Any]]:
    """
    Reconcile a compute's node group with its LLMHosts, and check their status.

    Runs again in
    30 seconds, until the node group is settled, or after RECONCILE_MAX_ATTEMPTS.

    :returns: The compute's state, or None if it does not exist.
    """
    compute = LLMHostCompute.objects.filter(pk=compute_id).first()
    if compute is None:
        logger.warning("%s.reconcile_llmhost_compute() LLMHostCompute %s does not exist.", logger_prefix, compute_id)
        return None
    service = LLMHostService()
    state = None
    try:
        state = ComputeProvisioner(cluster=service.cluster).reconcile(compute)
    except LLMHostComputeError as e:
        logger.error("%s.reconcile_llmhost_compute() failed for %s: %s", logger_prefix, compute, e)
    if service.cluster.ready:
        for llmhost in compute.llmhosts.filter(status__in=SAMLLMHostStatusEnum.deployed()):  # type: ignore[attr-defined]
            try:
                service.observe(llmhost, probe=False)
            except LLMHostServiceError as e:
                logger.error("%s.reconcile_llmhost_compute() status check of %s failed: %s", logger_prefix, llmhost, e)
    if (state is None or not state.settled) and attempt < RECONCILE_MAX_ATTEMPTS:
        reconcile_llmhost_compute.apply_async((compute_id, attempt + 1), countdown=RECONCILE_INTERVAL_SECONDS)
    return asdict(state) if state is not None else None


@app.task(queue=smarter_settings.infrastructure_tasks_celery_task_queue)
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
            logger.error("%s.reconcile_llmhost_computes() failed for %s: %s", logger_prefix, compute, e)
            retval[compute.name] = str(e)
    return retval


@app.task(queue=smarter_settings.llmclient_tasks_celery_task_queue)
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
                logger.error("%s.charge_llmhost_computes() failed to charge %s: %s", logger_prefix, resource, e)
        retval[compute.name] = str(cost)
    return retval


__all__ = [
    "charge_llmhost_computes",
    "destroy_llmhost",
    "launch_llmhost",
    "reconcile_llmhost_compute",
    "reconcile_llmhost_computes",
    "refresh_llmhost_status",
]
