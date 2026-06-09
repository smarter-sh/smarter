# pylint: disable=W0613,C0302
"""
PromptLandingView is a Django class-based view that serves as the base URL
"""

import logging

from django.http import (
    HttpRequest,
    HttpResponseNotFound,
)

from smarter.common.conf import smarter_settings
from smarter.lib.django import waffle
from smarter.lib.django.views import SmarterAuthenticatedNeverCachedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PROMPT_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


def should_log_verbose(level):
    """Check if logging should be done based on the waffle switch."""
    return smarter_settings.verbose_logging


verbose_logger = WaffleSwitchedLoggerWrapper(base_logger, should_log_verbose)


class PromptLandingView(SmarterAuthenticatedNeverCachedWebView):
    """
    Base url for the Smarter prompt application. Provides a logical
    endpoint without actually implementing any functionality.
    """

    def dispatch(self, request: HttpRequest, *args, **kwargs):
        return HttpResponseNotFound()
