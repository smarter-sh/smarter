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
from smarter.common.utils import (
    bool_environment_variable as utils_bool_environment_variable,
)
from smarter.common.utils import camel_to_snake as utils_camel_to_snake
from smarter.common.utils import camel_to_snake_dict as utils_camel_to_snake_dict
from smarter.common.utils import dict_is_contained_in as utils_dict_is_contained_in
from smarter.common.utils import dict_is_subset as utils_dict_is_subset
from smarter.common.utils import (
    generate_fernet_encryption_key as utils_generate_fernet_encryption_key,
)
from smarter.common.utils import get_readonly_csv_file as utils_get_readonly_csv_file
from smarter.common.utils import get_readonly_yaml_file as utils_get_readonly_yaml_file
from smarter.common.utils import mask_string as util_mask_string
from smarter.common.utils import mask_string as utils_mask_string
from smarter.common.utils import pascal_to_snake as utils_pascal_to_snake
from smarter.common.utils import recursive_sort_dict as utils_recursive_sort_dict
from smarter.common.utils import rfc1034_compliant_str as utils_rfc1034_compliant_str
from smarter.common.utils import (
    rfc1034_compliant_to_snake as utils_rfc1034_compliant_to_snake,
)
from smarter.common.utils import (
    smarter_build_absolute_uri as utils_smarter_build_absolute_uri,
)
from smarter.common.utils import snake_case as utils_snake_case
from smarter.common.utils import snake_to_camel as utils_snake_to_camel
from smarter.common.utils import to_snake_case as utils_to_snake_case
from smarter.lib import json

from .logger import logger

if TYPE_CHECKING:
    from django.http import HttpRequest
MOCK_REGEX = re.compile(r"<MagicMock|<Mock|mock\\.MagicMock|mock\\.Mock", re.IGNORECASE)


