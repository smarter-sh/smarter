"""
Celery tasks of the infrastructure app.

- :func:`sync_infrastructure_inventory`: Celery Beat, every few minutes. Discover the platform's
  Kubernetes cluster, i.e. the cluster, its add-ons, node groups, nodes, volumes, load balancers,
  ingresses and certificates, and reconcile the ledger with it. See
  :mod:`smarter.apps.infrastructure.services.inventory`.
"""

from smarter.common.conf import smarter_settings
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.workers.celery import app

from .services.inventory import sync_inventory

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.TASK_LOGGING, SmarterWaffleSwitches.INFRASTRUCTURE_LOGGING]
)
logger_prefix = logging.formatted_text(__name__)


@app.task(queue=smarter_settings.infrastructure_tasks_celery_task_queue)
def sync_infrastructure_inventory() -> dict[str, dict[str, int]]:
    """
    Discover the platform's Kubernetes cluster, and reconcile the ledger with it.

    :returns: For each resource type that could be listed, the number of resources that exist,
        and of those recorded as created and destroyed.
    """
    logger.debug("%s.sync_infrastructure_inventory() called", logger_prefix)
    return sync_inventory()


__all__ = ["sync_infrastructure_inventory"]
