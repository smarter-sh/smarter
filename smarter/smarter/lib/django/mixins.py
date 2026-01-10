"""
Module for basic string conversions.
"""

import logging
import re
import warnings
from typing import Optional, Union

from smarter.common.exceptions import SmarterValueError
from smarter.common.helpers.console_helpers import formatted_text


logger = logging.getLogger(__name__)
logger_prefix = formatted_text(f"{__name__}.SmarterConverterMixin")


class SmarterConverterMixin:
    """
    A collection of static methods for converting strings and data structures between different naming conventions
    such as snake_case, camelCase, PascalCase, and RFC 1034-compliant names.

    This class provides utility functions to facilitate the conversion of strings, dictionary keys, and lists
    between various formats commonly used in programming and data representation.

    **Available Methods:**
    - ``snake_to_camel(data: Union[str, dict, list], convert_values: bool = False) -> Optional[Union[str, dict, list]]``
    - ``pascal_to_snake(name: str) -> str``
    - ``camel_to_snake(data: Union[str, dict, list]) -> Optional[Union[str, dict, list]]``
    - ``rfc1034_compliant_str(val) -> str``
    - ``rfc1034_compliant_to_snake(val) -> str``
    """

    def snake_to_camel(
        self, data: Union[str, dict, list], convert_values: bool = False
    ) -> Optional[Union[str, dict, list]]:
        """
        Converts snake_case strings, dictionary keys, or lists of such, to camelCase format.

        :param data: The input to convert. Can be a string, a dictionary (with snake_case keys), or a list containing strings or dictionaries.
        :type data: str, dict, or list

        :param convert_values: If ``True``, string values within dictionaries are also converted to camelCase. Default is ``False``.
        :type convert_values: bool, optional

        :return: The converted data in camelCase format. Returns a string, dictionary, or list, matching the input type.
        :rtype: Optional[Union[str, dict, list]]

        .. note::
            - For dictionaries, only keys are converted by default. If ``convert_values`` is set, string values are also converted.
            - Nested dictionaries and lists are processed recursively.

        .. warning::
            If the input is not a string, dictionary, or list, a ``SmarterValueError`` is raised.

        **Example usage:**

        .. code-block:: python

            from smarter.common.utils import snake_to_camel

            # Convert a string
            print(snake_to_camel("user_name"))  # Output: userName

            # Convert a dictionary
            data = {
                "user_name": "alice",
                "user_profile": {
                    "first_name": "Alice",
                    "last_name": "Smith"
                }
            }
            print(snake_to_camel(data))
            # Output: {'userName': 'alice', 'userProfile': {'firstName': 'Alice', 'lastName': 'Smith'}}

            # Convert a list of strings
            print(snake_to_camel(["first_name", "last_name"]))
            # Output: ['firstName', 'lastName']

            # Convert values as well
            data = {"user_name": "first_name"}
            print(snake_to_camel(data, convert_values=True))
            # Output: {'userName': 'firstName'}

        """
        logger.debug("%s.snake_to_camel()", logger_prefix)

        def convert(name: str) -> str:
            components = name.split("_")
            return components[0] + "".join(x.title() for x in components[1:])

        if isinstance(data, str):
            return convert(data)

        if isinstance(data, list):
            return [self.snake_to_camel(item, convert_values=convert_values) for item in data]

        if not isinstance(data, dict):
            raise SmarterValueError(f"Expected data to be a dict or list, got: {type(data)}")

        dictionary: dict = data if isinstance(data, dict) else {}
        retval = {}
        for key, value in dictionary.items():
            if isinstance(value, dict):
                value = self.snake_to_camel(data=value, convert_values=convert_values)
            new_key = convert(key)
            if convert_values:
                new_value = convert(value) if isinstance(value, str) else value
            else:
                new_value = value
            retval[new_key] = new_value
        return retval

    def pascal_to_snake(self, name: str) -> str:
        """
        Converts a PascalCase string to pascal_case snake_case format.

        :param name: The PascalCase string to convert.
        :type name: str

        :return: The converted string in snake_case format.
        :rtype: str

        .. note::
            - Spaces in the input string are replaced with underscores.
            - Multiple consecutive underscores are collapsed into a single underscore.

        **Example usage:**

        .. code-block:: python

            from smarter.common.utils import pascal_to_snake

            print(pascal_to_snake("UserProfile"))  # Output: user_profile
            print(pascal_to_snake("FirstName LastName"))  # Output: first_name_last_name

        """
        logger.debug("%s.pascal_to_snake()", logger_prefix)
        pattern = re.compile(r"(?<!^)(?=[A-Z])")
        return pattern.sub("_", name).lower()

    def camel_to_snake(self, data: Union[str, dict, list]) -> Optional[Union[str, dict, list]]:
        """
        Converts camelCase strings, dictionary keys, or lists of such, to snake_case format.

        :param data: The input to convert. Can be a string, a dictionary (with camelCase keys), or a list containing strings or dictionaries.
        :type data: str, dict, or list

        :return: The converted data in snake_case format. Returns a string, dictionary, or list, matching the input type.
        :rtype: Optional[Union[str, dict, list]]

        .. note::
            - For dictionaries, only keys are converted. Values are preserved as-is, except for nested dictionaries, which are also converted.
            - Spaces in keys are replaced with underscores.
            - Multiple consecutive underscores are collapsed into a single underscore.
            - Nested dictionaries and lists are processed recursively.

        .. warning::
            If the input is not a string, dictionary, or list, a ``SmarterValueError`` is raised.

        **Example usage:**

        .. code-block:: python

            from smarter.common.utils import camel_to_snake

            # Convert a string
            print(camel_to_snake("userName"))  # Output: user_name

            # Convert a dictionary
            data = {
                "userName": "alice",
                "userProfile": {
                    "firstName": "Alice",
                    "lastName": "Smith"
                }
            }
            print(camel_to_snake(data))
            # Output: {'user_name': 'alice', 'user_profile': {'first_name': 'Alice', 'last_name': 'Smith'}}

            # Convert a list of strings
            print(camel_to_snake(["firstName", "lastName"]))
            # Output: ['first_name', 'last_name']
        """
        logger.debug("%s.camel_to_snake()", logger_prefix)

        def convert(name: str):
            name = name.replace(" ", "_")
            name = name[0].lower() + name[1:] if name and len(name) > 1 and name[0].isupper() else name
            s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
            result = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()
            result = re.sub("_+", "_", result)
            return result

        if isinstance(data, str):
            return convert(data)
        if isinstance(data, list):
            return [self.camel_to_snake(item) for item in data]
        if not isinstance(data, dict):
            raise SmarterValueError(f"Expected data to be a dict or list, got: {type(data)}")
        dictionary: dict = data if isinstance(data, dict) else {}
        retval = {}
        for key, value in dictionary.items():
            if isinstance(value, dict):
                value = self.camel_to_snake(value)
            new_key = convert(key)
            retval[new_key] = value
        return retval

    def rfc1034_compliant_str(self, val) -> str:
        """
        Generates a RFC 1034-compliant name string suitable for use as a DNS label or resource identifier.

        :param val: The input string to convert to RFC 1034-compliant format.
        :type val: str

        :return: A string that is:
            - lower case
            - contains only alphanumeric characters and hyphens
            - starts and ends with an alphanumeric character
            - has a maximum length of 63 characters
        :rtype: str

        :raises SmarterValueError: If the input is not a string or is empty after conversion.

        .. note::
            - Underscores in the input are replaced with hyphens.
            - Invalid characters (anything other than a-z, 0-9, or '-') are removed.
            - Leading and trailing hyphens are stripped.
            - The result is truncated to 63 characters if necessary.

        .. warning::
            This function is intended for generating DNS-safe names. It does not guarantee uniqueness or suitability for all RFC 1034 use cases.

        **Example usage:**

        .. code-block:: python

            from smarter.common.utils import rfc1034_compliant_str

            # Basic usage
            print(rfc1034_compliant_str("My_ChatBot_2025"))  # Output: my-chatbot-2025

            # With special characters
            print(rfc1034_compliant_str("My@Bot!_Name"))  # Output: my-bot-name

            # With long input
            long_name = "ThisIsAReallyLongChatBotNameThatShouldBeTruncatedToSixtyThreeCharacters_Extra"
            print(rfc1034_compliant_str(long_name))  # Output: thisisareallylongchatbotnamethatshouldbetruncatedtosixtythreecharacters

        """
        logger.debug("%s.rfc1034_compliant_str()", logger_prefix)
        if not isinstance(val, str):
            raise SmarterValueError(f"Could not generate RFC 1034 compliant name from {type(val)}")
        # Replace underscores with hyphens
        label = val.lower().replace("_", "-")
        # Remove invalid characters
        label = re.sub(r"[^a-z0-9-]", "", label)
        # Remove leading/trailing hyphens
        label = label.strip("-")
        # Truncate to 63 characters
        if label:
            return label[:63]
        else:
            raise SmarterValueError("Could not generate RFC 1034 compliant name from empty string")

    def rfc1034_compliant_to_snake(self, val) -> str:
        """
        Converts a RFC 1034-compliant name (typically used for DNS labels or resource identifiers) to a more human-readable ``snake_case`` name.

        This function is useful for translating machine-friendly names (which use hyphens as word separators) into Pythonic identifiers (which use underscores).

        :param val: The RFC 1034-compliant name to convert. This should be a string containing only lowercase letters, numbers, and hyphens.
        :type val: str

        :return: The converted name in ``snake_case`` format, with hyphens replaced by underscores.
        :rtype: str

        :raises SmarterValueError: If the input is not a string.

        .. note::
            - Only hyphens are replaced; other characters are preserved.
            - The function does not validate that the input is strictly RFC 1034-compliant. It assumes the input is already sanitized.

        .. warning::
            This function does not handle conversion of other non-alphanumeric characters. If the input contains characters other than hyphens, underscores, letters, or numbers, they will remain unchanged.

        **Example usage:**

        .. code-block:: python

            from smarter.common.utils import rfc1034_compliant_to_snake

            # Basic conversion
            print(rfc1034_compliant_to_snake("my-chatbot-2025"))
            # Output: my_chatbot_2025

            # Input with no hyphens
            print(rfc1034_compliant_to_snake("simplelabel"))
            # Output: simplelabel

            # Input with multiple hyphens
            print(rfc1034_compliant_to_snake("this-is-a-test-label"))
            # Output: this_is_a_test_label

            # Input with invalid type
            try:
                rfc1034_compliant_to_snake(12345)
            except SmarterValueError as e:
                print(e)
            # Output: Could not convert RFC 1034 compliant name from <class 'int'>
        """
        logger.debug("%s.rfc1034_compliant_to_snake()", logger_prefix)
        if not isinstance(val, str):
            raise SmarterValueError(f"Could not convert RFC 1034 compliant name from {type(val)}")
        # Replace hyphens with underscores
        name = val.replace("-", "_")
        return name

    def mask_string(self, string: str, mask_char: str = "*", mask_length: int = 4, string_length: int = 8) -> str:
        """
        Masks a string by replacing all but the last ``mask_length`` characters with ``mask_char``.

        .. deprecated:: 0.10.0
            This function is deprecated and will be removed in a future release.
            Use Pydantic's ``SecretStr`` or other secure alternatives for string masking.

        :param string: The string to mask. If a ``bytes`` object is provided, it will be decoded to UTF-8.
        :type string: str or bytes

        :param mask_char: The character to use for masking. Default is ``'*'``.
        :type mask_char: str, optional

        :param mask_length: The number of characters at the end of the string to leave unmasked. Must be non-negative and less than or equal to the length of the string.
        :type mask_length: int, optional

        :param string_length: The total length of the returned masked string. If the original string is shorter, the result will be truncated or padded accordingly.
        :type string_length: int, optional

        :return: The masked string, with all but the last ``mask_length`` characters replaced by ``mask_char``. The result is truncated to ``string_length`` if necessary.
        :rtype: str

        :raises TypeError: If ``string`` is not a string or bytes.
        :raises ValueError: If ``mask_length`` or ``string_length`` are negative, or if ``mask_length`` exceeds the length of the string.

        .. note::

            - If the input string is shorter than ``mask_length``, the original string is returned.
            - If ``mask_length`` is greater than ``string_length``, it is reduced to ``string_length``.


        **Example usage:**

        .. code-block:: python

            from smarter.common.utils import mask_string

            # Mask all but the last 4 characters
            masked = mask_string("supersecretpassword", mask_char="*", mask_length=4)
            print(masked)  # Output: *************word

            # Mask and truncate to 8 characters
            masked = mask_string("supersecretpassword", mask_char="#", mask_length=3, string_length=8)
            print(masked)  # Output: #####ord

            # Mask a short string
            masked = mask_string("abc", mask_length=4)
            print(masked)  # Output: abc

        """
        logger.debug("%s.mask_string()", logger_prefix)
        warnings.warn(
            "mask_string is deprecated and will be removed in a future release.", DeprecationWarning, stacklevel=2
        )
        if isinstance(string, bytes):
            decoded_string = string.decode("utf-8")
            string = decoded_string
        if not isinstance(string, str):
            raise TypeError("string must be a string")
        if len(string) <= mask_length:
            return string
        if mask_length < 0:
            raise ValueError("mask_length must be greater than or equal to 0")
        if string_length < 0:
            raise ValueError("string_length must be greater than or equal to 0")
        if mask_length > len(string):
            raise ValueError("mask_length must be less than or equal to the length of the string")
        if string_length > len(string):
            string_length = len(string)
        if mask_length > string_length:
            mask_length = string_length

        masked_string = (
            f"{f'{mask_char}' * (len(string) - mask_length)}{string[-mask_length:]}"
            if len(string) > mask_length
            else string
        )
        masked_string = masked_string[-string_length:] if len(masked_string) > string_length else masked_string
        return masked_string