class SmarterReadyState:
    """
    Constants representing the ready state of a Smarter class, formatted for logging.
    """

    READY = formatted_text_green("READY")
    NOT_READY = formatted_text_red("NOT_READY")


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
        return SmarterReadyState.READY

    @property
    def formatted_state_not_ready(self) -> str:
        """
        Returns the not-ready state formatted for logging.

        :return: The formatted not-ready state as a string.
        :rtype: str
        """
        return SmarterReadyState.NOT_READY

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

    def deserves_amnesty(self, slug: str) -> bool:
        """
        Determines if a given URL deserves amnesty based on the amnesty URLs list.

        :param slug: The URL path to check.
        :type slug: str
        :return: True if the URL deserves amnesty, False otherwise.
        :rtype: bool
        """
        slug = slug.lower()
        return any(amnesty_url in slug for amnesty_url in self.amnesty_urls)

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

    def bool_environment_variable(self, var_name: str, default: bool = False) -> bool:
        """
        Retrieves a boolean value from an environment variable.

        This method checks the specified environment variable and returns its value as a boolean.
        It recognizes common truthy values such as "true", "1", "yes", and "on". If the variable
        is not set or cannot be interpreted as a boolean, it returns the provided default value.

        :param var_name: The name of the environment variable to check.
        :type var_name: str
        :param default: The default boolean value to return if the environment variable is not set or invalid.
        :type default: bool
        :return: The boolean value of the environment variable or the default.
        :rtype: bool
        """
        return utils_bool_environment_variable(var_name=var_name, default=default)

    def to_snake_case(self, name: str) -> str:
        """
        Converts a string to snake_case.

        This method takes a string in any case format (e.g., camelCase, PascalCase, kebab-case)
        and converts it to snake_case, which is commonly used in Python for variable and function names.

        :param name: The string to convert to snake_case.
        :type name: str
        :return: The converted string in snake_case.
        :rtype: str
        """
        return utils_to_snake_case(name)

    def camel_to_snake(self, name: str) -> str:
        """
        Converts a camelCase or PascalCase string to snake_case.

        This method takes a string in camelCase or PascalCase format and converts it to snake_case.
        It is useful for standardizing naming conventions across different formats.

        :param name: The camelCase or PascalCase string to convert.
        :type name: str
        :return: The converted string in snake_case.
        :rtype: str
        """
        return str(utils_camel_to_snake(name))

    def camel_to_snake_dict(self, data: dict) -> dict:
        """
        Converts all keys in a dictionary from camelCase to snake_case.

        This method takes a dictionary with keys in camelCase format and returns a new dictionary
        with all keys converted to snake_case. The values are preserved as they are.

        :param data: The dictionary with camelCase keys to convert.
        :type data: dict
        :return: A new dictionary with keys converted to snake_case.
        :rtype: dict
        """
        return utils_camel_to_snake_dict(data)

    def dict_is_contained_in(self, dict1: dict, dict2: dict) -> bool:
        """
        Checks if one dictionary is contained within another.
        This method determines if all key-value pairs in `dict1` are present in `dict2`.

        :param dict1: The dictionary to check for containment.
        :type dict1: dict
        :param dict2: The dictionary to check against for containment.
        :type dict2: dict
        :return: True if `dict1` is contained in `dict2`, False otherwise.
        :rtype: bool
        """
        return utils_dict_is_contained_in(dict1=dict1, dict2=dict2)

    def dict_is_subset(self, small: dict, big: dict) -> bool:
        """
        Checks if one dictionary is a subset of another.

        This method determines if all key-value pairs in the `small` dictionary are present
        in the `big` dictionary. It returns True if the `small` dictionary is a subset of the `big` dictionary,
        and False otherwise.

        :param small: The dictionary to check as a subset.
        :type small: dict
        :param big: The dictionary to check against as a superset.
        :type big: dict
        :return: True if the `small` dictionary is a subset of the `big` dictionary, False otherwise.
        :rtype: bool
        """
        return utils_dict_is_subset(small=small, big=big)

    def generate_fernet_encryption_key(self) -> str:
        """
        Generates a Fernet encryption key.

        This method creates a new Fernet encryption key, which can be used for secure encryption and decryption of data.
        The generated key is returned as a URL-safe base64-encoded string.

        :return: A new Fernet encryption key.
        :rtype: str
        """
        return utils_generate_fernet_encryption_key()

    def get_readonly_csv_file(self, file_path: str):
        """
        Retrieves a read-only file object for a CSV file.

        This method opens the specified CSV file in read-only mode and returns a file object that can be used to read its contents.
        It ensures that the file is not modified during the reading process.

        :param file_path: The path to the CSV file to open.
        :type file_path: str
        :return: A read-only file object for the specified CSV file.
        :rtype: file
        """
        return utils_get_readonly_csv_file(file_path)

    def get_readonly_yaml_file(self, file_path: str):
        """
        Retrieves a read-only file object for a YAML file.

        This method opens the specified YAML file in read-only mode and returns a file object that can be used to read its contents.
        It ensures that the file is not modified during the reading process.

        :param file_path: The path to the YAML file to open.
        :type file_path: str
        :return: A read-only file object for the specified YAML file.
        :rtype: file
        """
        return utils_get_readonly_yaml_file(file_path)

    def snake_case(self, name: str) -> str:
        """
        Converts a string to snake_case.

        This method takes a string in any case format (e.g., camelCase, PascalCase, kebab-case)
        and converts it to snake_case, which is commonly used in Python for variable and function names.

        :param name: The string to convert to snake_case.
        :type name: str
        :return: The converted string in snake_case.
        :rtype: str
        """
        return utils_snake_case(name)

    def snake_to_camel(self, name: str) -> str:
        """
        Converts a snake_case string to camelCase.

        This method takes a string in snake_case format and converts it to camelCase.
        It is useful for standardizing naming conventions across different formats.

        :param name: The snake_case string to convert.
        :type name: str
        :return: The converted string in camelCase.
        :rtype: str
        """
        return str(utils_snake_to_camel(name))

    def pascal_to_snake(self, name: str) -> str:
        """
        Converts a PascalCase string to snake_case.

        This method takes a string in PascalCase format and converts it to snake_case.
        It is useful for standardizing naming conventions across different formats.

        :param name: The PascalCase string to convert.
        :type name: str
        :return: The converted string in snake_case.
        :rtype: str
        """
        return utils_pascal_to_snake(name)

    def rfc1034_compliant_str(self, name: str) -> str:
        """
        Converts a string to an RFC 1034 compliant format.

        This method takes a string and converts it to a format that complies with RFC 1034, which is commonly used for domain names.
        It replaces invalid characters with hyphens and ensures the resulting string is lowercase.

        :param name: The string to convert to RFC 1034 compliant format.
        :type name: str
        :return: The converted string in RFC 1034 compliant format.
        :rtype: str
        """
        return utils_rfc1034_compliant_str(name)

    def rfc1034_compliant_to_snake(self, name: str) -> str:
        """
        Converts an RFC 1034 compliant string to snake_case.

        This method takes a string in RFC 1034 compliant format and converts it to snake_case.
        It replaces hyphens with underscores and ensures the resulting string is lowercase.

        :param name: The RFC 1034 compliant string to convert.
        :type name: str
        :return: The converted string in snake_case.
        :rtype: str
        """
        return utils_rfc1034_compliant_to_snake(name)

    def recursive_sort_dict(self, data: dict) -> dict:
        """
        Recursively sorts a dictionary by its keys.

        This method takes a dictionary and returns a new dictionary with all keys sorted in ascending order.
        If any values are also dictionaries, they will be sorted recursively as well.

        :param data: The dictionary to sort.
        :type data: dict
        :return: A new dictionary with all keys sorted.
        :rtype: dict
        """
        return utils_recursive_sort_dict(data)


__all__ = [
    "SmarterHelperMixin",
]
