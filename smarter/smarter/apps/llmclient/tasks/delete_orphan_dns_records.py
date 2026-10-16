"""
Celery task that deletes the orphaned DNS records of deleted LLMClients.

Deploying an LLMClient creates an A record for its default host, e.g.
``example.3141-5926-5359.api.example.com``, in the zone of the environment's API domain.
Deleting the LLMClient should delete the record, but a record outlives its LLMClient when the
deletion's task fails or never runs. This task, which Celery Beat runs daily, finds those orphans
and deletes them.

Main Tasks
----------

- delete_orphan_dns_records(dry_run): Delete the A records of hosts that no LLMClient or LLMHost uses.

Safety
------

The task deletes real DNS records, so it is conservative:

- It runs only in the AWS environments, e.g. ``alpha`` and ``prod``. Elsewhere, the API domain
  is a proxy domain that every developer's local environment shares, and a local database does
  not know the others' LLMClients.
- It looks only in the zone of this environment's API domain, and only at A records whose name
  is exactly ``<label>.<account number>.<API domain>``: the shape of an LLMClient's default host.
  Another environment's hosts, e.g. ``example.3141-5926-5359.alpha.api.example.com`` in the zone
  of ``api.example.com``, have more labels, and are never touched.
- A host that any LLMClient or LLMHost uses is live, whether or not it is deployed. LLMHost
  Ingresses have hosts of the same shape, in the same zone.
- It deletes nothing if the database has no LLMClients, or if a live host cannot be computed,
  because every record would then look orphaned.
- It deletes at most :data:`MAX_DELETIONS_PER_RUN` records per run.

Usage
-----

Queue the Celery task, or call it directly to run it synchronously:

    delete_orphan_dns_records.delay()
    delete_orphan_dns_records(dry_run=True)

``python manage.py delete_orphan_dns_records --dry-run`` lists the orphans without deleting them.
"""

import re

from smarter.apps.infrastructure.services import infrastructure
from smarter.apps.infrastructure.services.dns import normalize_name
from smarter.apps.llmclient.models import LLMClient
from smarter.common.conf import smarter_settings
from smarter.common.const import SmarterEnvironments
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.workers.celery import app

from .utils import is_taskable

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.TASK_LOGGING, SmarterWaffleSwitches.LLM_CLIENT_LOGGING]
)
logger_prefix = logging.formatted_text(__name__)

MAX_DELETIONS_PER_RUN = 50
"""The most records that one run deletes.

The rest are deleted by the next runs.
"""

HOST_LABEL = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
"""An RFC 1034 label, e.g. an LLMClient's ``rfc1034_compliant_name``.

A wildcard, ``*``, is not one.
"""

ACCOUNT_NUMBER = r"\d{4}-\d{4}-\d{4}"
"""An account number, e.g. ``3141-5926-5359``."""


class OrphanDNSRecordsError(Exception):
    """The live hosts could not be determined, so no record can be judged orphaned."""


def api_domain() -> str:
    """The domain whose zone holds the LLMClients' default hosts, e.g. ``api.example.com``."""
    return normalize_name(smarter_settings.environment_api_domain)


def host_pattern(domain: str) -> re.Pattern:
    """
    The shape of an LLMClient's default host in a domain: ``<label>.<account number>.<domain>``.

    :param domain: The environment's API domain, e.g. ``api.example.com``.
    :returns: A pattern that matches a whole record name.
    """
    return re.compile(rf"^{HOST_LABEL}\.{ACCOUNT_NUMBER}\.{re.escape(domain)}$")


def live_hosts() -> set[str]:
    """
    Return the hosts that existing LLMClients and LLMHosts use, deployed or not.

    :returns: The hosts, normalized, e.g. ``example.3141-5926-5359.api.example.com``.
    :raises OrphanDNSRecordsError: If there are no LLMClients, or a host cannot be computed.
    """
    # pylint: disable=import-outside-toplevel
    from smarter.apps.llmhost.models import LLMHost
    from smarter.apps.llmhost.services.service import LLMHostService

    llmclients = list(LLMClient.objects.select_related("user_profile__account"))
    if not llmclients:
        raise OrphanDNSRecordsError("the database has no LLMClients.")
    hosts: set[str] = set()
    try:
        for llmclient in llmclients:
            hosts.add(normalize_name(llmclient.default_host))
        for llmhost in LLMHost.objects.select_related("user_profile__account"):
            hosts.add(normalize_name(LLMHostService.default_hostname(llmhost, LLMHostService.base_name(llmhost))))
    # pylint: disable=broad-except
    except Exception as e:
        raise OrphanDNSRecordsError(f"the host of a resource could not be computed: {e}") from e
    return hosts


@app.task(queue=smarter_settings.infrastructure_tasks_celery_task_queue)
def delete_orphan_dns_records(dry_run: bool = False) -> list[str]:
    """
    Delete the A records, in the zone of the environment's API domain, of hosts that no LLMClient or LLMHost uses.

    A Celery task, which Celery Beat runs daily, and which can also be called directly, to run
    synchronously. See the module's documentation for its safety rules.

    :param dry_run: Find the orphans, and log them, but delete nothing.
    :returns: The names of the orphaned records that were deleted, or that would be deleted by a dry run.
    """
    fn_name = logger_prefix + ".delete_orphan_dns_records()"
    if smarter_settings.environment not in SmarterEnvironments.aws_environments:
        logger.info("%s skipped: the %s environment shares its DNS zone.", fn_name, smarter_settings.environment)
        return []
    if not is_taskable():
        return []

    domain = api_domain()
    dns = infrastructure.dns
    zone = dns.get_zone(domain)
    if zone is None:
        logger.warning("%s DNS zone not found for %s. Nothing to do.", fn_name, domain)
        return []
    try:
        live = live_hosts()
    except OrphanDNSRecordsError as e:
        logger.error("%s deleted nothing: %s", fn_name, e)
        return []

    pattern = host_pattern(domain)
    orphans = sorted(
        record.name
        for record in dns.list_records(zone.id)
        if record.type == "A" and pattern.match(record.name) and record.name not in live
    )
    if len(orphans) > MAX_DELETIONS_PER_RUN:
        logger.warning(
            "%s found %s orphaned A records in %s. Deleting the first %s; the next runs delete the rest.",
            fn_name,
            len(orphans),
            domain,
            MAX_DELETIONS_PER_RUN,
        )
        orphans = orphans[:MAX_DELETIONS_PER_RUN]
    if dry_run:
        for name in orphans:
            logger.info("%s dry run: would delete the orphaned A record %s", fn_name, name)
        return orphans

    deleted = []
    for name in orphans:
        try:
            if dns.delete_record(zone.id, name, "A"):
                deleted.append(name)
                logger.info("%s deleted the orphaned A record %s from zone %s", fn_name, name, zone.id)
        # pylint: disable=broad-except
        except Exception as e:
            logger.error("%s failed to delete the orphaned A record %s: %s", fn_name, name, e)
    return deleted


__all__ = ["MAX_DELETIONS_PER_RUN", "OrphanDNSRecordsError", "delete_orphan_dns_records", "live_hosts"]
