"""Common classes"""

import re
from typing import TYPE_CHECKING, Optional, Union

import yaml

from smarter.common.exceptions import SmarterValueError
from smarter.common.helpers.console_helpers import (
    formatted_text,
    formatted_text_green,
    formatted_text_red,
)
from smarter.common.utils import mask_string as util_mask_string
from smarter.common.utils import (
    smarter_build_absolute_uri as utils_smarter_build_absolute_uri,
)
from smarter.lib import json

from .logger import logger

if TYPE_CHECKING:
    from django.http import HttpRequest
MOCK_REGEX = re.compile(r"<MagicMock|<Mock|mock\\.MagicMock|mock\\.Mock", re.IGNORECASE)


class SmarterHelperMixin:
    """
    A generic mixin providing helper functions for Smarter classes.

    This mixin offers utility methods and properties commonly needed
    across Smarter classes, such as standardized class name formatting,
    URL amnesty lists, JSON serialization, and data conversion.
    """

    def __init__(self, *args, **kwargs):
        logger.debug("%s.__init__() - initializing with args=%s, kwargs=%s", self.formatted_class_name, args, kwargs)

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
    def formatted_state_ready(self) -> str:
        """
        Returns the readiness state formatted for logging.

        :return: The formatted readiness state as a string.
        :rtype: str
        """
        return formatted_text_green("READY")

    @property
    def formatted_state_not_ready(self) -> str:
        """
        Returns the not-ready state formatted for logging.

        :return: The formatted not-ready state as a string.
        :rtype: str
        """
        return formatted_text_red("NOT_READY")

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

    def smarter_build_absolute_uri(self, request: "HttpRequest") -> Optional[str]:
        """
        Attempts to get the absolute URI from a request object.

        This utility function tries to retrieve the request URL from any valid
        child class of :class:`django.http.HttpRequest`. It is especially useful
        in unit tests or scenarios where the request object may not implement
        ``build_absolute_uri()``.

        :param request: The request object.
        :type request: Optional[HttpRequest]
        :return: The absolute request URL.
        :rtype: Optional[str]
        :raises SmarterValueError: If the URI cannot be built from the request.
        """
        return utils_smarter_build_absolute_uri(request)

    def mask_string(
        self, string: Optional[str] = "", mask_char: str = "*", mask_length: int = 4, string_length: int = 8
    ) -> str:
        """
        Masks a string for secure logging.

        This utility function masks all but the last `unmasked_chars` characters
        of the input string, replacing them with asterisks. It is useful for
        logging sensitive information like API keys or passwords.

        :param string: The string to be masked.
        :type string: str
        :param mask_char: The character used for masking.
        :type mask_char: str
        :param mask_length: The number of characters to mask.
        :type mask_length: int
        :param string_length: The length of the string to consider for masking.
        :type string_length: int
        :return: The masked string.
        :rtype: str
        """
        return util_mask_string(
            string=string, mask_char=mask_char, mask_length=mask_length, string_length=string_length  # type: ignore
        )

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

    def sorted_dict(self, data: dict) -> dict:
        """
        Returns a new dictionary with keys sorted.

        :param data: The dictionary to sort.
        :type data: dict
        :return: A new dictionary with sorted keys.
        :rtype: dict
        """
        return {k: data[k] for k in sorted(data.keys())}


__all__ = [
    "SmarterHelperMixin",
]
