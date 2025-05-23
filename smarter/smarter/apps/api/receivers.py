"""Receiver functions for chatapp signals."""

# pylint: disable=W0613


import json
from logging import getLogger

from django.core.handlers.wsgi import WSGIRequest
from django.dispatch import receiver

from smarter.common.helpers.console_helpers import formatted_json, formatted_text

from .signals import api_request_completed, api_request_initiated
from .v1.cli.views.base import CliBaseApiView


logger = getLogger(__name__)


# api_request_initiated.send(sender=self.__class__, instance=self, request=request)
@receiver(api_request_initiated, dispatch_uid="api_request_initiated")
def handle_api_request_initiated(sender, instance: CliBaseApiView, request: WSGIRequest, **kwargs):
    """Handle API request initiated signal."""
    logger.info(
        "%s - %s - %s",
        formatted_text("smarter.apps.api.receivers.api_request_initiated"),
        instance.__class__.__name__,
        request.path,
    )


@receiver(api_request_completed, dispatch_uid="api_request_completed")
def handle_api_request_completed(sender, instance: CliBaseApiView, request: WSGIRequest, response, **kwargs):
    """Handle API request completed signal."""
    json_content: dict
    try:
        json_content = json.loads(response.content)
    # pylint: disable=W0718
    except Exception:
        json_content = response.content.decode("utf-8", errors="replace")
    logger.info(
        "%s - %s - %s\n%s",
        formatted_text("smarter.apps.api.receivers.api_request_completed"),
        instance.__class__.__name__,
        request.path,
        formatted_json(json_content),
    )
