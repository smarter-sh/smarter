"""Common classes"""

from logging import getLogger

from django.http import HttpRequest

from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.django.validators import SmarterValidator


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

    def smarter_build_absolute_uri(self, request: HttpRequest) -> str:
        """
        A utility function to attempt to get the request URL from any valid
        child class of HttpRequest. This mostly protects us from unit tests
        class mutations that do not implement build_absolute_uri().

        TO DO: refactor initialize request from __init__() to a property
        to avoid having to redundantly pass the request object around.

        :param request: The request object.
        :return: The request URL.
        """
        if request is None:
            return None

        url: str = None

        try:
            url = request.build_absolute_uri() if hasattr(request, "build_absolute_uri") else None
        except (AttributeError, KeyError):
            logger.warning(
                "%s.smarter_build_absolute_uri() failed to call request.build_absolute_uri() with error: %s",
                self.formatted_class_name,
                formatted_text("AttributeError or KeyError"),
            )
            url = None

        if url is not None:
            return url

        try:
            url = f"{request.scheme}://{request.get_host()}{request.get_full_path()}"
            if SmarterValidator.is_valid_url(url):
                return url
        except (AttributeError, KeyError):
            logger.warning(
                "%s.smarter_build_absolute_uri() failed to call request.get_host() or request.get_full_path() with error: %s, request: %s, %s",
                self.formatted_class_name,
                formatted_text("AttributeError or KeyError"),
                request,
                type(request).__name__,
            )

        try:
            scheme = request.META.get("wsgi.url_scheme", "http")
            host = request.META.get("HTTP_HOST", request.META.get("SERVER_NAME"))
            path = request.get_full_path()
            url = f"{scheme}://{host}{path}"
            if SmarterValidator.is_valid_url(url):
                logger.info(
                    "%s.smarter_build_absolute_uri() generated with request.META parameters: %s",
                    self.formatted_class_name,
                    url,
                )
                return url
        except (AttributeError, KeyError):
            logger.warning(
                "%s.smarter_build_absolute_uri() failed to build URL from request.META with error: %s",
                self.formatted_class_name,
                formatted_text("AttributeError or KeyError"),
            )

        logger.error(
            "%s.smarter_build_absolute_uri() failed to generate a valid URL from the request object.",
            self.formatted_class_name,
        )
        return None
