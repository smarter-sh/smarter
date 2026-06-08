"""
Celery tasks for llm_client app.

These tasks are long-running and/or i/o intensive operations that are managed by Celery.
They are intended to be called asynchronously from the main application.
"""

from smarter.common.helpers.aws.acm import AWSCertificateManager
from smarter.common.helpers.aws.route53 import AWSRoute53
from smarter.common.helpers.aws_helpers import aws_helper
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.TASK_LOGGING, SmarterWaffleSwitches.LLM_CLIENT_LOGGING]
)
logger_prefix = logging.formatted_text(__name__)


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
