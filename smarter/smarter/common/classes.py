"""Common classes"""

import json
from typing import Union
from logging import getLogger

import yaml
from django.http import HttpRequest

from smarter.common.helpers.console_helpers import formatted_text
from smarter.common.utils import (
    smarter_build_absolute_uri as utils_smarter_build_absolute_uri,
)
from smarter.common.exceptions import SmarterValueError
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

    def to_json(self) -> dict:
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
        return utils_smarter_build_absolute_uri(request)

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
