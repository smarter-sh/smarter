"""
Smarter request mixin.

This is a helper class for the Django request object that resolves
known url patterns for Smarter chatbots. key features include:
- lazy loading of the user, account, user profile and session_key.
- meta data for describing chatbot characteristics.
- session_key generation.
- url parsing and validation.
- url pattern recognition.
- logging.
"""

import hashlib
import inspect
import logging
import re
import warnings
from datetime import datetime
from functools import cached_property
from typing import Any, Optional, Union
from unittest.mock import MagicMock
from urllib.parse import ParseResult, urlparse, urlunsplit

import tldextract
import yaml
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpRequest, QueryDict
from rest_framework.request import Request as RestFrameworkRequest

from smarter.apps.account.mixins import AccountMixin
from smarter.apps.account.utils import (
    account_number_from_url,
    get_cached_account,
    get_cached_admin_user_for_account,
)
from smarter.common.conf import settings as smarter_settings
from smarter.common.const import SMARTER_CHAT_SESSION_KEY_NAME
from smarter.common.exceptions import SmarterValueError
from smarter.common.helpers.url_helpers import session_key_from_url
from smarter.common.utils import (
    hash_factory,
    mask_string,
    rfc1034_compliant_to_snake,
    smarter_build_absolute_uri,
)
from smarter.lib import json
from smarter.lib.django import waffle
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper


# Match netloc: chatbot_name.account_number.api.environment_api_domain
netloc_pattern_named_url = re.compile(
    rf"^(?P<chatbot_name>[a-zA-Z0-9\-]+)\.(?P<account_number>\d{{4}}-\d{{4}}-\d{{4}})\.api\.{re.escape(smarter_settings.environment_platform_domain)}(:\d+)?$"
)


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.REQUEST_MIXIN_LOGGING) and level >= smarter_settings.log_level


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)

SmarterRequestType = Optional[Union[RestFrameworkRequest, HttpRequest, WSGIRequest, MagicMock]]
"""Type alias for all Smarter request types."""


