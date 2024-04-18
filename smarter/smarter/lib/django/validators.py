"""
Internal validation features. This module contains functions for validating various data types.
Before adding anything to this module, please first check if there is a built-in Python function
or a Django utility that can do the validation.
"""

import json
import logging
import re
from urllib.parse import urlparse, urlunparse

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator, validate_email, validate_ipv4_address

from smarter.common.const import OpenAIEndPoint, OpenAIMessageKeys, OpenAIObjectTypes
from smarter.common.exceptions import SmarterValueError


logger = logging.getLogger(__name__)


# pylint: disable=R0904
class SmarterValidator:
    """
    Class for validating various data types. Before adding anything to this class, please
    first check if there is a built-in Python function or a Django utility that can do the validation.
    """

    LOCAL_HOSTS = ["localhost", "127.0.0.1", "testserver"]
    LOCAL_URLS = [f"http://{host}" for host in LOCAL_HOSTS] + [f"https://{host}" for host in LOCAL_HOSTS]
    VALID_ACCOUNT_NUMBER_PATTERN = r"^\d{4}-\d{4}-\d{4}$"
    VALID_PORT_PATTERN = r"^[0-9]{1,5}$"
    VALID_URL_PATTERN = r"^(http|https)://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,6}(:[0-9]{1,5})?$"
    VALID_UUID_PATTERN = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"

    @staticmethod
    def validate_account_number(account_number: str) -> None:
        """Validate account number format"""
        if not re.match(SmarterValidator.VALID_ACCOUNT_NUMBER_PATTERN, account_number):
            raise SmarterValueError(f"Invalid account number {account_number}")

    @staticmethod
    def validate_domain(domain: str) -> None:
        """Validate domain format"""
        try:
            if domain not in SmarterValidator.LOCAL_HOSTS + [None, ""]:
                SmarterValidator.validate_url("http://" + domain)
        except SmarterValueError as e:
            raise SmarterValueError(f"Invalid domain {domain}") from e

    @staticmethod
    def validate_email(email: str) -> None:
        """Validate email format"""
        try:
            validate_email(email)
        except ValidationError as e:
            raise SmarterValueError(f"Invalid email {email}") from e

    @staticmethod
    def validate_ip(ip: str) -> None:
        """Validate IP address format"""
        try:
            validate_ipv4_address(ip)
        except ValidationError as e:
            raise SmarterValueError(f"Invalid IP address {ip}") from e

    @staticmethod
    def validate_port(port: str) -> None:
        """Validate port format"""
        if not re.match(SmarterValidator.VALID_PORT_PATTERN, port):
            raise SmarterValueError(f"Invalid port {port}")

    @staticmethod
    def validate_url(url: str) -> None:
        """Validate URL format"""
        try:
            if any(local_url in url for local_url in SmarterValidator.LOCAL_URLS):
                return
        except TypeError as e:
            raise SmarterValueError(f"Invalid url {url}") from e
        try:
            validator = URLValidator()
            validator(url)
        except ValidationError as e:
            if SmarterValidator.is_valid_ip(url):
                return
            raise SmarterValueError(f"Invalid url {url}") from e

    @staticmethod
    def validate_uuid(uuid: str) -> None:
        """Validate UUID format"""
        if not re.match(SmarterValidator.VALID_UUID_PATTERN, uuid):
            raise SmarterValueError(f"Invalid UUID {uuid}")

    # --------------------------------------------------------------------------
    # boolean helpers
    # --------------------------------------------------------------------------
    @staticmethod
    def is_valid_account_number(account_number: str) -> bool:
        """Check if account number is valid"""
        try:
            SmarterValidator.validate_account_number(account_number)
            return True
        except SmarterValueError:
            return False

    @staticmethod
    def is_valid_domain(domain: str) -> bool:
        """Check if domain is valid"""
        try:
            SmarterValidator.validate_domain(domain)
            return True
        except SmarterValueError:
            return False

    @staticmethod
    def is_valid_email(email: str) -> bool:
        """Check if email is valid"""
        try:
            SmarterValidator.validate_email(email)
            return True
        except SmarterValueError:
            return False

    @staticmethod
    def is_valid_ip(ip: str) -> bool:
        """Check if IP address is valid"""
        try:
            SmarterValidator.validate_ip(ip)
            return True
        except SmarterValueError:
            return False

    @staticmethod
    def is_valid_port(port: str) -> bool:
        try:
            SmarterValidator.validate_port(port)
            return True
        except SmarterValueError:
            return False

    @staticmethod
    def is_valid_url(url: str) -> bool:
        try:
            SmarterValidator.validate_url(url)
            return True
        except SmarterValueError:
            return False

    @staticmethod
    def is_valid_uuid(uuid: str) -> bool:
        try:
            SmarterValidator.validate_uuid(uuid)
            return True
        except SmarterValueError:
            return False

    # --------------------------------------------------------------------------
    # list helpers
    # --------------------------------------------------------------------------
    @staticmethod
    def validate_list_of_account_numbers(account_numbers: list) -> None:
        """Validate list of account numbers"""
        for account_number in account_numbers:
            SmarterValidator.validate_account_number(account_number)

    @staticmethod
    def validate_list_of_domains(domains: list) -> None:
        """Validate list of domains"""
        for domain in domains:
            SmarterValidator.validate_domain(domain)

    @staticmethod
    def validate_list_of_emails(emails: list) -> None:
        """Validate list of emails"""
        for email in emails:
            SmarterValidator.validate_email(email)

    @staticmethod
    def validate_list_of_ips(ips: list) -> None:
        """Validate list of IP addresses"""
        for ip in ips:
            SmarterValidator.validate_ip(ip)

    @staticmethod
    def validate_list_of_ports(ports: list) -> None:
        """Validate list of ports"""
        for port in ports:
            SmarterValidator.validate_port(port)

    @staticmethod
    def validate_list_of_urls(urls: list) -> None:
        """Validate list of URLs"""
        for url in urls:
            SmarterValidator.validate_url(url)

    @staticmethod
    def validate_list_of_uuids(uuids: list) -> None:
        """Validate list of UUIDs"""
        for uuid in uuids:
            SmarterValidator.validate_uuid(uuid)

    # --------------------------------------------------------------------------
    # utility helpers
    # --------------------------------------------------------------------------
    @staticmethod
    def base_domain(url: str) -> str:
        if not url:
            return None
        base_url = SmarterValidator.base_url(url)
        if not base_url:
            return None
        base_url = base_url.replace("http://", "").replace("https://", "")
        return base_url.rstrip("/")

    @staticmethod
    def base_url(url: str) -> str:
        if not url:
            return None
        url = SmarterValidator.urlify(url)
        SmarterValidator.validate_url(url)
        parsed_url = urlparse(url)
        unparsed_url = urlunparse((parsed_url.scheme, parsed_url.netloc, "", "", "", ""))
        return SmarterValidator.trailing_slash(unparsed_url)

    @staticmethod
    def trailing_slash(url: str) -> str:
        if not url:
            return None
        return url if url.endswith("/") else url + "/"

    @staticmethod
    def urlify(url: str, scheme: str = None) -> str:
        """ensure that URL starts with http:// or https://"""
        if not scheme and SmarterValidator.is_valid_url(url):
            return SmarterValidator.trailing_slash(url)
        if scheme and scheme not in ["http", "https"]:
            SmarterValidator.raise_error(f"Invalid scheme {scheme}. Should be one of ['http', 'https']")

        if not str:
            return None
        if not "://" in url:
            url = f"http://{url}"
        parsed_url = urlparse(url)
        scheme = scheme or parsed_url.scheme or "http"
        url = urlunparse((scheme, parsed_url.netloc, parsed_url.path, "", "", ""))
        url = SmarterValidator.trailing_slash(url)
        SmarterValidator.validate_url(url)
        return url

    @staticmethod
    def raise_error(msg: str) -> None:
        """Raise a SmarterValueError with the given message"""
        raise SmarterValueError(msg)


