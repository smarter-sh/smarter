"""Receiver functions for chatapp signals."""

# pylint: disable=W0613


import logging

from django.dispatch import receiver
from rest_framework.request import Request

from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from .signals import api_request_completed, api_request_initiated
from .v1.cli.views.base import CliBaseApiView


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.RECEIVER_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


# api_request_initiated.send(sender=self.__class__, instance=self, request=request)
@receiver(api_request_initiated, dispatch_uid="api_request_initiated")
def handle_api_request_initiated(sender, instance: CliBaseApiView, request: Request, **kwargs):
    """Handle API request initiated signal."""
    logger.info(
        "%s - %s - %s",
        formatted_text("smarter.apps.api.receivers.api_request_initiated"),
        instance.__class__.__name__,
        request.path,
    )


@receiver(api_request_completed, dispatch_uid="api_request_completed")
def handle_api_request_completed(sender, instance: CliBaseApiView, request: Request, response, **kwargs):
    """Handle API request completed signal."""

    logger.info(
        "%s - %s - %s",
        formatted_text("smarter.apps.api.receivers.api_request_completed"),
        instance.__class__.__name__,
        request.path,
    )
