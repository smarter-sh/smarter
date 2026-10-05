"""
Celery tasks for llmclient app.

These tasks are long-running and/or i/o intensive operations that are managed by Celery.
They are intended to be called asynchronously from the main application.
"""

import os
from string import Template

from smarter.common.conf import smarter_settings
from smarter.common.helpers.aws.acm import AWSCertificateManager
from smarter.common.helpers.aws.route53 import AWSRoute53
from smarter.common.helpers.aws_helpers import aws_helper
from smarter.common.helpers.k8s_helpers import kubernetes_helper
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.TASK_LOGGING, SmarterWaffleSwitches.LLM_CLIENT_LOGGING]
)
logger_prefix = logging.formatted_text(__name__)

INGRESS_TEMPLATE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../k8s/ingress.yaml.tpl"))


def is_taskable() -> bool:
    """
    Module helper function to check if aws resources are accessible.

    for task processing.
    """
    prefix = logger_prefix + f".{is_taskable.__name__}()"
    # verifies that the aws credentials are available and valid.
    if not aws_helper.ready():
        logger.info("%s AWS helper is not ready. Request is not taskable.", prefix)
        return False

    # verify that route53 and acm helpers are available.
    if not isinstance(aws_helper.route53, AWSRoute53):
        logger.info("%s AWS Route53 helper is not available. Request is not taskable.", prefix)
        return False

    if not isinstance(aws_helper.acm, AWSCertificateManager):
        logger.info("%s AWS ACM helper is not available. Request is not taskable.", prefix)
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
    kubernetes_helper.apply_manifest(manifest)