class SmarterRequestMixin(AccountMixin):
    """
    Helper class for the Django request object that enforces authentication and
    provides lazy loading of the user, account, user profile, and session_key.

    This mixin works with any Django request object and any valid URL, but is designed
    as a helper class for Smarter ChatBot URLs.

    .. note::
        The request object is an optional positional argument due to Django view lifecycles,
        which do not recognize the request object until after class ``__init__()``.
        ``SmarterRequestMixin`` is included as a mixin in the Smarter base view classes.

    **Valid endpoints:**

    1. Root endpoints for named URLs (public or authenticated chats)
       (``self.is_chatbot_named_url == True``)

       - ``http://example.3141-5926-5359.api.localhost:8000/`` → ``smarter.apps.chatbot.api.v1.views.default.DefaultChatbotApiView``
       - ``http://example.3141-5926-5359.api.localhost:8000/config`` → ``smarter.apps.prompt.views.ChatConfigView``

    2. Authenticated sandbox endpoints (authenticated chats)
       (``self.is_chatbot_sandbox_url == True``)

       - ``http://localhost:8000/workbench/<str:name>/`` → ``smarter.apps.prompt.views.ChatAppWorkbenchView``
       - ``http://localhost:8000/workbench/<str:name>/config/`` → ``smarter.apps.prompt.views.ChatConfigView``

    3. smarter.sh/v1 endpoints (public or authenticated chats)
       (``self.is_chatbot_smarter_api_url == True``)

       - ``http://localhost:8000/api/v1/workbench/<int:chatbot_id>/chat/`` → ``smarter.apps.chatbot.api.v1.views.default.DefaultChatbotApiView``
       - ``http://localhost:8000/api/v1/workbench/<int:chatbot_id>/chat/config/`` → ``smarter.apps.prompt.views.ChatConfigView``

    4. Command-line interface API endpoints (authenticated chats)
       (``self.is_chatbot_cli_api_url == True``)

       - ``http://localhost:8000/api/v1/cli/chat/<str:name>/`` → ``smarter.apps.chatbot.api.v1.cli.views.nonbrokered.chat.ApiV1CliChatApiView``
       - ``http://localhost:8000/api/v1/cli/chat/config/<str:name>/`` → ``smarter.apps.chatbot.api.v1.cli.views.nonbrokered.chat_config.ApiV1CliChatConfigApiView``

    5. Other endpoints (possibly deprecated or unused)
       - ``http://localhost:8000/api/v1/chat/``

    **Example URLs:**

    - ``http://testserver``
    - ``http://localhost:8000/``
    - ``http://localhost:8000/docs/``
    - ``http://localhost:8000/dashboard/``
    - ``https://alpha.platform.smarter.sh/api/v1/workbench/1/chatbot/``
    - ``http://example.com/contact/``
    - ``http://localhost:8000/workbench/example/config/?session_key=...``
    - ``https://hr.3141-5926-5359.alpha.api.smarter.sh/``
    - ``https://hr.3141-5926-5359.alpha.api.smarter.sh/config/?session_key=...``
    - ``http://example.3141-5926-5359.api.localhost:8000/``
    - ``http://example.3141-5926-5359.api.localhost:8000/?session_key=...``
    - ``http://example.3141-5926-5359.api.localhost:8000/config/``
    - ``http://example.3141-5926-5359.api.localhost:8000/config/?session_key=...``
    - ``http://localhost:8000/api/v1/workbench/1/chat/``
    - ``http://localhost:8000/api/v1/cli/chat/smarter/?new_session=false&uid=mcdaniel``
    - ``https://hr.smarter.sh/``

    :ivar session_key: Unique identifier for a chat session, generated by :meth:`generate_session_key`.
    """

    __slots__ = (
        "_instance_id",
        "_smarter_request",
        "_timestamp",
        "_url",
        "_url_account_number",
        "_parse_result",
        "_params",
        "_session_key",
        "_data",
        "_cache_key",
    )

    # pylint: disable=W0613
    def __init__(self, request: Optional[HttpRequest], *args, **kwargs):
        self._instance_id = id(self)
        self._smarter_request: Optional[HttpRequest] = request
        self._timestamp = datetime.now()
        self._url: Optional[str] = None
        self._url_account_number: Optional[str] = None
        self._parse_result: ParseResult
        self._params: Optional[QueryDict] = None
        self._session_key: Optional[str] = kwargs.pop("session_key") if "session_key" in kwargs else None
        self._data: Optional[dict] = None
        self._cache_key: Optional[str] = None

        if request:
            self.smarter_request = request
        else:
            logger.debug(
                "%s.__init__() - request is None. SmarterRequestMixin will be partially initialized. This might affect request processing.",
                self.formatted_class_name,
            )
            super().__init__(request, *args, api_token=self.api_token, **kwargs)
        if self.smarter_request:
            self.smarter_request.user = self.user

    def init(self, request: HttpRequest, *args, **kwargs):
        """
        Handles initializations that require a valid request.

        This method is called from ``__init__()`` if the request object is passed.
        It is also called from the ``smarter_request`` setter.

        Args:
            request (HttpRequest): Django HttpRequest object.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Raises:
            SmarterValueError: If the request URL is missing or invalid.

        Example::

            from smarter.lib.django.request import SmarterRequestMixin

            class Foo(SmarterRequestMixin):
                pass

            foo = Foo(request)
            foo.init(request)
        """
        url = smarter_build_absolute_uri(self.smarter_request) if self.smarter_request else None

        logger.info(
            "%s.init() - initializing with request=%s, args=%s, kwargs=%s", self.formatted_class_name, url, args, kwargs
        )

        if url is None:
            raise SmarterValueError(
                f"{self.formatted_class_name}.__init__() - request url is None or empty. request={request}"
            )

        self._parse_result = urlparse(url)
        if not self._parse_result.scheme or not self._parse_result.netloc:
            raise SmarterValueError(f"{self.formatted_class_name} - request url is not a valid URL. url={url}")

        # rebuild the url minus any query parameters
        # example:
        # a request url like https://hr.3141-5926-5359.alpha.api.smarter.sh/config/?session_key=38486326c21ef4bcb7e7bc305bdb062f16ee97ed8d2462dedb4565c860cd8ecc
        # will return https://hr.3141-5926-5359.alpha.api.smarter.sh/config/
        self._url = urlunsplit((self._parse_result.scheme, self._parse_result.netloc, self._parse_result.path, "", ""))
        self._url = SmarterValidator.urlify(self._url)

        super().__init__(request, *args, api_token=self.api_token, **kwargs)

        logger.info(
            "%s.init() - initializing with instance_id=%s, request=%s, args=%s, kwargs=%s auth_header=%s user_profile=%s, account=%s",
            self.formatted_class_name,
            self._instance_id,
            request,
            args,
            kwargs,
            request.META.get("HTTP_AUTHORIZATION") if request and hasattr(request, "META") else None,
            self.user_profile if self.user_profile else None,
            self.account if self.account else None,
        )

        if isinstance(self._session_key, str):
            SmarterValidator.validate_session_key(self._session_key)
            logger.info(
                "%s.init() - session_key is set to %s from kwargs",
                self.formatted_class_name,
                self._session_key,
            )

        if self._parse_result and self.is_chatbot_named_url:
            account_number = account_number_from_url(self.url)
            if account_number:
                self._url_account_number = account_number
                if self.account and self.account.account_number != account_number:
                    raise SmarterValueError(
                        f"account number from url ({account_number}) does not match existing account ({self.account.account_number})."
                    )

            if self.account and not self._user:
                logger.debug(
                    "%s.init() - account (%s) is set but user is not.",
                    self.formatted_class_name,
                    self.account,
                )

        self.eval_chatbot_url()

        if self.is_requestmixin_ready:
            self.helper_logger(
                f"init() {self._instance_id} initialized successfully url={self.url}, session_key={self.session_key}, user={self.user_profile}"
            )
        else:
            msg = f"{self.formatted_class_name}.init() - request {self._instance_id} is not ready. request={self.smarter_request}"
            logger.warning(msg)

        logger.info("SmarterRequestMixin().init() - finished %s", self.dump())

    def invalidate_cached_properties(self):
        """
        Invalidates all cached properties on the instance to force re-evaluation.

        This method removes all attributes cached by `@cached_property` decorators
        from the instance's `__dict__`. It is useful for testing or when the request
        object changes and you need to ensure that all dependent properties are recalculated.

        Example::

            from smarter.lib.django.request import SmarterRequestMixin

            class Foo(SmarterRequestMixin):
                pass

            foo = Foo(request)
            foo.invalidate_cached_properties(request)

        Raises:
            None
        """
        for cls in self.__class__.__mro__:
            for name, value in inspect.getmembers(cls):
                if isinstance(value, cached_property):
                    self.__dict__.pop(name, None)

    @property
    def smarter_request(self) -> SmarterRequestType:
        """
        Returns the current request object.

        This property is named to avoid potential name collisions in child classes.
        This property is preferred over standard Django request types in that
        it more elegantly resolves idiosyncratic usage like Unit tests, Sphinx docs,
        and other non-standard request objects.

        Example::

            request_mixin = SmarterRequestMixin(request)
            req = request_mixin.smarter_request

        :return: The current request object.
        """
        return self._smarter_request

    @smarter_request.setter
    def smarter_request(self, request: SmarterRequestType):
        self._smarter_request = request
        if request is not None:
            logger.info(
                "%s.smarter_request setter called with request: %s",
                self.formatted_class_name,
                smarter_build_absolute_uri(request),
            )
            self.init(request)

    @cached_property
    def auth_header(self) -> Optional[str]:
        """Get the Authorization header from the request.

        :return: The value of the "Authorization" header if present, otherwise None.

        Example::

            request_mixin = SmarterRequestMixin(request)
            print(request_mixin.auth_header)

        :return: The Authorization header as a string, or None if not present.
        """
        return (
            self._smarter_request.META.get("HTTP_AUTHORIZATION")
            if self._smarter_request and hasattr(self._smarter_request, "META")
            else None
        )

    @cached_property
    def api_token(self) -> Optional[bytes]:
        """
        Get the API token from the request.

        :return: The API token as bytes if present in the Authorization header, otherwise None.

        Example::

            request_mixin = SmarterRequestMixin(request)
            token = request_mixin.api_token

        :return: The API token as bytes, or None if not present.
        """
        if isinstance(self.auth_header, str) and self.auth_header.startswith("Token "):
            return self.auth_header.split("Token ")[1].encode()
        return None

    @cached_property
    def qualified_request(self) -> bool:
        """
        A cursory screening of the WSGI request object to look for
        any disqualifying conditions that confirm this is not a
        request that we are interested in.

        The request is considered "qualified" if **all** of the following are true:

        - The request object (`self._smarter_request`) is present.
        - The URL path is present and non-empty.
        - The request does **not** originate from an internal AWS Kubernetes subnet (netloc starts with `192.168`).
        - The path is **not** in the list of `amnesty_urls`.
        - The path does **not** start with `/admin/`.
        - The path does **not** start with `/docs/`.
        - The path does **not** end with a static file extension (e.g., `.css`, `.js`, `.png`, `.jpg`, `.jpeg`, `.gif`, `.svg`, `.woff`, `.woff2`, `.ttf`, `.eot`, `.ico`).

        :return: True if the request passes all checks and is of interest, otherwise False.

        Example::

            # True case: a valid chatbot request
            request_mixin = SmarterRequestMixin(request)
            if request_mixin.qualified_request:
                print("This is a qualified chatbot request.")

            # False case: a static asset or admin/docs request
            static_request = SmarterRequestMixin(static_asset_request)
            if not static_request.qualified_request:
                print("This request is not of interest.")

        """
        if not self._smarter_request:
            return False
        path = self._parse_result.path if self._parse_result else None
        if not path:
            return False

        if self.parsed_url and self.parsed_url.netloc and self.parsed_url.netloc[:7] == "192.168":
            # internal processes running in a AWS kubernetes internal subnet.
            # definitely not a chatbot request.
            return False

        if path in self.amnesty_urls:
            return False
        if path.startswith("/admin/"):
            return False
        if path.startswith("/docs/"):
            return False

        static_extensions = [
            ".css",
            ".js",
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".svg",
            ".woff",
            ".woff2",
            ".ttf",
            ".eot",
            ".ico",
        ]
        if any(path.endswith(ext) for ext in static_extensions):
            return False

        return True

    @property
    def url(self) -> str:
        """
        The string representation of the ParseResult object stored in _parse_result.

        :return: The URL as a string.

        Example::

            request_mixin = SmarterRequestMixin(request)
            url_str = request_mixin.url
            print(url_str)  # e.g., 'https://example.com/path/'

        """
        if not isinstance(self._parse_result, ParseResult):
            raise SmarterValueError(
                f"The URL has not been initialized as a ParseResult. Received type: {type(self._parse_result)}"
            )
        if self._url:
            return self._url

        logger.error(
            "%s.url() property was accessed before it was initialized. request: %s",
            self.formatted_class_name,
            self.smarter_request,
        )
        raise SmarterValueError("The URL has not been initialized. Please check the request object.")

    @property
    def parsed_url(self) -> ParseResult:
        """
        Expose the private ParseResult URL object as a public property.

        :return: The parsed URL as a `ParseResult` object.

        Example::

            request_mixin = SmarterRequestMixin(request)
            parsed = request_mixin.parsed_url
            print(parsed.netloc)  # e.g., 'example.com'

        """
        if not isinstance(self._parse_result, ParseResult):
            raise SmarterValueError("The URL has not been initialized as a ParseResult.")
        return self._parse_result

    @property
    def url_path_parts(self) -> list:
        """
        Extract the path parts from the URL.

        :return: A list of strings representing each part of the URL path.

        Example::

            request_mixin = SmarterRequestMixin(request)
            parts = request_mixin.url_path_parts
            print(parts)  # e.g., ['api', 'v1', 'workbench', '1', 'chat']

        """
        return self.parsed_url.path.strip("/").split("/")

    @property
    def params(self) -> Optional[QueryDict]:
        """
        The query string parameters from the Django request object.

        This extracts the query string parameters from the request object and converts them to a dictionary.
        Used in child views to pass optional command-line parameters to the broker.

        :return: QueryDict containing the query string parameters.

        Example::

            request_mixin = SmarterRequestMixin(request)
            params = request_mixin.params
            print(params)  # e.g., {'session_key': 'abc123', 'uid': 'xyz'}

        """
        if not self._params:
            try:
                self._params = QueryDict(self.smarter_request.META.get("QUERY_STRING", ""))
            except AttributeError as e:
                logger.error(
                    "%s.params() internal error. Could not parse query string parameters: %s",
                    self.formatted_class_name,
                    e,
                )
                return None
        return self._params

    @property
    def uid(self) -> Optional[str]:
        """
        Unique identifier for the client.

        This is assumed to be a combination of the machine MAC address and the hostname.

        :return: The client UID as a string, or None if not available.

        Example::

            request_mixin = SmarterRequestMixin(request)
            uid = request_mixin.uid
            print(uid)  # e.g., '00:1A:2B:3C:4D:5E-myhost'

        """
        return self.params.get("uid") if isinstance(self.params, QueryDict) else None

    @cached_property
    def cache_key(self) -> Optional[str]:
        """
        Returns a cache key for the request.

        This is used to cache the chat request thread. The key is a combination of:
        - the class name,
        - authenticated username,
        - the chat name,
        - and the client UID.

        Currently used by the ApiV1CliChatConfigApiView and ApiV1CliChatApiView as a means of sharing the session_key.

        :param name: A generic object or resource name.
        :param uid: UID of the client, assumed to have been created from the machine MAC address and the hostname of the client.
        :return: A unique cache key string.

        Example::

            request_mixin = SmarterRequestMixin(request)
            key = request_mixin.cache_key
            print(key)  # e.g., 'a1b2c3d4e5f6...'

        """
        if self._cache_key:
            return self._cache_key

        if not self.smarter_request:
            logger.warning(
                "%s.cache_key() - request is None or not set. Cannot generate cache key.",
                self.formatted_class_name,
            )
            return None

        uid = self.uid or "unknown_uid"
        username = getattr(self.smarter_request, "user", "Anonymous") if self.smarter_request else "Anonymous"
        raw_string = f"{self.__class__.__name__}_{str(username)}_cache_key()_{str(uid)}"
        hash_object = hashlib.sha256()
        hash_object.update(raw_string.encode())
        hash_string = hash_object.hexdigest()
        self._cache_key = hash_string

        return self._cache_key

    @property
    def session_key(self) -> str:
        """
        Getter for the session_key property.

        The session_key is a unique identifier for a chat session.
        It is used to identify the chat session across multiple requests.
        If the session_key is not already set, it attempts to find it
        in the URL parameters. Barring that, it generates a new one.

        :return: The session key as a string.

        Example::

            request_mixin = SmarterRequestMixin(request)
            session_key = request_mixin.session_key
            print(session_key)  # e.g., '38486326c21ef4bcb7e7bc305bdb062f16ee97ed8d2462dedb4565c860cd8ecc'

        """
        if not self._session_key:
            self._session_key = self.find_session_key() or self.generate_session_key()
            SmarterValidator.validate_session_key(self._session_key)
            logger.info("%s.session_key() - setting session_key to %s", self.formatted_class_name, self._session_key)
        return self._session_key

    @property
    def smarter_request_chatbot_id(self) -> Optional[int]:
        """
        Extract the chatbot id from the URL.

        Example:
            http://localhost:8000/api/v1/workbench/1912/chat/config/

            return 1912

        :return: The chatbot id as an integer, or None if not found.
        """
        if not self.smarter_request:
            return None
        if not self.qualified_request:
            return None

        if self.is_chatbot_smarter_api_url:
            path_parts = self.url_path_parts
            return int(path_parts[3])

        if self.is_chatbot_named_url:
            # can't get from ChatBot bc of circular import
            return None

    @property
    def url_account_number(self) -> Optional[str]:
        """
        Extract the account number from the URL using the pattern defined in
        SmarterValidator.VALID_ACCOUNT_NUMBER_PATTERN.

        Example:
            http://example.3141-5926-5359.api.localhost:8000/config

            returns "3141-5926-5359"

        :return: The account number as a string, or None if not found.
        """
        if self._url_account_number:
            return self._url_account_number

        if not self.smarter_request:
            return None
        if not self.qualified_request:
            return None
        self._url_account_number = account_number_from_url(self.url)
        return self._url_account_number

    @cached_property
    def smarter_request_chatbot_name(self) -> Optional[str]:
        """
        Extract the chatbot name from the URL.

        Example:
            http://example.3141-5926-5359.api.localhost:8000/config

            returns "example"

        :return: The chatbot name as a string, or None if not found.
        """
        if not self.is_chatbot:
            return None

        # 1.) http://example.api.localhost:8000/config
        if self.is_chatbot_named_url and self.parsed_url is not None:
            netloc_parts = self.parsed_url.netloc.split(".") if self.parsed_url and self.parsed_url.netloc else None
            retval = netloc_parts[0] if netloc_parts else None
            retval = rfc1034_compliant_to_snake(retval) if isinstance(retval, str) else retval
            return retval

        # 2.) example: http://localhost:8000/workbench/<str:name>/config/
        if self.is_chatbot_sandbox_url:
            try:
                retval = self.url_path_parts[1]
                retval = rfc1034_compliant_to_snake(retval) if isinstance(retval, str) else retval
                return retval
            # pylint: disable=broad-except
            except Exception:
                logger.error(
                    "%s.smarter_request_chatbot_name() - failed to extract chatbot name from url: %s",
                    self.formatted_class_name,
                    self.url,
                )
        # 3.) http://localhost:8000/api/v1/workbench/<int:chatbot_id>
        # no name. nothing to do in this case.
        if self.is_chatbot_smarter_api_url:
            return None

        # 4.) http://localhost:8000/api/v1/cli/chat/config/<str:name>/
        #     http://localhost:8000/api/v1/cli/chat/<str:name>/
        if self.is_chatbot_cli_api_url:
            try:
                retval = self.url_path_parts[-1]
                retval = rfc1034_compliant_to_snake(retval) if isinstance(retval, str) else retval
                return retval
            # pylint: disable=broad-except
            except Exception:
                logger.error(
                    "%s.smarter_request_chatbot_name() - failed to extract chatbot name from url: %s",
                    self.formatted_class_name,
                    self.url,
                )

        return None

    @property
    def timestamp(self):
        """
        Create a consistent timestamp based on the time that this object was instantiated.

        :return: The timestamp as a `datetime` object.

        Example:
            ```python
            request_mixin = SmarterRequestMixin(request)
            ts = request_mixin.timestamp
            print(ts)  # e.g., 2025-12-01 12:34:56.789012
            ```
        """
        return self._timestamp

    @property
    def data(self) -> Optional[Union[dict, list, str]]:
        """
        Get the request body data as a dictionary, list or str.

        Used for setting the session_key.

        :return: The request body data as a dict, list, or str, or None if not available.

        Example:
            ```python
            request_mixin = SmarterRequestMixin(request)
            data = request_mixin.data
            print(data)  # e.g., {'session_key': 'abc123', ...}
            ```
        """
        if self._data:
            return self._data

        if not self.smarter_request:
            return None
        if not self.qualified_request:
            return None

        if not self.smarter_request:
            logger.warning("%s.data() - request is None or not set.", self.formatted_class_name)
            return {}
        try:
            body = self.smarter_request.body if hasattr(self.smarter_request, "body") else None
            if body is not None:
                body_str = body.decode("utf-8").strip()

                try:
                    self._data = json.loads(body_str) if isinstance(body_str, (str, bytearray, bytes)) else None
                    logger.info(
                        "%s.data() - initialized json from request body: %s",
                        self.formatted_class_name,
                        body_str,
                    )
                except json.JSONDecodeError:
                    try:
                        self._data = yaml.safe_load(body_str) if body_str else {}
                        logger.info(
                            "%s.data() - initialized json from parsed yaml request body: %s",
                            self.formatted_class_name,
                            body_str,
                        )
                    except yaml.YAMLError:
                        logger.error(
                            "%s.data() - failed to parse request body: %s",
                            self.formatted_class_name,
                            body_str,
                        )
                self._data = self._data or {}
        except json.JSONDecodeError:
            try:
                body = self.smarter_request.body if hasattr(self.smarter_request, "body") else None
                if body is not None:
                    body_str = body.decode("utf-8").strip()
                    self._data = yaml.safe_load(body_str) if body_str else {}
                    logger.info(
                        "%s.data() - initialized from parsed request body as yaml: %s",
                        self.formatted_class_name,
                        body_str,
                    )
            except yaml.YAMLError:
                logger.error(
                    "%s - failed to parse request body as JSON or YAML. request.body=%s",
                    self.formatted_class_name,
                    body_str,
                )

        self._data = self._data or {}
        self.helper_logger(f"request body json={self._data}")

        return self._data

    @cached_property
    def unique_client_string(self) -> str:
        """
        Generate a unique string based on several request attributes.

        This string is used for generating `session_key` and `client_key`.

        The unique string is composed of:
            - Account number
            - URL
            - User agent
            - IP address
            - Timestamp

        Returns:
            str: A unique string representing the client and request context.

        Example:
            ```python
            request_mixin = SmarterRequestMixin(request)
            unique_str = request_mixin.unique_client_string
            print(unique_str)
            ```
        """
        if not self.smarter_request:
            return "unique_client_string"
        account_number = self.account.account_number if self.account else "####-####-####"
        url = self.url if self.url else "http://localhost:8000/"
        timestamp = self.timestamp.isoformat()
        return f"{account_number}.{url}.{self.user_agent}.{self.ip_address}.{timestamp}"

    @property
    def client_key(self) -> Optional[str]:
        """
        (Deprecated) For smarter.sh/v1 API endpoints, the `client_key` is used to identify the client.

        Generates a unique client key based on the client's IP address, user agent, and the current datetime.

        Returns:
            str: A unique client key string.
        """
        warnings.warn(
            "The 'client_key' property is deprecated and will be removed in a future version.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.session_key

    @cached_property
    def ip_address(self) -> Optional[str]:
        """
        Get the client's IP address from the request object.

        This property attempts to extract the IP address from the request's META dictionary,
        using the "REMOTE_ADDR" key. If the IP address is not available, it returns None.

        Returns:
            Optional[str]: The client's IP address as a string, or None if not found.

        Example:
            ```python
            request_mixin = SmarterRequestMixin(request)
            ip = request_mixin.ip_address
            print(ip)  # e.g., '192.168.1.100'
            ```
        """
        if (
            self.smarter_request is not None
            and hasattr(self.smarter_request, "META")
            and isinstance(self.smarter_request.META, dict)
        ):
            return self.smarter_request.META.get("REMOTE_ADDR", "") or "ip_address"
        return None

    @cached_property
    def user_agent(self) -> Optional[str]:
        """
        Get the client's user agent string from the request object.

        This property attempts to extract the user agent from the request's META dictionary,
        using the "HTTP_USER_AGENT" key. If the user agent is not available, it returns a default value.

        Returns:
            Optional[str]: The client's user agent string, or None if not found.

        Example:
            ```python
            request_mixin = SmarterRequestMixin(request)
            ua = request_mixin.user_agent
            print(ua)  # e.g., 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)...'
            ```
        """
        if (
            self.smarter_request is not None
            and hasattr(self.smarter_request, "META")
            and isinstance(self.smarter_request.META, dict)
        ):
            # META is a dictionary-like object containing all HTTP headers
            # and other request metadata.
            # HTTP_USER_AGENT is the standard header for user agent information.
            # If it doesn't exist, we return a default value.
            # This is useful for debugging and logging purposes.
            return self.smarter_request.META.get("HTTP_USER_AGENT", "user_agent")
        return None

    @property
    def is_config(self) -> bool:
        """
        Returns True if the URL resolves to a config endpoint.

        Examples:
            http://testserver/api/v1/cli/chat/config/testc7098865f39202d5/
            http://localhost:8000/workbench/example/config/?session_key=1aeee4c1f183354247f43f80261573da921b0167c7c843b28afd3cb5ebba0d9a
            http://localhost:8000/api/v1/workbench/<int:chatbot_id>/chat/config/
            http://example.api.localhost:8000/config

        Returns:
            bool: True if the URL is a config endpoint, otherwise False.
        """
        return "config" in self.url_path_parts

    @cached_property
    def is_dashboard(self) -> bool:
        """
        Returns True if the URL resolves to a dashboard endpoint.

        Returns:
            bool: True if the URL is a dashboard endpoint, otherwise False.
        """
        if not self.smarter_request:
            return False
        return self.url_path_parts[-1] == "dashboard"

    @cached_property
    def is_workbench(self) -> bool:
        """
        Returns True if the URL resolves to a workbench endpoint.

        Returns:
            bool: True if the URL is a workbench endpoint, otherwise False.
        """
        if not self.smarter_request:
            return False
        return self.url_path_parts[-1] == "workbench"

    @cached_property
    def is_environment_root_domain(self) -> bool:
        """
        Returns True if the URL resolves to the environment root domain.

        Returns:
            bool: True if the URL is the environment root domain, otherwise False.
        """
        if not self.smarter_request:
            return False
        if not self.parsed_url:
            return False
        return self.parsed_url.netloc == smarter_settings.environment_platform_domain and self.parsed_url.path == "/"

    @cached_property
    def is_chatbot(self) -> bool:
        """
        Returns True if the URL resolves to a chatbot endpoint.

        Conditions are checked in a lazy sequence to avoid unnecessary processing.

        Examples:
            - http://localhost:8000/api/v1/prompt/1/chat/
            - http://localhost:8000/api/v1/cli/chat/example/
            - http://example.3141-5926-5359.api.localhost:8000/
            - http://localhost:8000/workbench/<str:name>/chat/
            - http://localhost:8000/api/v1/chatbots/1556/chat/

        Returns:
            bool: True if the URL is a chatbot endpoint, otherwise False.
        """

        return self.qualified_request and (
            self.is_chatbot_named_url
            or self.is_chatbot_sandbox_url
            or self.is_chatbot_smarter_api_url
            or self.is_chatbot_cli_api_url
        )

    @cached_property
    def is_smarter_api(self) -> bool:
        """
        Returns True if the URL is of the form http://localhost:8000/api/v1/.

        Examples:
            - path_parts: ['api', 'v1', 'chatbots', '1', 'chat']
            - http://api.localhost:8000/

        Returns:
            bool: True if the URL matches the smarter API pattern, otherwise False.
        """
        if not self.smarter_request:
            return False
        if not self.url:
            return False
        if "api" in self.url_path_parts:
            return True
        return False

    @cached_property
    def is_chatbot_smarter_api_url(self) -> bool:
        """
        Returns True if the URL is of the form:

            - http://localhost:8000/api/v1/workbench/1/chat/
              path_parts: ['api', 'v1', 'workbench', '<int:pk>', 'chat']

            - http://localhost:8000/api/v1/chatbots/1556/chat/
              path_parts: ['api', 'v1', 'chatbots', '<int:pk>', 'chat']

        Returns:
            bool: True if the URL matches a smarter API chatbot endpoint, otherwise False.
        """
        if not self.smarter_request:
            return False
        if not self.qualified_request:
            return False
        if not self.parsed_url:
            return False

        if len(self.url_path_parts) != 5:
            return False
        if self.url_path_parts[0] != "api":
            return False
        if self.url_path_parts[1] != "v1":
            return False
        if self.url_path_parts[2] not in ["workbench", "chatbots"]:
            return False
        if not self.url_path_parts[3].isnumeric():
            # expecting <int:pk> to be numeric: ['api', 'v1', 'workbench', '<int:pk>', 'chat']
            return False
        if self.url_path_parts[4] != "chat":
            # expecting 'chat' at the end of the path_parts: ['api', 'v1', 'workbench', '<int:pk>', 'chat']
            return False

        return True

    @cached_property
    def is_chatbot_cli_api_url(self) -> bool:
        """
        Returns True if the URL is of the form http://localhost:8000/api/v1/cli/chat/example/.

        The expected path parts are:
            ['api', 'v1', 'cli', 'chat', 'example']

        Returns:
            bool: True if the URL matches the CLI chatbot API pattern, otherwise False.
        """
        if not self.smarter_request:
            return False
        if not self.is_smarter_api:
            return False

        path_parts = self.url_path_parts
        try:
            if path_parts[2] != "cli":
                return False
            if path_parts[3] != "chat":
                return False
        except IndexError:
            return False

        return True

    @cached_property
    def is_chatbot_named_url(self) -> bool:
        """
        Returns True if the url is of the form:

            - https://example.3141-5926-5359.api.smarter.sh/
            - http://example.3141-5926-5359.api.localhost:8000/
            - http://example.3141-5926-5359.api.localhost:8000/config/

        Returns:
            bool: True if the URL matches the named chatbot pattern, otherwise False.
        """
        if not self.smarter_request:
            return False
        if not self.url:
            return False
        if not smarter_settings.environment_api_domain in self.url:
            return False
        account_number = self.url_account_number
        if account_number is not None:
            logger.info(
                "%s.is_chatbot_named_url() - url is a named url with account number: %s",
                self.formatted_class_name,
                account_number,
            )
            if self.account is None:
                # lazy load the account from the account number
                self.account = get_cached_account(account_number=account_number)
            return True

        # Accept root path or root with trailing slash
        if isinstance(self._parse_result, ParseResult) and self._parse_result.path not in ("", "/"):
            return False

        if isinstance(self._parse_result, ParseResult) and netloc_pattern_named_url.match(self._parse_result.netloc):
            return True

        return False

    @cached_property
    def is_chatbot_sandbox_url(self) -> bool:
        """
        Example URLs for chatbot sandbox endpoints.

        Examples:

            https://alpha.platform.smarter.sh/workbench/example/
            https://<environment_domain>/workbench/<name>
            path_parts: ['workbench', 'example']

            http://localhost:8000/workbench/<str:name>/chat/
            https://alpha.platform.smarter.sh/workbench/example/config/
            https://<environment_domain>/workbench/<name>/config/
            path_parts: ['workbench', 'example', 'config']

            http://localhost:8000/api/v1/prompt/1/chat/
            http://<environment_domain>/api/v1/prompt/<int:chatbot_id>/chat/

        Returns:
            bool: True if the URL matches a chatbot sandbox endpoint, otherwise False.
        """
        if not self.smarter_request:
            logger.warning("%s.is_chatbot_sandbox_url() - request is None or not set.", self.formatted_class_name)
            return False
        if not self.qualified_request:
            return False
        if not self._parse_result:
            logger.warning("%s.is_chatbot_sandbox_url() - url is None or not set.", self.formatted_class_name)
            return False

        # smarter api - http://localhost:8000/api/v1/prompt/1/chat/
        path_parts = self.url_path_parts
        if (
            len(path_parts) == 5
            and path_parts[0] == "api"
            and path_parts[1] == "v1"
            and path_parts[2] == "prompt"
            and path_parts[3].isnumeric()
            and path_parts[4] == "chat"
        ):
            return True

        # ---------------------------------------------------------------------
        # workbench urls: http://localhost:8000/workbench/<str:name>/chat/
        # ---------------------------------------------------------------------

        # valid path_parts:
        #   ['workbench', '<slug>', 'chat']
        #   ['workbench', '<slug>', 'config']
        if self.parsed_url.netloc != smarter_settings.environment_platform_domain:
            return False
        if len(path_parts) != 3:
            return False
        if path_parts[0] != "workbench":
            return False
        if not path_parts[1].isalpha():
            # expecting <slug> to be alpha: ['workbench', '<slug>', 'config']
            return False
        if path_parts[-1] in ["config", "chat"]:
            # expecting:
            #   ['workbench', '<slug>', 'chat']
            #   ['workbench', '<slug>', 'config']
            return True

        logger.warning(
            "%s.is_chatbot_sandbox_url() - could not verify whether url is a chatbot sandbox url: %s",
            self.formatted_class_name,
            path_parts,
        )
        return False

    @cached_property
    def is_default_domain(self) -> bool:
        """
        Returns True if the URL is the default domain for the environment.

        Example:
            api.alpha.platform.smarter.sh

        :return:
            bool: True if the URL is the default environment domain, otherwise False.
        """
        if not self.smarter_request:
            return False
        if not self.url:
            return False
        return smarter_settings.environment_api_domain in self.url

    @cached_property
    def path(self) -> Optional[str]:
        """
        Extracts the path from the URL.

        :return:
            Optional[str]: The path as a string, or None if not found.

        Examples:
            - https://hr.3141-5926-5359.alpha.api.smarter.sh/chatbot/
              returns '/chatbot/'
        """
        if not self.smarter_request:
            return None
        if not self.url:
            return None
        if not self.parsed_url:
            return None
        if self.parsed_url.path == "":
            return "/"
        return self.parsed_url.path

    @cached_property
    def root_domain(self) -> Optional[str]:
        """
        Extracts the root domain from the URL.

        :return: The root domain or None if not found.

        Example::

            request_mixin = SmarterRequestMixin(request)
            print(request_mixin.root_domain)
            # For 'https://hr.3141-5926-5359.alpha.api.smarter.sh/chatbot/' → 'smarter.sh'
            # For 'http://localhost:8000/' → 'localhost'

        """
        if not self.smarter_request:
            return None
        if not self.url:
            return None
        url = SmarterValidator.urlify(self.url, environment=smarter_settings.environment)  # type: ignore
        if url:
            extracted = tldextract.extract(url)
            if extracted.domain and extracted.suffix:
                return f"{extracted.domain}.{extracted.suffix}"
            if extracted.domain:
                return extracted.domain
        return None

    @cached_property
    def subdomain(self) -> Optional[str]:
        """
        Extracts the subdomain from the URL.

        :return: The subdomain or None if not found.

        Example::

            request_mixin = SmarterRequestMixin(request)
            sub = request_mixin.subdomain
            print(sub)  # e.g., 'hr.3141-5926-5359.alpha' for
                        # 'https://hr.3141-5926-5359.alpha.api.smarter.sh/chatbot/'
        """
        if not self.smarter_request:
            return None
        if not self.url:
            return None
        extracted = tldextract.extract(self.url)
        return extracted.subdomain

    @cached_property
    def api_subdomain(self) -> Optional[str]:
        """
        Extracts the API subdomain from the URL.

        :return: The API subdomain or None if not found.

        example::

            - https://hr.3141-5926-5359.alpha.api.smarter.sh/chatbot/
            returns 'hr'
        """
        if not self.smarter_request:
            return None
        if not self.is_chatbot:
            return None
        try:
            result = urlparse(self.url)
            domain_parts = result.netloc.split(".")
            return domain_parts[0]
        except TypeError:
            return None

    @cached_property
    def domain(self) -> Optional[str]:
        """
        Extracts the domain from the URL.

        :return: The domain or None if not found.

        examples::

            - https://hr.3141-5926-5359.alpha.api.smarter.sh/chatbot/
              returns 'hr.3141-5926-5359.alpha.api.smarter.sh'
        """
        if not self.smarter_request:
            return None
        if not self.parsed_url:
            return None
        return self.parsed_url.netloc if self.parsed_url else None

    @cached_property
    def formatted_class_name(self) -> str:
        """
        Returns the class name in a formatted string
        along with the name of this mixin.

        :return: Formatted class name string.
        """
        parent_class = super().formatted_class_name
        return f"{parent_class}.SmarterRequestMixin()"

    @cached_property
    def is_requestmixin_ready(self) -> bool:
        """
        Returns True if the request mixin is ready for processing.
        This is a convenience property to check if the request is ready.

        :return: True if the request mixin is ready, False otherwise.
        """
        # cheap and easy way to fail.
        if not isinstance(self._smarter_request, Union[HttpRequest, RestFrameworkRequest, WSGIRequest, MagicMock]):
            logger.debug(
                "%s.is_requestmixin_ready() - %s request is not a HttpRequest. Received %s. Cannot process request.",
                self.formatted_class_name,
                self._instance_id,
                type(self._smarter_request).__name__,
            )
            return False
        if not isinstance(self._parse_result, ParseResult):
            logger.debug(
                "%s.is_requestmixin_ready() - %s _parse_result is not a ParseResult. Received %s. Cannot process request.",
                self.formatted_class_name,
                self._instance_id,
                type(self._parse_result).__name__,
            )
            return False
        if not isinstance(self._url, str):
            logger.debug(
                "%s.is_requestmixin_ready() - %s _url is not a string. Received %s. Cannot process request.",
                self.formatted_class_name,
                self._instance_id,
                type(self._url).__name__,
            )
            return False
        return True

    @property
    def ready(self) -> bool:
        """
        returns True if the request is ready for processing.

        :return: True if the request is ready, False otherwise.

        """
        retval = bool(super().ready)
        if not retval:
            logger.debug(
                "%s.ready() - %s super().ready returned False. This might cause problems with other initializations.",
                self.formatted_class_name,
                self._instance_id,
            )
        return retval and self.is_requestmixin_ready

    # --------------------------------------------------------------------------
    # instance methods
    # --------------------------------------------------------------------------
    def get_cookie_value(self, cookie_name):
        """
        Retrieve the value of a cookie from the request object.

        :param request: Django HttpRequest object
        :param cookie_name: Name of the cookie to retrieve
        :return: Value of the cookie or None if the cookie does not exist
        """
        if self.smarter_request and self.smarter_request.COOKIES:
            return self.smarter_request.COOKIES.get(cookie_name)

    def generate_session_key(self) -> str:
        """
        Generate a session_key based on a unique string and the current datetime.

        :return: A unique session key string.
        """
        session_key = hash_factory(length=64)
        self.helper_logger(f"Generated new session key: {session_key}")
        return session_key

    def find_session_key(self) -> Optional[str]:
        """
        Returns the unique chat session key value for this request.

        The session_key is managed by the /config/ endpoint for the chatbot. The React app calls this endpoint at app initialization to get a JSON dict that includes, among other info, this session_key, which uniquely identifies the device and the individual chatbot session for the device.

        For subsequent chat prompt requests, the session_key is intended to be sent in the body of the request as a key-value pair, e.g. {"session_key": "1234567890"}.

        This method will also check the request headers and cookies for the session_key. The session key can be found in one of the following:

         - URL parameter: http://localhost:8000/workbench/example/config/?session_key=1aeee4c1f183354247f43f80261573da921b0167c7c843b28afd3cb5ebba0d9a
         - Request JSON body: {'session_key': '1aeee4c1f183354247f43f80261573da921b0167c7c843b28afd3cb5ebba0d9a'}
         - Request header: {'session_key': '1aeee4c1f183354247f43f80261573da921b0167c7c843b28afd3cb5ebba0d9a'}
         - Cookie
         - A session_key generator

        :return: The session key as a string, or None if not found.
        """
        if self._session_key:
            return self._session_key

        session_key: Optional[str]

        # this is our expected case. we look for the session key in the parsed url.
        session_key = session_key_from_url(self.url)
        if session_key:
            SmarterValidator.validate_session_key(session_key)
            self.helper_logger(
                f"session_key() - initialized from url: {session_key}",
            )
            return session_key

        # next, we look for it in the request body data.
        if isinstance(self.data, dict):
            session_key = self.data.get(SMARTER_CHAT_SESSION_KEY_NAME)
            session_key = session_key.strip() if isinstance(session_key, str) else None
            if session_key:
                SmarterValidator.validate_session_key(session_key)
                self.helper_logger(
                    f"session_key() - initialized from request body: {session_key}",
                )
                return session_key

        # next, we look for it in the cookie data.
        session_key = self.get_cookie_value(SMARTER_CHAT_SESSION_KEY_NAME)
        session_key = session_key.strip() if isinstance(session_key, str) else None
        if session_key:
            SmarterValidator.validate_session_key(session_key)
            self.helper_logger(
                f"session_key() - initialized from cookie data of the request object: {session_key}",
            )
            return session_key

        # finally, we look for it in the GET parameters.
        session_key = self.smarter_request.GET.get(SMARTER_CHAT_SESSION_KEY_NAME) if self.smarter_request else None
        session_key = session_key.strip() if isinstance(session_key, str) else None
        if session_key:
            SmarterValidator.validate_session_key(session_key)
            self.helper_logger(
                f"session_key() - initialized from the get() parameters of the request object: {session_key}",
            )
            return session_key

    def to_json(self) -> dict[str, Any]:
        """
        serializes the object.

        :return: A dictionary representation of the object.
        """
        if not self.is_requestmixin_ready:
            return super().to_json()
        return {
            "ready": self.ready,
            "url": self.url,
            "session_key": self.session_key,
            "auth_header": self.auth_header[:10] + "****" if self.auth_header else None,
            "api_token": mask_string(self.api_token.decode()) if self.api_token else None,
            "data": self.data,
            "chatbot_id": self.smarter_request_chatbot_id,
            "chatbot_name": self.smarter_request_chatbot_name,
            "is_smarter_api": self.is_smarter_api,
            "is_chatbot": self.is_chatbot,
            "is_chatbot_smarter_api_url": self.is_chatbot_smarter_api_url,
            "is_chatbot_named_url": self.is_chatbot_named_url,
            "is_chatbot_sandbox_url": self.is_chatbot_sandbox_url,
            "is_chatbot_cli_api_url": self.is_chatbot_cli_api_url,
            "is_default_domain": self.is_default_domain,
            "path": self.path,
            "root_domain": self.root_domain,
            "subdomain": self.subdomain,
            "api_subdomain": self.api_subdomain,
            "domain": self.domain,
            "timestamp": self.timestamp.isoformat(),
            "unique_client_string": self.unique_client_string,
            "client_key": self.client_key,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "parsed_url": str(self.parsed_url) if self.parsed_url else None,
            "request": self.smarter_request is not None,
            "qualified_request": self.qualified_request,
            "url_path_parts": self.url_path_parts,
            "params": self.params,
            "uid": self.uid,
            "cache_key": self.cache_key,
            "is_config": self.is_config,
            "is_dashboard": self.is_dashboard,
            "is_workbench": self.is_workbench,
            "is_environment_root_domain": self.is_environment_root_domain,
            **super().to_json(),
        }

    def eval_chatbot_url(self):
        """
        If we are a chatbot, based on analysis of the URL format
        then we need to make a follow up check of the user and account.

        Examples:

            - http://example.3141-5926-5359.api.localhost:8000/
            - https://alpha.platform.smarter.sh/api/v1/workbench/1/chatbot/
            - http://localhost:8000/api/v1/cli/chat/example/

        1.) For named urls, we extract the account number from the url,
            then we load the account and admin user for that account.

        2.) For smarter api urls, we would extract the chatbot id from the url,
            then we would load the chatbot, account, and admin user for that account.

        3.) For cli api urls, we would extract the chatbot name from the url,
            then we would load the chatbot, account, and admin user for that account.


        """
        if not self.is_chatbot:
            return
        if self.is_chatbot_named_url:
            # http://example.3141-5926-5359.api.localhost:8000/
            if not self.account:
                account_number = account_number_from_url(self.url)
                if account_number:
                    self.account = get_cached_account(account_number=account_number)  # type: ignore
            if self.account and not self.user:
                self.user = get_cached_admin_user_for_account(account=self.account)  # type: ignore
        if self.is_chatbot_smarter_api_url:
            # https://alpha.platform.smarter.sh/api/v1/workbench/1/chatbot/
            pass
        if self.is_chatbot_cli_api_url:
            # http://localhost:8000/api/v1/cli/chat/example/
            pass

    def helper_logger(self, message: str):
        """
        Create a log entry
        """
        logger.info("%s %s", self.formatted_class_name, message)

    def dump(self):
        """
        Dump the object to the console.
        """
        return json.dumps(self.to_json())
