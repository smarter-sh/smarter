"""
Point the ingresses of deployed LLMClients at the api's renamed Kubernetes Service.

The api's Service was renamed from :data:`~smarter.apps.llmclient.tasks.utils.LEGACY_API_SERVICE_NAME`,
``smarter``, to :data:`~smarter.apps.llmclient.tasks.utils.API_SERVICE_NAME`, ``smarter-api``. New ingresses
name the new Service. Each LLMClient's existing ingress, which its deployment created, still names the old one,
which the Helm chart keeps as an alias for one release. ``manage.py initialize_platform`` calls this, through
``manage.py retarget_llmclient_ingresses``, so that every deployment rewrites the ingresses that still need it.

Safety
------

- It finds the ingresses from the database, by the default and custom hosts of the deployed LLMClients, never by
  a label search, which would also find the platform's own ingresses that smarter-infrastructure manages.
- It rewrites an ingress only if it exists and still names the old Service, so a second run changes nothing.
- It re-applies the same template that deploying an LLMClient applies, :func:`apply_ingress_manifest`, so a
  rewritten ingress is exactly what a new deployment would create.
- It does nothing where the platform doesn't create ingresses (``llmclient_tasks_create_ingress_manifest``), or
  where Kubernetes isn't configured, e.g. a developer's machine.
"""

from typing import Optional

from smarter.apps.infrastructure.services import infrastructure
from smarter.apps.llmclient.models import LLMClient
from smarter.common.conf import smarter_settings
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.typing import SmarterDictType

from .utils import LEGACY_API_SERVICE_NAME, apply_ingress_manifest

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.TASK_LOGGING, SmarterWaffleSwitches.LLM_CLIENT_LOGGING]
)
logger_prefix = logging.SmarterFormattedText.text(__name__)


def deployed_hosts() -> list[str]:
    """
    The hosts that deployed LLMClients' ingresses serve: each one's default host, and its custom host, if any.

    :returns: The hosts, each once, in a stable order.
    """
    hosts: list[str] = []
    for llmclient in LLMClient.objects.filter(deployed=True).select_related("user_profile__account", "custom_domain"):
        candidates = [llmclient.default_host, llmclient.custom_host]
        for host in candidates:
            if host and host not in hosts:
                hosts.append(host)
    return hosts


def backend_service_name(ingress: SmarterDictType) -> Optional[str]:
    """
    The name of the Service that an ingress sends its requests to, from its first rule's first path.

    :param ingress: The ingress, as the Kubernetes api returns it.
    :returns: The Service's name, or None if the ingress has no such backend.
    """
    spec = ingress.get("spec") or {}
    rules = spec.get("rules") or []
    if not rules:
        return None
    http = rules[0].get("http") or {}
    paths = http.get("paths") or []
    if not paths:
        return None
    backend = paths[0].get("backend") or {}
    service = backend.get("service") or {}
    return service.get("name")


def retarget_llmclient_ingresses(dry_run: bool = False) -> list[str]:
    """
    Re-apply the ingress of each deployed LLMClient host whose ingress still names the old Service.

    :param dry_run: Find the ingresses, and log them, but change nothing.
    :returns: The hosts whose ingresses were rewritten, or that a dry run would rewrite.
    """
    fn_name = logger_prefix + ".retarget_llmclient_ingresses()"
    if not smarter_settings.llmclient_tasks_create_ingress_manifest:
        logger.info("%s skipped: this platform doesn't create LLMClient ingresses.", fn_name)
        return []
    if not infrastructure.kubernetes.ready:
        logger.info("%s skipped: Kubernetes isn't configured.", fn_name)
        return []

    namespace = smarter_settings.environment_namespace
    retargeted: list[str] = []
    for host in deployed_hosts():
        ingress = infrastructure.kubernetes.get_resource("ingress", host, namespace)
        if ingress is None:
            continue
        if backend_service_name(ingress) != LEGACY_API_SERVICE_NAME:
            continue
        if not dry_run:
            apply_ingress_manifest(host)
        retargeted.append(host)
        logger.info("%s %s the ingress of %s", fn_name, "would retarget" if dry_run else "retargeted", host)
    logger.info("%s %d ingresses %s.", fn_name, len(retargeted), "would be retargeted" if dry_run else "retargeted")
    return retargeted
