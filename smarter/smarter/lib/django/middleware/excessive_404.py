"""
Middleware to block clients that trigger excessive 404 responses.
"""

import ipaddress
import logging

from django.core.cache import cache
from django.http import HttpResponseForbidden
from django.utils.deprecation import MiddlewareMixin

from smarter.common.classes import SmarterHelperMixin


logger = logging.getLogger(__name__)


class BlockExcessive404Middleware(MiddlewareMixin, SmarterHelperMixin):
    """Block clients that trigger excessive 404 responses."""

    THROTTLE_LIMIT = 25
    THROTTLE_TIMEOUT = 600  # seconds (10 minutes)

    def get_client_ip(self, request):
        """Get client IP address from request."""
        # Check for real IP from various proxy headers in order of preference
        for header in ["HTTP_X_REAL_IP", "HTTP_X_FORWARDED_FOR", "HTTP_CF_CONNECTING_IP"]:
            ip = request.META.get(header)
            if ip:
                # X-Forwarded-For can contain multiple IPs, take the first (original client)
                if header == "HTTP_X_FORWARDED_FOR":
                    ip = ip.split(",")[0].strip()
                # Skip internal/private IP ranges (Kubernetes pods, load balancers)
                if not self._is_private_ip(ip.strip()):
                    return ip.strip()

        # Fallback to REMOTE_ADDR (should not be used in production behind proxies)
        return request.META.get("REMOTE_ADDR", "127.0.0.1")

    def _is_private_ip(self, ip):
        """Check if IP is in private/internal ranges."""
        try:
            ip_obj = ipaddress.ip_address(ip)
            return ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local
        except ValueError:
            # Invalid IP format
            return True

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
