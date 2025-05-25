"""Common classes"""

from django.http import HttpRequest

from smarter.common.helpers.console_helpers import formatted_text


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

    @property
    def formatted_class_name(self):
        return formatted_text(self.__class__.__name__)

    def smarter_build_absolute_uri(self, request: HttpRequest) -> str:
        """
        A utility function to attempt to get the request URL.
        from any valid child class of HttpRequest.
        """
        url = self.smarter_build_absolute_uri(request)
        if url is not None:
            return url
        url = f"{request.scheme}://{request.get_host()}{request.get_full_path()}"
        if url is not None:
            return url
        scheme = request.META.get("wsgi.url_scheme", "http")
        host = request.META.get("HTTP_HOST", request.META.get("SERVER_NAME"))
        path = request.get_full_path()
        url = f"{scheme}://{host}{path}"
        return url
