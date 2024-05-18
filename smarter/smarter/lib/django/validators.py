"""
Internal validation features. This module contains functions for validating various data types.
Before adding anything to this module, please first check if there is a built-in Python function
or a Django utility that can do the validation.

TODO: add `import validators` and study this library to see what can be removed and/or refactored here
      see https://python-validators.github.io/validators/
"""

import logging
import re
from urllib.parse import urlparse, urlunparse

import validators
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator, validate_email, validate_ipv4_address

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
    VALID_HOSTNAME_PATTERN = r"^(?!-)[A-Z\d-]{1,63}(?<!-)$"
    VALID_UUID_PATTERN = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    VALID_SESSION_KEY = r"^[a-fA-F0-9]{64}$"
    VALID_SEMANTIC_VERSION = r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(-(0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(\.(0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*)?(\+[0-9a-zA-Z-]+(\.[0-9a-zA-Z-]+)*)?$"
    VALID_URL_FRIENDLY_STRING = (
        r"^((http|https)\:\/\/)?[a-zA-Z0-9\.\/\?\:@\-_=#]+\.([a-zA-Z]){2,6}([a-zA-Z0-9\.\&\/\?\:@\-_=#])*$"
    )
    VALID_CLEAN_STRING = r"^[\w\-\.~:\/\?#\[\]@!$&'()*+,;=%]+$"
    VALID_CLEAN_STRING_WITH_SPACES = r"^[\w\-\.~:\/\?#\[\]@!$&'()*+,;= %]+$"

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
        except TypeError:
            pass
        try:
            validator = URLValidator()
            validator(url)
        except ValidationError as e:
            parsed = urlparse(url)
            if all([parsed.scheme, parsed.netloc]) or url.startswith("localhost"):
                return
            if SmarterValidator.is_valid_ip(url):
                return
            if validators.url(url):
                return
            raise SmarterValueError(f"Invalid url {url}") from e

    @staticmethod
    def validate_hostname(hostname: str) -> None:
        """Validate hostname format"""
        if ":" in hostname:
            hostname, port = hostname.split(":")
            if not port.isdigit() or not (0 <= int(port) <= 65535):
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

    # --------------------------------------------------------------------------
    # boolean helpers
    # --------------------------------------------------------------------------
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
        logger.debug("urlify %s, %s", url, scheme)
        if not url:
            return None
        if not "://" in url:
            url = f"http://{url}"
        if not scheme and SmarterValidator.is_valid_url(url):
            retval = SmarterValidator.trailing_slash(url)
            logger.debug("urlify returning %s, %s", retval, scheme)
            return retval
        if scheme and scheme not in ["http", "https"]:
            SmarterValidator.raise_error(f"Invalid scheme {scheme}. Should be one of ['http', 'https']")

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
