"""Common classes"""

import re
from functools import cached_property
from typing import TYPE_CHECKING, Any, Optional, Union

import yaml

from smarter.common.exceptions import SmarterValueError
from smarter.common.helpers.console_helpers import (
    formatted_text,
    formatted_text_green,
    formatted_text_red,
)
from smarter.common.utils import (
    ConvertibleCaseType,
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
from smarter.common.utils import pascal_to_snake as utils_pascal_to_snake
from smarter.common.utils import recursive_sort_dict as utils_recursive_sort_dict
from smarter.common.utils import rfc1034_compliant_str as utils_rfc1034_compliant_str
from smarter.common.utils import (
    rfc1034_compliant_to_snake as utils_rfc1034_compliant_to_snake,
)
from smarter.common.utils import (
    smarter_build_absolute_uri as utils_smarter_build_absolute_uri,
)
from smarter.common.utils import snake_to_camel as utils_snake_to_camel
from smarter.common.utils import to_snake_case as utils_to_snake_case
from smarter.lib import json
from smarter.lib.cache import cache_results

from .logger import logger

if TYPE_CHECKING:
    from django.http import HttpRequest
MOCK_REGEX = re.compile(r"<MagicMock|<Mock|mock\\.MagicMock|mock\\.Mock", re.IGNORECASE)

FOREVER = 60 * 60 * 24 * 365  # 1 year in seconds


class SmarterReadyState:
    """
    Constants representing the ready state of a Smarter class, formatted for logging.
    """

    READY = formatted_text_green("READY")
    NOT_READY = formatted_text_red("NOT_READY")


class SmarterHelperMixin:
    """
    A generic mixin providing helper functions for Smarter classes.

    This mixin offers utility methods and properties commonly needed across Smarter classes, such as:

    - Standardized class name formatting for logging and display
    - URL amnesty lists for exempting certain endpoints from checks
    - JSON and YAML serialization/deserialization utilities
    - Data conversion and dictionary utilities
    - Secure string masking for logging sensitive information
    - Environment variable parsing helpers
    - Fernet encryption key generation
    - File handling utilities for CSV and YAML files
    - Case conversion utilities (snake_case, camelCase, PascalCase, RFC 1034)

    **Intended Usage:**
        Inherit this mixin in Smarter classes to gain access to a suite of common helper methods and properties, reducing code duplication and standardizing utility logic.

    **Examples:**

    .. code-block:: python

        class MyClass(SmarterHelperMixin):
            pass

        obj = MyClass()
        print(obj.formatted_class_name)
        print(obj.data_to_dict('{"foo": "bar"}'))
        print(obj.mask_string("my-secret-key"))

    **Main Features:**

    - ``formatted_class_name``: Returns the class name formatted for logging.
    - ``amnesty_urls``: List of URL paths exempt from certain checks.
    - ``deserves_amnesty(slug)``: Checks if a URL deserves amnesty.
    - ``smarter_build_absolute_uri(request)``: Safely builds an absolute URI from a Django HttpRequest.
    - ``mask_string(...)``: Masks sensitive strings for secure logging.
    - ``bool_environment_variable(var_name, default)``: Parses environment variables as booleans.
    - ``generate_fernet_encryption_key()``: Generates a Fernet encryption key.
    - ``data_to_dict(data)``: Converts JSON/YAML string or dict to dict.
    - ``sorted_dict(data)``: Returns a sorted copy of a dictionary.
    - ``dict_is_contained_in(dict1, dict2)``: Checks if one dict is contained in another.
    - ``dict_is_subset(small, big)``: Checks if one dict is a subset of another.
    - ``recursive_sort_dict(data)``: Recursively sorts a dictionary.
    - ``get_readonly_csv_file(file_path)``: Opens a CSV file in read-only mode.
    - ``get_readonly_yaml_file(file_path)``: Opens a YAML file in read-only mode.
    - Case conversion utilities: ``to_snake_case``, ``camel_to_snake``, ``camel_to_snake_dict``, ``snake_case``, ``snake_to_camel``, ``pascal_to_snake``, ``rfc1034_compliant_str``, ``rfc1034_compliant_to_snake``.


    """

    def __init__(self, *args, **kwargs):
        logger.debug("%s.__init__() - initializing with args=%s, kwargs=%s", self.formatted_class_name, args, kwargs)

    @cached_property
    def formatted_class_name(self) -> str:
        """
        Returns the class name formatted for logging.

        :return: The formatted class name as a string.
        :rtype: str

        """
        return formatted_text(self.__class__.__name__)

    @cached_property
    def unformatted_class_name(self) -> str:
        """
        Returns the raw class name without formatting.

        :return: The unformatted class name as a string.
        :rtype: str

        This is useful for logging or serialization where the plain class name is needed.
        """
        return self.__class__.__name__

    @cached_property
    def formatted_state_ready(self) -> str:
        """
        Returns the readiness state formatted for logging.

        :return: The formatted readiness state as a string.
        :rtype: str
        """
        return SmarterReadyState.READY

    @cached_property
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

    @cached_property
    def health_check_urls(self) -> list[str]:
        """
        Returns a list of URL paths that are considered health check endpoints.

        :return: List of health check URL path strings.
        :rtype: list[str]
        """
        return ["readiness", "healthz"]

    @cached_property
    def amnesty_urls(self) -> list[str]:
        """
        Returns a list of URLs that are exempt from certain checks.

        :return: List of URL path strings that are exempt.
        :rtype: list[str]
        """
        return self.health_check_urls + ["favicon.ico", "robots.txt", "sitemap.xml"]

    def deserves_amnesty(self, slug: str) -> bool:
        """
        Determines if a given URL deserves amnesty based on the amnesty URLs list.
        This excuses certain endpoints (like health checks) from select middleware
        checks.

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

        # pylint: disable=W0613
        @cache_results()
        def _smarter_build_absolute_uri(pk=id(self)):
            return utils_smarter_build_absolute_uri(request)

        return _smarter_build_absolute_uri()

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

    def generate_fernet_encryption_key(self) -> str:
        """
        Generates a Fernet encryption key.

        This method creates a new Fernet encryption key, which can be used for secure encryption and decryption of data.
        The generated key is returned as a URL-safe base64-encoded string.

        :return: A new Fernet encryption key.
        :rtype: str
        """
        return utils_generate_fernet_encryption_key()

    ###########################################################################
    # Dictionary utilities
    ###########################################################################
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

    ###########################################################################
    # File handling utilities
    ###########################################################################

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

    ###########################################################################
    # Case conversion utilities
    ###########################################################################

    def to_snake_case(self, obj: object) -> str:
        """
        Converts a string to snake_case.

        This method takes a string in any case format (e.g., camelCase, PascalCase, kebab-case)
        and converts it to snake_case, which is commonly used in Python for variable and function names.

        :param obj: The object to convert to snake_case.
        :type obj: object
        :return: The converted string in snake_case.
        :rtype: str
        """

        return utils_to_snake_case(obj)

    def camel_to_snake(self, data: ConvertibleCaseType) -> Any:
        """
        Converts a camelCase or PascalCase string to snake_case.

        This method takes a string in camelCase or PascalCase format and converts it to snake_case.
        It is useful for standardizing naming conventions across different formats.

        :param data: The camelCase or PascalCase string to convert.
        :type data: Union[str, dict, list]
        :return: The converted string in snake_case.
        :rtype: Optional[Union[str, dict, list]]
        """

        return utils_camel_to_snake(data)

    def camel_to_snake_dict(self, data: dict[str, object]) -> dict[str, object]:
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

    def snake_to_camel(self, data: ConvertibleCaseType, convert_values: bool = False) -> Any:
        """
        Converts a snake_case string to camelCase.

        This method takes a string in snake_case format and converts it to camelCase.
        It is useful for standardizing naming conventions across different formats.

        :param name: The snake_case string to convert.
        :type name: str
        :return: The converted string in camelCase.
        :rtype: Optional[Union[str, dict, list]]
        """

        return utils_snake_to_camel(data, convert_values=convert_values)

    def pascal_to_snake(self, name: ConvertibleCaseType) -> Any:
        """
        Converts a PascalCase string to snake_case.

        This method takes a string in PascalCase format and converts it to snake_case.
        It is useful for standardizing naming conventions across different formats.

        :param name: The PascalCase string to convert.
        :type name: ConvertibleCaseType
        :return: The converted string in snake_case.
        :rtype: Union[str, dict, list]
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


__all__ = [
    "SmarterHelperMixin",
]
