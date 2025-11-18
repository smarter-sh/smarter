"""
Middleware to block clients that trigger excessive 404 responses.
"""

import logging

from django.core.cache import cache
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponseForbidden

from smarter.common.classes import SmarterMiddlewareMixin
from smarter.common.conf import settings as smarter_settings
from smarter.common.utils import is_authenticated_request
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return (
        waffle.switch_is_active(SmarterWaffleSwitches.MIDDLEWARE_LOGGING) and level >= smarter_settings.log_level
    ) or level >= logging.WARNING


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class BlockExcessive404Middleware(SmarterMiddlewareMixin):
    """Block clients that trigger excessive 404 responses."""

    THROTTLE_LIMIT = 25
    THROTTLE_TIMEOUT = 600  # seconds (10 minutes)

    def process_response(self, request: WSGIRequest, response):
        if response.status_code == 404:
            # skip this for authenticated users
            if is_authenticated_request(request):
                return response

            client_ip = self.get_client_ip(request)
            if not client_ip:
                return response

            throttle_key = f"excessive_404_throttle:{client_ip}"
            blocked_count = cache.get(throttle_key, 0)
            if blocked_count >= self.THROTTLE_LIMIT:
                logger.warning(
                    "%s Throttled client %s after %d 404s", self.formatted_class_name, client_ip, blocked_count
                )
                return HttpResponseForbidden(
                    "You have been blocked due to too many invalid requests from your IP. Try again later or contact support@smarter.sh."
                )
            try:
                blocked_count = cache.incr(throttle_key)
            except ValueError:
                cache.set(throttle_key, 1, timeout=self.THROTTLE_TIMEOUT)
                blocked_count = 1
            else:
                cache.set(throttle_key, blocked_count, timeout=self.THROTTLE_TIMEOUT)
        return response