####################################################################################################
# Legacy openai validators
####################################################################################################


def validate_item(item, valid_items: list, item_type: str) -> None:
    """Ensure that item exists in valid_items"""
    if item not in valid_items:
        raise SmarterValueError(f"Item {item} not found in {item_type}: {valid_items}")


def validate_temperature(temperature: any) -> None:
    """Ensure that temperature is a float between 0 and 1"""
    try:
        float_temperature = float(temperature)
        if float_temperature < 0 or float_temperature > 1:
            raise SmarterValueError("temperature should be between 0 and 1")
    except SmarterValueError as exc:
        raise SmarterValueError("Temperature must be a float") from exc


def validate_max_tokens(max_tokens: any) -> None:
    """Ensure that max_tokens is an int between 1 and 2048"""
    if not isinstance(max_tokens, int):
        raise TypeError("max_tokens should be an int")

    if max_tokens < 1 or max_tokens > 2048:
        raise SmarterValueError("max_tokens should be between 1 and 2048")


def validate_endpoint(end_point: any) -> None:
    """Ensure that end_point is a valid endpoint based on the OpenAIEndPoint enum"""
    if not isinstance(end_point, str):
        raise TypeError(f"Invalid end_point '{end_point}'. end_point should be a string.")

    if end_point not in OpenAIEndPoint.all_endpoints:
        raise SmarterValueError(f"Invalid end_point {end_point}. Should be one of {OpenAIEndPoint.all_endpoints}")


