"""Receiver functions for chatapp signals."""

# pylint: disable=W0613


import logging
from typing import Optional

from django.core.handlers.wsgi import WSGIRequest
from django.dispatch import receiver

from smarter.common.conf import smarter_settings
from smarter.common.helpers.console_helpers import formatted_json, formatted_text
from smarter.lib import json
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
    json_content: Optional[dict]
    content = response.content if hasattr(response, "content") else None
    try:
        if isinstance(content, dict):
            json_content = content
        elif isinstance(content, str):
            json_content = json.loads(content)
        else:
            logger.warning(
                "handle_api_request_completed: recasting json content %s %s failed. attempting to load as json",
                type(content),
                content,
            )
            json_content = json.loads(content) if content else None
    # pylint: disable=W0718
    except Exception:
        logger.warning(
            "handle_api_request_completed: recasting json content %s %s failed. attempting to decode as utf-8",
            type(content),
            content,
        )
        try:
            json_content = content.decode("utf-8", errors="replace")
            json_content = json.loads(json_content) if isinstance(json_content, str) else json_content
        except Exception:
            json_content = None

    logger.info(
        "%s - %s - %s\n%s",
        formatted_text("smarter.apps.api.receivers.api_request_completed"),
        instance.__class__.__name__,
        request.path,
        formatted_json(json_content) if isinstance(json_content, dict) else json_content,
    )
