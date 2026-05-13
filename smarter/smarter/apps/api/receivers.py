"""Receiver functions for chatapp signals."""

# pylint: disable=W0613


from django.dispatch import receiver
from rest_framework.request import Request

from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .signals import api_request_completed, api_request_initiated

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.RECEIVER_LOGGING])


@receiver(api_request_initiated, dispatch_uid="api_request_initiated")
def handle_api_request_initiated(sender, instance, request: Request, **kwargs):
    """Handle API request initiated signal."""
    logger.info(
        "%s - %s - %s - %s - user: %s",
        logging.formatted_text(f"{__name__}.api_request_initiated()"),
        instance.__class__.__name__,
        request.path,
        request.method,
        request.user if hasattr(request, "user") and hasattr(request.user, "is_authenticated") else "N/A",
    )


@receiver(api_request_completed, dispatch_uid="api_request_completed")
def handle_api_request_completed(sender, instance, request: Request, response, **kwargs):
    """Handle API request completed signal."""

    logger.info(
        "%s - %s - %s - %s - user: %s",
        logging.formatted_text(f"{__name__}.api_request_completed()"),
        instance.__class__.__name__,
        request.path,
        request.method,
        request.user if hasattr(request, "user") and hasattr(request.user, "is_authenticated") else "N/A",
    )