def validate_object_types(object_type: any) -> None:
    """Ensure that object_type is a valid object type based on the OpenAIObjectTypes enum"""
    if not isinstance(object_type, str):
        raise TypeError(f"Invalid object_type '{object_type}'. object_type should be a string.")

    if object_type not in OpenAIObjectTypes.all_object_types:
        raise SmarterValueError(
            f"Invalid object_type {object_type}. Should be one of {OpenAIObjectTypes.all_object_types}"
        )


def validate_request_body(request_body) -> None:
    """See openai.chat.completion.request.json"""
    if not isinstance(request_body, dict):
        raise TypeError("request body should be a dict")


def validate_messages(request_body):
    """See openai.chat.completion.request.json"""
    if "messages" not in request_body:
        raise SmarterValueError("dict key 'messages' was not found in request body object")
    messages = request_body["messages"]
    if not isinstance(messages, list):
        raise SmarterValueError("dict key 'messages' should be a JSON list")
    for message in messages:
        if not isinstance(message, dict):
            raise SmarterValueError(f"invalid object type {type(message)} found in messages list")
        if "role" not in message:
            raise SmarterValueError(f"dict key 'role' not found in message {json.dumps(message, indent=4)}")
        if message["role"] not in OpenAIMessageKeys.all:
            raise SmarterValueError(
                f"invalid role {message['role']} found in message {json.dumps(message, indent=4)}. "
                f"Should be one of {OpenAIMessageKeys.all}"
            )
        if "content" not in message:
            raise SmarterValueError(f"dict key 'content' not found in message {json.dumps(message, indent=4)}")


def validate_completion_request(request_body) -> None:
    """See openai.chat.completion.request.json"""
    validate_request_body(request_body=request_body)
    if "model" not in request_body:
        raise SmarterValueError("dict key 'model' not found in request body object")
    if "temperature" not in request_body:
        raise SmarterValueError("dict key 'temperature' not found in request body object")
    if "max_tokens" not in request_body:
        raise SmarterValueError("dict key 'max_tokens' not found in request body object")
    validate_messages(request_body=request_body)


def validate_embedding_request(request_body) -> None:
    """See openai.embedding.request.json"""
    validate_request_body(request_body=request_body)
    if "input_text" not in request_body:
        raise SmarterValueError("dict key 'input_text' not found in request body object")
