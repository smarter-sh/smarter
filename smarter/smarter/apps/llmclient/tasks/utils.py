"""
Celery tasks for llmclient app.

These tasks are long-running and/or i/o intensive operations that are managed by Celery.
They are intended to be called asynchronously from the main application.
"""

import os
from string import Template

from smarter.apps.infrastructure.services import infrastructure
from smarter.common.conf import smarter_settings
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.TASK_LOGGING, SmarterWaffleSwitches.LLM_CLIENT_LOGGING]
)
logger_prefix = logging.formatted_text(__name__)

INGRESS_TEMPLATE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../k8s/ingress.yaml.tpl"))


def is_taskable() -> bool:
    """Whether the cloud's DNS and certificate services are ready for task processing."""
    prefix = logger_prefix + f".{is_taskable.__name__}()"
    # verifies that the cloud credentials are available and valid.
    if not infrastructure.ready:
        logger.info("%s the cloud provider is not ready. Request is not taskable.", prefix)
        return False

    if not infrastructure.dns.ready:
        logger.info("%s the DNS service is not ready. Request is not taskable.", prefix)
        return False

    if not infrastructure.certificates.ready:
        logger.info("%s the certificate service is not ready. Request is not taskable.", prefix)
        return False

    return True


def apply_ingress_manifest(domain: str) -> None:
    """
    Create, or update, the Kubernetes ingress of an llmclient's hostname.

    cert-manager issues the hostname's TLS certificate for the ingress, into the secret
    ``<domain>-tls``.

    :param domain: The hostname, e.g. an llmclient's default host or custom host.
    :raises SmarterException: If the manifest cannot be applied.
    """
    ingress_values = {
        "app_name": smarter_settings.platform_name,
        "cluster_issuer": smarter_settings.environment_api_domain,
        "environment_namespace": smarter_settings.environment_namespace,
        "domain": domain,
        "service_name": "smarter",
    }
    with open(INGRESS_TEMPLATE_PATH, encoding="utf-8") as ingress_template:
        manifest = Template(ingress_template.read()).substitute(ingress_values)
    infrastructure.kubernetes.apply_manifest(manifest)
