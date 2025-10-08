"""Common classes"""

import ipaddress
from logging import getLogger
from typing import Any, Union

import yaml
from django.http import HttpRequest
from django.utils.deprecation import MiddlewareMixin

from smarter.common.exceptions import SmarterValueError
from smarter.common.helpers.console_helpers import formatted_text
from smarter.common.utils import (
    smarter_build_absolute_uri as utils_smarter_build_absolute_uri,
)
from smarter.lib import json


logger = getLogger(__name__)


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
