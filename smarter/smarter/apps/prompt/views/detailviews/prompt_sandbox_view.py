# pylint: disable=W0613,C0302
"""PromptSandboxView is a Django class-based view that serves as the base URL."""

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


class PromptSandboxView(SmarterAuthenticatedNeverCachedWebView):
    """
    Base url for LLMClient.sandbox_url.

    This a a noop view that
    is used for generating the base URL for the workbench prompt
    /chat/ and /chat/config/ endpoints, both of which are constructed
    inside of the React app and are not actual Django views.
    """

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{PromptSandboxView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def dispatch(self, request: HttpRequest, *args, **kwargs):
        return HttpResponseNotFound()
