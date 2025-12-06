"""Common classes"""

import ipaddress
import logging
from typing import Any, Optional, Union

import yaml
from django.http import HttpRequest
from django.utils.deprecation import MiddlewareMixin

from smarter.common.conf import settings as smarter_settings
from smarter.common.exceptions import SmarterValueError
from smarter.common.helpers.console_helpers import formatted_text
from smarter.common.utils import (
    is_authenticated_request,
)
from smarter.common.utils import (
    smarter_build_absolute_uri as utils_smarter_build_absolute_uri,
)
from smarter.lib import json


logger = logging.getLogger(__name__)


class Singleton(type):
    """
    A metaclass for creating singleton classes.

    usage:
    class MyClass(metaclass=Singleton):
    """

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class SmarterHelperMixin:
    """
    A generic mixin providing helper functions for Smarter classes.

    This mixin offers utility methods and properties commonly needed
    across Smarter classes, such as standardized class name formatting,
    URL amnesty lists, JSON serialization, and data conversion.
    """

    def __init__(self, *args, **kwargs):
        pass

    @property
    def formatted_class_name(self) -> str:
        """
        Returns the class name formatted for logging.

        :return: The formatted class name as a string.
        :rtype: str

        """
        return formatted_text(self.__class__.__name__)

    @property
    def unformatted_class_name(self) -> str:
        """
        Returns the raw class name without formatting.

        :return: The unformatted class name as a string.
        :rtype: str

        This is useful for logging or serialization where the plain class name is needed.
        """
        return self.__class__.__name__

    @property
    def ready(self) -> bool:
        """
        Indicates whether the object is ready for use. This is a placeholder
        that should be overridden in subclasses.

        :return: True if ready, False otherwise.
        :rtype: bool
        """
        return True

    @property
    def amnesty_urls(self) -> list[str]:
        """
        Returns a list of URLs that are exempt from certain checks.

        This is a placeholder and should be overridden in subclasses.

        :return: List of URL path strings that are exempt.
        :rtype: list[str]
        """
        return ["readiness", "healthz", "favicon.ico", "robots.txt", "sitemap.xml"]

    def to_json(self) -> dict[str, Any]:
        """
        Convert the object to a JSON-serializable dictionary.

        This is a placeholder method and should be overridden in subclasses
        to provide a complete JSON representation of the object.

        :return: Dictionary representation of the object.
        :rtype: dict[str, Any]
        """
        return {
            "class_name": self.unformatted_class_name,
        }

    def smarter_build_absolute_uri(self, request: HttpRequest) -> str:
        """
        Attempts to get the absolute URI from a request object.

        This utility function tries to retrieve the request URL from any valid
        child class of :class:`django.http.HttpRequest`. It is especially useful
        in unit tests or scenarios where the request object may not implement
        ``build_absolute_uri()``.

        :param request: The request object.
        :type request: HttpRequest
        :return: The absolute request URL.
        :rtype: str
        :raises SmarterValueError: If the URI cannot be built from the request.
        """
        retval = utils_smarter_build_absolute_uri(request)
        if not retval:
            raise SmarterValueError(
                "Failed to build absolute URI from request. "
                "Ensure the request object is valid and has the necessary attributes."
            )
        return retval

    def data_to_dict(self, data: Union[dict, str]) -> dict:
        """
        Converts data to a dictionary, handling different types of input.

        This method accepts either a dictionary or a string. If a string is provided,
        it will attempt to parse it as JSON first, and if that fails, as YAML.
        If parsing fails or the data type is unsupported, a SmarterValueError is raised.

        :param data: The data to convert, either a dict or a JSON/YAML string.
        :type data: dict or str
        :return: The data as a dictionary.
        :rtype: dict
        :raises SmarterValueError: If the data cannot be converted to a dictionary.
        """
        if isinstance(data, dict):
            return data
        elif isinstance(data, str):
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                try:
                    return yaml.safe_load(data)
                except yaml.YAMLError as yaml_error:
                    raise SmarterValueError("String data is neither valid JSON nor YAML.") from yaml_error
        else:
            raise SmarterValueError("Unsupported data type for conversion to dict.")


class SmarterMiddlewareMixin(MiddlewareMixin, SmarterHelperMixin):
    """A mixin for middleware classes with helper functions.

    This mixin provides utilities for extracting client IP addresses,
    checking authentication indicators, and other middleware-related helpers.
    Inherits from both Django's :class:`MiddlewareMixin` and :class:`SmarterHelperMixin`.
    """

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
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded_for:
            # X-Forwarded-For format: "client_ip, proxy1_ip, proxy2_ip"
            # The leftmost IP is the original client IP
            client_ip = forwarded_for.split(",")[0].strip()
            # Validate it's not a private IP (load balancer/proxy IP)
            if not self._is_private_ip(client_ip):
                logger.info(
                    "%s.get_client_ip() - Using X-Forwarded-For: %s",
                    self.formatted_class_name,
                    client_ip,
                )
                return client_ip

        # Check X-Real-IP (set by Nginx ingress controller)
        real_ip = request.META.get("HTTP_X_REAL_IP")
        if real_ip and not self._is_private_ip(real_ip.strip()):
            logger.info(
                "%s.get_client_ip() - Using X-Real-IP: %s",
                self.formatted_class_name,
                real_ip.strip(),
            )
            return real_ip.strip()

        # Check Cloudflare connecting IP if using Cloudflare
        cf_ip = request.META.get("HTTP_CF_CONNECTING_IP")
        if cf_ip and not self._is_private_ip(cf_ip.strip()):
            logger.info(
                "%s.get_client_ip() - Using CF-Connecting-IP: %s",
                self.formatted_class_name,
                cf_ip.strip(),
            )
            return cf_ip.strip()

        # Fallback to REMOTE_ADDR (will be load balancer IP in AWS)
        remote_addr = request.META.get("REMOTE_ADDR", "127.0.0.1")
        logger.info(
            "%s.get_client_ip() - Falling back to REMOTE_ADDR: %s",
            self.formatted_class_name,
            remote_addr,
        )

        if not self._is_private_ip(remote_addr):
            logger.info(
                "%s.get_client_ip() - Using REMOTE_ADDR: %s",
                self.formatted_class_name,
                remote_addr,
            )
            return remote_addr

        if request.path.replace("/", "") not in self.amnesty_urls and not smarter_settings.environment_is_local:
            logger.warning(
                "%s __call()__ - Could not determine client IP: %s",
                self.formatted_class_name,
                self.smarter_build_absolute_uri(request=request),
            )
        return None

    def _is_private_ip(self, ip):
        """Check if IP is in private/internal ranges."""
        try:
            ip_obj = ipaddress.ip_address(ip)
            return ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local
        except ValueError as e:
            logger.warning("%s._is_private_ip() - Invalid IP address: %s, error: %s", self.formatted_class_name, ip, e)
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
