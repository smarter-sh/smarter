"""
SmarterMiddlewareMixin: A mixin for middleware classes with helper functions.
"""

import ipaddress
import re
import uuid
from typing import Optional

from django.utils.deprecation import MiddlewareMixin

from smarter.common.conf import smarter_settings
from smarter.common.utils import (
    is_authenticated_request,
)

from .helper_mixin import SmarterHelperMixin
from .logger import logger

MOCK_REGEX = re.compile(r"<MagicMock|<Mock|mock\\.MagicMock|mock\\.Mock", re.IGNORECASE)


class SmarterMiddlewareMixin(MiddlewareMixin, SmarterHelperMixin):
    """A mixin for middleware classes with helper functions.

    This mixin provides utilities for extracting client IP addresses,
    checking authentication indicators, and other middleware-related helpers.
    Inherits from both Django's :class:`MiddlewareMixin` and :class:`SmarterHelperMixin`.
    """

    def __call__(self, request):
        logger.debug(
            "%s.__call__() - processing request: %s",
            self.formatted_class_name,
            self.smarter_build_absolute_uri(request),
        )
        return super().__call__(request)

    def get_client_ip(self, request) -> Optional[str]:
        """
        Get client IP address from request.

        This method attempts to determine the original client IP address,
        accounting for proxies, load balancers, and CDNs. It checks common
        headers set by proxies and falls back to ``REMOTE_ADDR``.

        Notes
        -----
        - In AWS CLB → Kubernetes Nginx setups, the client IP flow is:
          Client → CLB → Nginx Ingress → Django.
          - CLB adds ``X-Forwarded-For`` with the original client IP.
          - Nginx may add ``X-Real-IP`` or modify ``X-Forwarded-For``.
          - Django sees ``REMOTE_ADDR`` as the Nginx IP (not the client IP).
        - If using Cloudflare, it adds the ``CF-Connecting-IP`` header.
        - Always validate IPs to avoid trusting spoofed headers.

        :param request: The Django request object.
        :type request: HttpRequest
        :return: The detected client IP address, or None if not found.
        :rtype: Optional[str]
        """

        # First check X-Forwarded-For (most reliable for CLB)
        # set by Nginx ingress controller and Traefik.
        # Contains the original client IP and any proxy IPs.
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded_for:
            # X-Forwarded-For format: "client_ip, proxy1_ip, proxy2_ip"
            # The leftmost IP is the original client IP
            client_ip = forwarded_for.split(",")[0].strip()
            # Validate it's not a private IP (load balancer/proxy IP)
            if not self._is_private_ip(client_ip):
                logger.debug(
                    "%s.get_client_ip() - Using X-Forwarded-For: %s",
                    self.formatted_class_name,
                    client_ip,
                )
                return client_ip

        # Check X-Real-IP (set by Nginx ingress controller and Traefik)
        real_ip = request.META.get("HTTP_X_REAL_IP")
        if real_ip and not self._is_private_ip(real_ip.strip()):
            logger.debug(
                "%s.get_client_ip() - Using X-Real-IP: %s",
                self.formatted_class_name,
                real_ip.strip(),
            )
            return real_ip.strip()

        # Check Cloudflare connecting IP if using Cloudflare
        cf_ip = request.META.get("HTTP_CF_CONNECTING_IP")
        if cf_ip and not self._is_private_ip(cf_ip.strip()):
            logger.debug(
                "%s.get_client_ip() - Using CF-Connecting-IP: %s",
                self.formatted_class_name,
                cf_ip.strip(),
            )
            return cf_ip.strip()

        # Fallback to REMOTE_ADDR (will be load balancer IP in AWS)
        remote_addr = request.META.get("REMOTE_ADDR", "127.0.0.1")
        logger.debug(
            "%s.get_client_ip() - Falling back to REMOTE_ADDR: %s",
            self.formatted_class_name,
            remote_addr,
        )

        if not self._is_private_ip(remote_addr):
            logger.debug(
                "%s.get_client_ip() - Using REMOTE_ADDR: %s",
                self.formatted_class_name,
                remote_addr,
            )
            return remote_addr

        if request.path.replace("/", "") not in self.amnesty_urls and not smarter_settings.environment_is_local:
            logger.warning(
                "%s __call()__ - Could not determine client IP: %s, Meta: %s",
                self.formatted_class_name,
                self.smarter_build_absolute_uri(request=request),
                request.META,
            )
        return None

    def _is_private_ip(self, ip):
        """Check if IP is in private/internal ranges."""
        try:
            ip_obj = ipaddress.ip_address(ip)
            return ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local
        except ValueError as e:
            # Regex to match MagicMock or mock object string representations
            ip_str = str(ip)
            if MOCK_REGEX.search(ip_str) or "Mock" in getattr(ip, "__class__", type(ip)).__name__:
                logger.warning(
                    "%s._is_private_ip() - Mock object detected as IP: %s", self.formatted_class_name, ip_str
                )
            else:
                logger.warning(
                    "%s._is_private_ip() - Invalid IP address: %s, error: %s", self.formatted_class_name, ip_str, e
                )
            return True

    def has_auth_indicators(self, request):
        """
        Check if request has authentication indicators (cookies, headers, etc.).

        This method inspects the request for common authentication signals,
        such as session cookies, CSRF tokens, authorization headers, API keys,
        or Django's built-in authentication.

        :param request: The Django request object.
        :type request: HttpRequest
        :return: True if authentication indicators are present, False otherwise.
        :rtype: bool
        """

        # Check for Django session cookie
        if request.COOKIES.get("sessionid"):
            return True

        # Check for CSRF token (indicates active session)
        if request.COOKIES.get("csrftoken"):
            return True

        # Check for Authorization header
        if request.META.get("HTTP_AUTHORIZATION"):
            return True

        # Check for API key header
        if request.META.get("HTTP_X_API_KEY"):
            return True

        # Check if user is authenticated (Django built-in)
        if is_authenticated_request(request):
            return True

        return False

    def job_id_factory(self, prefix: str = "job") -> str:
        """
        Factory method to generate a unique job ID.

        This method creates a unique identifier for jobs or tasks, using
        a specified prefix and a random UUID. The resulting ID is
        formatted as "{prefix}_{uuid}". This is used primarily for
        managing subscriptions to Server-Sent Events (SSE) channels,
        for ensuring that each subscription has a unique identifier.

        :param prefix: The prefix to use for the job ID (default is "job").
        :type prefix: str
        :return: A unique job ID string.
        :rtype: str
        """
        return f"{prefix}_{str(uuid.uuid4())}"


__all__ = [
    "SmarterMiddlewareMixin",
]
