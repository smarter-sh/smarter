"""
Celery tasks for the llmhost app, and how the web server queues them.

- :mod:`~smarter.apps.llmhost.tasks.llmhost`: launch, destroy and delete an LLMHost, and check its status.
- :mod:`~smarter.apps.llmhost.tasks.compute`: reconcile LLMHostComputes' node groups, delete a deleted
  compute's node group, and charge for their nodes.
- :mod:`~smarter.apps.llmhost.tasks.dns`: the DNS records of LLMHosts' Ingresses.
- :mod:`~smarter.apps.llmhost.tasks.queue`: the ``queue_*`` functions, which are how the manifest brokers, the
  api, the admin and the receivers change LLMHosts and computes. Only the infrastructure worker writes to the
  cluster and the cloud (ADR-038, phase 3, issue #1080).

Every name is exported here, so callers import from :mod:`smarter.apps.llmhost.tasks`. Each task names itself
``smarter.apps.llmhost.tasks.<function>`` (:data:`~smarter.apps.llmhost.const.TASK_NAME_PREFIX`), whatever its
module, which is the name that Celery Beat's schedule uses.
"""

from .compute import (
    charge_llmhost_computes,
    delete_llmhost_nodegroup,
    reconcile_llmhost_compute,
    reconcile_llmhost_computes,
)
from .dns import create_dns_record, destroy_dns_record, dns_enabled, managed_hostname
from .llmhost import (
    delete_llmhost,
    destroy_llmhost,
    launch_llmhost,
    record_task_failure,
    refresh_llmhost_status,
)
from .queue import (
    queue_delete,
    queue_destroy,
    queue_launch,
    queue_nodegroup_deletion,
    queue_reconcile,
)

__all__ = [
    "charge_llmhost_computes",
    "create_dns_record",
    "delete_llmhost",
    "delete_llmhost_nodegroup",
    "destroy_dns_record",
    "destroy_llmhost",
    "dns_enabled",
    "launch_llmhost",
    "managed_hostname",
    "queue_delete",
    "queue_destroy",
    "queue_launch",
    "queue_nodegroup_deletion",
    "queue_reconcile",
    "reconcile_llmhost_compute",
    "reconcile_llmhost_computes",
    "record_task_failure",
    "refresh_llmhost_status",
]
