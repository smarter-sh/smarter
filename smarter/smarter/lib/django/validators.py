"""
Internal validation features. This module contains functions for validating various data types.
Before adding anything to this module, please first check if there is a built-in Python function
or a Django utility that can do the validation.

TODO: add `import validators` and study this library to see what can be removed and/or refactored here
      see https://python-validators.github.io/validators/
"""

import json
import logging
import re
import warnings
from urllib.parse import urlparse, urlunparse

import validators
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator, validate_email, validate_ipv4_address

from smarter.common.const import SmarterEnvironments
from smarter.common.exceptions import SmarterValueError


logger = logging.getLogger(__name__)


# pylint: disable=R0904
class SmarterValidator:
    """
    Class for validating various data types. Before adding anything to this class, please
    first check if there is a built-in Python function or a Django utility that can do the validation.
    """

    LOCAL_HOSTS = ["localhost", "127.0.0.1"]
    LOCAL_HOSTS += [host + ":8000" for host in LOCAL_HOSTS]
    LOCAL_HOSTS.append("testserver")

    LOCAL_URLS = [f"http://{host}" for host in LOCAL_HOSTS] + [f"https://{host}" for host in LOCAL_HOSTS]
    VALID_ACCOUNT_NUMBER_PATTERN = r"^\d{4}-\d{4}-\d{4}$"
    VALID_PORT_PATTERN = r"^[0-9]{1,5}$"
    VALID_URL_PATTERN = r"^(http|https)://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,6}(:[0-9]{1,5})?$"
    VALID_HOSTNAME_PATTERN = r"^(?!-)[A-Za-z0-9_-]{1,63}(?<!-)$"
    VALID_UUID_PATTERN = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    VALID_SESSION_KEY = r"^[a-fA-F0-9]{64}$"
    VALID_SEMANTIC_VERSION = r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(-(0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(\.(0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*)?(\+[0-9a-zA-Z-]+(\.[0-9a-zA-Z-]+)*)?$"
    VALID_URL_FRIENDLY_STRING = (
        r"^((http|https)\:\/\/)?[a-zA-Z0-9\.\/\?\:@\-_=#]+\.([a-zA-Z]){2,6}([a-zA-Z0-9\.\&\/\?\:@\-_=#])*$"
    )
    VALID_CLEAN_STRING = r"^(?!-)[A-Za-z0-9_-]{1,63}(?<!-)(\.[A-Za-z0-9_-]{1,63})*$"
    VALID_CLEAN_STRING_WITH_SPACES = r"^[\w\-\.~:\/\?#\[\]@!$&'()*+,;= %]+$"
    VALID_URL_ENDPOINT = r"^/[a-zA-Z0-9/_\-\{\}]+/$"  # NOTE: this allows placeholders like {id} in the url
    VALID_CAMEL_CASE = r"^[a-zA-Z0-9]+(?:[A-Z][a-z0-9]+)*$"
    VALID_SNAKE_CASE = r"^[a-z0-9]+(?:_[a-z0-9]+)*$"
    VALID_PASCAL_CASE = r"^[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]+)*$"

    @staticmethod
    def validate_camel_case(value: str) -> None:
        """Validate camel case format"""
        if not re.match(SmarterValidator.VALID_CAMEL_CASE, value):
            raise SmarterValueError(f"Invalid camel case {value}")
        if not value:
            raise SmarterValueError("Value cannot be empty")
        if not value[0].islower():
            raise SmarterValueError(f"Value must start with a lowercase letter: {value}")
        if not value[0].isalpha():
            raise SmarterValueError(f"Value must start with a letter: {value}")
        if not value[1:].isalnum():
            raise SmarterValueError(f"Value must be in camel case format: {value}")
        if not value[1:].isalpha():
            raise SmarterValueError(f"Value must be in camel case format: {value}")

    @staticmethod
    def is_valid_camel_case(value: str) -> bool:
        """Check if the value is valid camel case"""
        try:
            SmarterValidator.validate_camel_case(value)
            return True
        except SmarterValueError:
            return False

    @staticmethod
    def validate_snake_case(value: str) -> None:
        """Validate snake case format"""
        if not re.match(SmarterValidator.VALID_SNAKE_CASE, value):
            raise SmarterValueError(f"Invalid snake case {value}")
        if not value:
            raise SmarterValueError("Value cannot be empty")
        if not value[0].islower():
            raise SmarterValueError(f"Value must start with a lowercase letter: {value}")
        if not value[0].isalpha():
            raise SmarterValueError(f"Value must start with a letter: {value}")

    @staticmethod
    def is_valid_snake_case(value: str) -> bool:
        """Check if the value is valid snake case"""
        try:
            SmarterValidator.validate_snake_case(value)
            return True
        except SmarterValueError:
            return False

    @staticmethod
    def validate_pascal_case(value: str) -> None:
        """Validate pascal case format"""
        if not re.match(SmarterValidator.VALID_PASCAL_CASE, value):
            raise SmarterValueError(f"Invalid pascal case {value}")
        if not value:
            raise SmarterValueError("Value cannot be empty")
        if not value[0].isupper():
            raise SmarterValueError(f"Value must start with an uppercase letter: {value}")
        if not value[0].isalpha():
            raise SmarterValueError(f"Value must start with a letter: {value}")
        if not value[1:].islower():
            raise SmarterValueError(f"Value must be in pascal case format: {value}")
        if not value[1:].isalnum():
            raise SmarterValueError(f"Value must be in pascal case format: {value}")
        if not value[1:].isalpha():
            raise SmarterValueError(f"Value must be in pascal case format: {value}")

    @staticmethod
    def is_valid_pascal_case(value: str) -> bool:
        """Check if the value is valid pascal case"""
        try:
            SmarterValidator.validate_pascal_case(value)
            return True
        except SmarterValueError:
            return False

    @staticmethod
    def validate_json(value: str) -> None:
        """Validate JSON format"""
        try:
            if not isinstance(value, str):
                raise SmarterValueError("Value must be a string")
            if not value.strip():
                return
            json.loads(value)
        except (ValueError, TypeError) as e:
            raise SmarterValueError(f"Invalid JSON value {value}") from e

    @staticmethod
    def is_valid_json(value: str) -> bool:
        """Check if the value is valid JSON"""
        try:
            SmarterValidator.validate_json(value)
            return True
        except SmarterValueError:
            return False

    @staticmethod
    def validate_semantic_version(version: str) -> None:
        """Validate semantic version format (e.g., 1.12.1)"""
        if not re.match(SmarterValidator.VALID_SEMANTIC_VERSION, version):
            raise SmarterValueError(f"Invalid semantic version {version}")

    @staticmethod
    def is_valid_semantic_version(version: str) -> bool:
        """Check if the semantic version is valid"""
        try:
            SmarterValidator.validate_semantic_version(version)
            return True
        except SmarterValueError:
            return False

    @staticmethod
    def validate_is_not_none(value: str) -> None:
        """Validate that the value is not None"""
        if value is None:
            raise SmarterValueError("Value cannot be None")
        if not value:
            raise SmarterValueError("Value cannot be empty")

    @staticmethod
    def is_not_none(value: str) -> bool:
        """Check if the value is not None"""
        try:
            SmarterValidator.validate_is_not_none(value)
            return True
        except SmarterValueError:
            return False

    @staticmethod
    def validate_session_key(session_key: str) -> None:
        """Validate session key format"""
        if not re.match(SmarterValidator.VALID_SESSION_KEY, session_key):
            raise SmarterValueError(f"Invalid session key {session_key}")

    @staticmethod
    def validate_account_number(account_number: str) -> None:
        """Validate account number format"""
        if not re.match(SmarterValidator.VALID_ACCOUNT_NUMBER_PATTERN, account_number):
            raise SmarterValueError(f"Invalid account number {account_number}")

    @staticmethod
    def validate_domain(domain: str) -> None:
        """Validate domain format"""
        if domain not in SmarterValidator.LOCAL_HOSTS + [None, ""]:
            SmarterValidator.validate_hostname(domain.split(":")[0])
            SmarterValidator.validate_url("http://" + domain)

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
        if not port.isdigit():
            raise SmarterValueError(f"Port must be numeric: {port}")
        port_num = int(port)
        if not (0 <= port_num <= 65535):
            raise SmarterValueError(f"Port out of range (0-65535): {port}")

    @staticmethod
    def validate_url(url: str) -> None:
        """Validate URL format"""
        valid_protocols = ["http", "https"]
        if not url:
            raise SmarterValueError(f"Invalid url {url}")
        try:
            if any(local_url in url for local_url in SmarterValidator.LOCAL_URLS):
                return
        except TypeError:
            pass
        try:
            validator = URLValidator(schemes=valid_protocols)
            validator(url)
            parsed = urlparse(url)
            if parsed.hostname:
                SmarterValidator.validate_hostname(parsed.hostname)
        except ValidationError as e:
            parsed = urlparse(url)
            if parsed.scheme not in valid_protocols:
                raise SmarterValueError(f"Invalid url protocol {parsed.scheme}") from e
            if all([parsed.scheme, parsed.netloc]) or url.startswith("localhost"):
                return
            if SmarterValidator.is_valid_ip(url):
                return
            if validators.url(url):
                parsed = urlparse(url)
                if parsed.scheme in valid_protocols:
                    return
            raise SmarterValueError(f"Invalid url {url}") from e

    @staticmethod
    def validate_hostname(hostname: str) -> None:
        """Validate hostname format"""
        if ":" in hostname:
            hostname, port = hostname.split(":")
            if not port.isdigit() or not 0 <= int(port) <= 65535:
                raise SmarterValueError(f"Invalid port {port}")
        if len(hostname) > 255:
            raise SmarterValueError(f"Invalid hostname {hostname}")
        if hostname[-1] == ".":
            hostname = hostname[:-1]  # strip exactly one dot from the right, if present
        allowed = re.compile(SmarterValidator.VALID_HOSTNAME_PATTERN, re.IGNORECASE)
        if all(allowed.match(x) for x in hostname.split(".")):
            return
        raise SmarterValueError(f"Invalid hostname {hostname}")

    @staticmethod
    def validate_uuid(uuid: str) -> None:
        """Validate UUID format"""
        if not re.match(SmarterValidator.VALID_UUID_PATTERN, uuid):
            raise SmarterValueError(f"Invalid UUID {uuid}")

    @staticmethod
    def validate_clean_string(v: str) -> None:
        """Validate clean string format"""
        if not re.match(SmarterValidator.VALID_CLEAN_STRING, v):
            raise SmarterValueError(f"Invalid clean string {v}")

    @staticmethod
    def validate_http_request_header_key(key: str) -> None:
        """
        Validate HTTP request header key format
        HTTP header name must be ASCII and cannot contain special characters like ()<>@,;:\"/[]?={} \t
        """
        if not key.isascii() or not re.match(r"^[!#$%&'*+\-.^_`|~0-9a-zA-Z]+$", key):
            raise SmarterValueError("Header name contains invalid characters or is not ASCII.")

    @staticmethod
    def validate_http_request_header_value(value: str) -> None:
        """
        Validate HTTP request header value format
        HTTP header value must not contain control characters like \n or \r
        """
        if not re.match(r"^[\t\x20-\x7E\x80-\xFF]*$", value):
            raise SmarterValueError("Header value contains invalid characters (e.g., control characters).")

    # --------------------------------------------------------------------------
    # boolean helpers
    # --------------------------------------------------------------------------
    @staticmethod
    def is_valid_http_request_header_key(key: str) -> bool:
        """Check if HTTP request header key is valid"""
        try:
            SmarterValidator.validate_http_request_header_key(key)
            return True
        except SmarterValueError:
            return False

    @staticmethod
    def is_valid_http_request_header_value(value: str) -> bool:
        """Check if HTTP request header value is valid"""
        try:
            SmarterValidator.validate_http_request_header_value(value)
            return True
        except SmarterValueError:
            return False

    @staticmethod
    def is_valid_session_key(session_key: str) -> bool:
        try:
            SmarterValidator.validate_session_key(session_key)
            return True
        except SmarterValueError:
            return False

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
    def is_valid_hostname(hostname: str) -> bool:
        try:
            SmarterValidator.validate_hostname(hostname)
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

    @staticmethod
    def is_valid_cleanstring(v: str) -> bool:
        try:
            SmarterValidator.validate_clean_string(v)
            return True
        except SmarterValueError:
            return False

    @staticmethod
    def is_valid_url_endpoint(url: str) -> bool:
        """
        Check if the URL is valid and ends with a trailing slash.
        example: /api/v1/tests/unauthenticated/list/
        """
        try:
            SmarterValidator.validate_url_endpoint(url)
            return True
        except SmarterValueError:
            return False

    # --------------------------------------------------------------------------
    # list helpers
    # --------------------------------------------------------------------------
    @staticmethod
    def validate_url_endpoint(url: str) -> None:
        """Validate URL endpoint format"""
        if not re.match(SmarterValidator.VALID_URL_ENDPOINT, url):
            raise SmarterValueError(f"URL endpoint '{url}' contains invalid characters.")
        if not url.startswith("/"):
            raise SmarterValueError(f"Invalid URL endpoint '{url}'. Should start with a leading slash")
        if not url.endswith("/"):
            raise SmarterValueError(f"Invalid URL endpoint '{url}'. Should end with a trailing slash")

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
    def urlify(url: str, scheme: str = None, environment: str = SmarterEnvironments.LOCAL) -> str:
        """
        ensure that URL starts with http:// or https://
        and ends with a trailing slash
        """
        logger.debug("urlify %s, %s", url, scheme)
        if not url:
            return None
        if scheme:
            warnings.warn("scheme is deprecated and will be removed in a future release.", DeprecationWarning)
        if scheme and scheme not in ["http", "https"]:
            SmarterValidator.raise_error(f"Invalid scheme {scheme}. Should be one of ['http', 'https']")
        scheme = "http" if environment == SmarterEnvironments.LOCAL else "https"
        if not "://" in url:
            url = f"{scheme}://{url}"
        parsed_url = urlparse(url)
        url = urlunparse((scheme, parsed_url.netloc, parsed_url.path, "", "", ""))
        url = SmarterValidator.trailing_slash(url)
        SmarterValidator.validate_url(url)
        return url

    @staticmethod
    def raise_error(msg: str) -> None:
        """Raise a SmarterValueError with the given message"""
        raise SmarterValueError(msg)
