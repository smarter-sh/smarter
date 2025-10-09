"""Common classes"""

import ipaddress
import logging
from typing import Any, Optional, Union

import yaml
from django.http import HttpRequest
from django.utils.deprecation import MiddlewareMixin

from smarter.common.exceptions import SmarterValueError
from smarter.common.helpers.console_helpers import formatted_text
from smarter.common.utils import (
    smarter_build_absolute_uri as utils_smarter_build_absolute_uri,
)
from smarter.lib import json
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.MIDDLEWARE_LOGGING) and level >= logging.INFO


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


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
    A generic mixin with helper functions.
    """

    def __init__(self, *args, **kwargs):
        pass

    @property
    def formatted_class_name(self) -> str:
        """
        For logging. Applies standardized styling to the class name.
        """
        return formatted_text(self.__class__.__name__)

    @property
    def unformatted_class_name(self) -> str:
        """
        For logging. Applies standardized styling to the class name.
        """
        return self.__class__.__name__

    @property
    def ready(self) -> bool:
        return True

    @property
    def amnesty_urls(self) -> list[str]:
        """
        A list of URLs that are exempt from certain checks.
        This is a placeholder and should be overridden in subclasses.
        """
        return ["readiness", "healthz", "favicon.ico", "robots.txt", "sitemap.xml"]

    def to_json(self) -> dict[str, Any]:
        """
        A placeholder method for converting the object to JSON.
        Should be overridden in subclasses.
        """
        return {
            "class_name": self.unformatted_class_name,
        }

    def smarter_build_absolute_uri(self, request: HttpRequest) -> str:
        """
        A utility function to attempt to get the request URL from any valid
        child class of HttpRequest. This mostly protects us from unit tests
        class mutations that do not implement build_absolute_uri().

        :param request: The request object.
        :return: The request URL.
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
    """A mixin for middleware classes with helper functions."""

    def get_client_ip(self, request) -> Optional[str]:
        """Get client IP address from request."""

        # In AWS CLB -> Kubernetes Nginx setup, the client IP flow is:
        # Client -> CLB -> Nginx Ingress -> Django
        # CLB adds X-Forwarded-For with original client IP
        # Nginx may add X-Real-IP or modify X-Forwarded-For

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
            return remote_addr

    def _is_private_ip(self, ip):
        """Check if IP is in private/internal ranges."""
        try:
            ip_obj = ipaddress.ip_address(ip)
            logger.info(
                "%s._is_private_ip() - Checking IP: %s, is_private: %s",
                self.formatted_class_name,
                ip,
                ip_obj.is_private,
            )
            return ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local
        except ValueError as e:
            logger.warning("%s._is_private_ip() - Invalid IP address: %s, error: %s", self.formatted_class_name, ip, e)
            return True

    def has_auth_indicators(self, request):
        """Check if request has authentication indicators (cookies, headers, etc.)."""

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
        if hasattr(request, "user") and request.user.is_authenticated:
            return True

        return False
