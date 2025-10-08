"""
Middleware to block clients that trigger excessive 404 responses.
"""

import logging

from django.core.cache import cache
from django.http import HttpResponseForbidden

from smarter.common.classes import SmarterMiddlewareMixin


logger = logging.getLogger(__name__)


class BlockExcessive404Middleware(SmarterMiddlewareMixin):
    """Block clients that trigger excessive 404 responses."""

    THROTTLE_LIMIT = 25
    THROTTLE_TIMEOUT = 600  # seconds (10 minutes)

    def process_response(self, request, response):
        if response.status_code == 404:
            client_ip = self.get_client_ip(request)
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
