# pylint: disable=C0302
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
from datetime import datetime
from functools import cached_property
from typing import Any, Optional, Union
from unittest.mock import MagicMock
from urllib.parse import ParseResult, urlparse

import tldextract
import yaml
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpRequest, QueryDict
from rest_framework.request import Request as RestFrameworkRequest

from smarter.apps.account.mixins import AccountMixin, UserType
from smarter.apps.account.models import Account, User, UserProfile
from smarter.apps.account.utils import (
    account_number_from_url,
    get_cached_account,
    get_cached_admin_user_for_account,
)
from smarter.common.conf import smarter_settings
from smarter.common.const import SMARTER_CHAT_SESSION_KEY_NAME
from smarter.common.exceptions import SmarterValueError
from smarter.common.helpers.console_helpers import (
    formatted_text,
    formatted_text_green,
    formatted_text_red,
)
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


# pylint: disable=W0613
def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.REQUEST_MIXIN_LOGGING)


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

       - ``http://example.3141-5926-5359.api.localhost:9357/`` → ``smarter.apps.chatbot.api.v1.views.default.DefaultChatbotApiView``
       - ``http://example.3141-5926-5359.api.localhost:9357/config`` → ``smarter.apps.prompt.views.ChatConfigView``

    2. Authenticated sandbox endpoints (authenticated chats)
       (``self.is_chatbot_sandbox_url == True``)

       - ``http://localhost:9357/workbench/<str:name>/`` → ``smarter.apps.prompt.views.ChatAppWorkbenchView``
       - ``http://localhost:9357/workbench/<str:name>/config/`` → ``smarter.apps.prompt.views.ChatConfigView``

    3. smarter.sh/v1 endpoints (public or authenticated chats)
       (``self.is_chatbot_smarter_api_url == True``)

       - ``http://localhost:9357/api/v1/workbench/<int:chatbot_id>/chat/`` → ``smarter.apps.chatbot.api.v1.views.default.DefaultChatbotApiView``
       - ``http://localhost:9357/api/v1/workbench/<int:chatbot_id>/chat/config/`` → ``smarter.apps.prompt.views.ChatConfigView``

    4. Command-line interface API endpoints (authenticated chats)
       (``self.is_chatbot_cli_api_url == True``)

       - ``http://localhost:9357/api/v1/cli/chat/<str:name>/`` → ``smarter.apps.chatbot.api.v1.cli.views.nonbrokered.chat.ApiV1CliChatApiView``
       - ``http://localhost:9357/api/v1/cli/chat/config/<str:name>/`` → ``smarter.apps.chatbot.api.v1.cli.views.nonbrokered.chat_config.ApiV1CliChatConfigApiView``

    5. Other endpoints (possibly deprecated or unused)
       - ``http://localhost:9357/api/v1/chat/``

    **Example URLs:**

    - ``http://testserver``
    - ``http://localhost:9357/``
    - ``http://localhost:9357/docs/``
    - ``http://localhost:9357/dashboard/``
    - ``https://alpha.platform.smarter.sh/api/v1/workbench/1/chatbot/``
    - ``http://example.com/contact/``
    - ``http://localhost:9357/workbench/example/config/?session_key=...``
    - ``https://hr.3141-5926-5359.alpha.api.example.com/``
    - ``https://hr.3141-5926-5359.alpha.api.example.com/config/?session_key=...``
    - ``http://example.3141-5926-5359.api.localhost:9357/``
    - ``http://example.3141-5926-5359.api.localhost:9357/?session_key=...``
    - ``http://example.3141-5926-5359.api.localhost:9357/config/``
    - ``http://example.3141-5926-5359.api.localhost:9357/config/?session_key=...``
    - ``http://localhost:9357/api/v1/workbench/1/chat/``
    - ``http://localhost:9357/api/v1/cli/chat/smarter/?new_session=false&uid=mcdaniel``
    - ``https://hr.smarter.sh/``

    :ivar session_key: Unique identifier for a chat session, generated by :meth:`generate_session_key`.
    """

    __slots__ = (
        "_instance_id",
        "_smarter_request",
        "_smarter_request_user",
        "_timestamp",
        "_url",
        "_url_account_number",
        "_parsed_url",
        "_params",
        "_session_key",
        "_data",
        "_cache_key",
    )

    # pylint: disable=W0613
    def __init__(self, *args, request: Optional[HttpRequest] = None, **kwargs):
        self._instance_id = id(self)
        self._smarter_request: Optional[HttpRequest] = None
        self._smarter_request_user: Optional[UserType] = None
        self._timestamp = datetime.now()
        self._url: Optional[str] = None
        self._url_account_number: Optional[str] = None
        self._parsed_url: ParseResult = None
        self._params: Optional[QueryDict] = None
        self._session_key: Optional[str] = kwargs.pop("session_key") if "session_key" in kwargs else None
        self._data: Optional[dict] = None
        self._cache_key: Optional[str] = None

        stack = inspect.stack()
        caller = stack[1]
        module_name = caller.frame.f_globals["__name__"]
        logger.debug(
            "%s.__init__() - called by %s with request=%s, args=%s, kwargs=%s",
            self.request_mixin_logger_prefix,
            formatted_text(module_name),
            request,
            args,
            kwargs,
        )
        request = request or next(
            (req for req in args if isinstance(req, (RestFrameworkRequest, HttpRequest, WSGIRequest, MagicMock))), None
        )
        # ---------------------------------------------------------------------
        # the following reassignments are not necessarily technically required,
        # but they make it explicit what arguments are being passed to
        # the parent AccountMixin class, and this gives us an opportunity to
        # log the values for debugging purposes.
        # ---------------------------------------------------------------------
        user = kwargs.pop("user", None) or next((user for user in args if isinstance(user, User)), None)
        if user:
            logger.debug(
                "%s.__init__() - found a user argument: %s",
                self.request_mixin_logger_prefix,
                user,
            )
            self._smarter_request_user = user
        user_profile = kwargs.pop("user_profile", None) or next(
            (user_profile for user_profile in args if isinstance(user_profile, UserProfile)), None
        )
        if user_profile:
            logger.debug(
                "%s.__init__() - found a user_profile argument: %s",
                self.request_mixin_logger_prefix,
                user_profile,
            )
        account = kwargs.pop("account", None) or next(
            (account for account in args if isinstance(account, Account)), None
        )
        if account:
            logger.debug(
                "%s.__init__() - found an account argument: %s",
                self.request_mixin_logger_prefix,
                account,
            )
        self._smarter_request = request
        AccountMixin.__init__(
            self,
            request=request,
            account=account,
            user=self._smarter_request_user,
            user_profile=user_profile,
            api_token=self.api_token,
        )
        if request:
            self.smarter_request = request
        else:
            logger.debug(
                "%s.__init__() - no request provided. Cannot initialize. Calling super().__init__() with args=%s, kwargs=%s",
                self.request_mixin_logger_prefix,
                args,
                kwargs,
            )
            super().__init__(*args, **kwargs)
            return None

        if not self.smarter_request:
            raise SmarterValueError(
                f"{self.request_mixin_logger_prefix}.__init__() - did not find a request object. SmarterRequestMixin cannot be initialized."
            )

        if self.parsed_url and self.is_chatbot_named_url:
            account_number = self.url_account_number
            if account_number:
                self._url_account_number = account_number
                if self.account and self.account.account_number != account_number:
                    raise SmarterValueError(
                        f"account number from url ({account_number}) does not match existing account ({self.account.account_number})."
                    )

        self.eval_chatbot_url()

        logger.debug(
            "%s.__init__() - finished %s",
            self.request_mixin_logger_prefix,
            SmarterRequestMixin.__repr__(self),
        )

        self.log_request_mixin_ready_status()

    def __str__(self) -> str:
        """
        String representation of the SmarterRequestMixin instance.

        :return: A string describing the instance.
        :rtype: str
        """
        return (
            f"{formatted_text(SmarterRequestMixin.__name__)}[{id(self)}]"
            f"("
            f"request={self.smarter_request}, "
            f"user={self.user_profile}"
            f")"
        )

    def __repr__(self) -> str:
        """
        Official string representation of the SmarterRequestMixin instance.

        :return: A string representation suitable for debugging.
        :rtype: str
        """
        return json.dumps(self.to_json(), indent=4)

    def __bool__(self) -> bool:
        """
        Boolean representation of the SmarterRequestMixin instance.

        :return: True if the instance is ready, False otherwise.
        :rtype: bool
        """
        return self.is_requestmixin_ready

    def __hash__(self) -> int:
        """
        Hash representation of the SmarterRequestMixin instance.

        :return: An integer hash of the instance.
        :rtype: int
        """
        return hash(
            (
                self.url,
                self.user_profile,
            )
        )

    def __eq__(self, other: Any) -> bool:
        """
        Equality comparison for SmarterRequestMixin instances.

        :param other: Another object to compare.
        :return: True if the instances are equal, False otherwise.
        :rtype: bool
        """
        if not isinstance(other, SmarterRequestMixin):
            return False
        return self.url == other.url and self.user_profile == other.user_profile

    def __lt__(self, other: Any) -> bool:
        """
        Less-than comparison for SmarterRequestMixin instances.

        :param other: Another object to compare.
        :return: True if the instance is less than the other, False otherwise.
        :rtype: bool
        """
        if not isinstance(other, SmarterRequestMixin):
            return NotImplemented
        return (self.url, self.user_profile) < (other.url, other.user_profile)

    def __le__(self, other: Any) -> bool:
        """
        Less-than-or-equal comparison for SmarterRequestMixin instances.

        :param other: Another object to compare.
        :return: True if the instance is less than or equal to the other, False otherwise.
        :rtype: bool
        """
        if not isinstance(other, SmarterRequestMixin):
            return NotImplemented
        return (self.url, self.user_profile) <= (other.url, other.user_profile)

    def __gt__(self, other: Any) -> bool:
        """
        Greater-than comparison for SmarterRequestMixin instances.

        :param other: Another object to compare.
        :return: True if the instance is greater than the other, False otherwise.
        :rtype: bool
        """
        if not isinstance(other, SmarterRequestMixin):
            return NotImplemented
        return (self.url, self.user_profile) > (other.url, other.user_profile)

    def __ge__(self, other: Any) -> bool:
        """
        Greater-than-or-equal comparison for SmarterRequestMixin instances.

        :param other: Another object to compare.
        :return: True if the instance is greater than or equal to the other, False otherwise.
        :rtype: bool
        """
        if not isinstance(other, SmarterRequestMixin):
            return NotImplemented
        return (self.url, self.user_profile) >= (other.url, other.user_profile)

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
    def request_mixin_logger_prefix(self) -> str:
        """
        Returns the logger prefix for the class.
        """
        return formatted_text(f"{__name__}.{SmarterRequestMixin.__name__}[{id(self)}]")

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
        self.clear_cached_properties()
        self._smarter_request = request
        logger.debug(
            "%s.smarter_request setter - request set to: %s",
            self.request_mixin_logger_prefix,
            request,
        )
        if request is not None:
            self._url = smarter_build_absolute_uri(request) if request else None
            logger.debug(
                "%s.smarter_request setter - url set to: %s",
                self.request_mixin_logger_prefix,
                self._url,
            )
            if (
                hasattr(request, "user")
                and request.user
                and hasattr(request.user, "is_authenticated")
                and request.user.is_authenticated
            ):
                self._smarter_request_user = request.user  # type: ignore
                logger.debug(
                    "%s.smarter_request setter - smarter_request_user set to: %s is_authenticated=%s",
                    self.request_mixin_logger_prefix,
                    self.smarter_request_user,
                    request.user.is_authenticated,
                )
                self.user = self._smarter_request_user
            else:
                # this duplicates the functionality of the DRF
                # authentication class. there are a variety of
                # cases where SmarterRequestMixin is initialized
                # before DRF reaches the point in its lifecycle
                # where authentication is performed. in those cases,
                # we attempt to authenticate here, to the same overall
                # effect.
                self.authenticate()

    @property
    def smarter_request_user(self) -> Optional[UserType]:
        """
        Returns the user associated with the request

        This property is named to avoid potential name collisions in child classes.
        It retrieves the user from the request object if available.

        Example::

            request_mixin = SmarterRequestMixin(request)
            user = request_mixin.smarter_request_user

        :return: The user associated with the request, or None if not available.
        """
        return self._smarter_request_user

    @property
    def auth_header(self) -> Optional[str]:
        """
        Get the Authorization header from the request.

        Example::

            request_mixin = SmarterRequestMixin(request)
            print(request_mixin.auth_header)

        This property checks for the "Authorization" header in the request headers or in the Django META dictionary.

        :return: The value of the "Authorization" header as a string, or None if not present.
        """
        return (
            self._smarter_request.headers.get("Authorization")
            if self._smarter_request and hasattr(self._smarter_request, "headers")
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
            logger.debug(
                "%s.api_token() - found Token auth header.",
                self.request_mixin_logger_prefix,
            )
            return self.auth_header.split("Token ")[1].encode()

        if isinstance(self.auth_header, str) and self.auth_header.startswith("Bearer "):
            logger.debug(
                "%s.api_token() - found Bearer auth header.",
                self.request_mixin_logger_prefix,
            )
            return self.auth_header.split("Bearer ")[1].encode()
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
            logger.debug(
                "%s.qualified_request() - request is None. Not a qualified request.",
                self.request_mixin_logger_prefix,
            )
            return False
        path = self.parsed_url.path if self.parsed_url else None
        if not path:
            logger.debug(
                "%s.qualified_request() - request path is None or empty. Not a qualified request: %s",
                self.request_mixin_logger_prefix,
                self.url,
            )
            return False

        if self.parsed_url and self.parsed_url.netloc and self.parsed_url.netloc[:7] == "192.168":
            logger.debug(
                "%s.qualified_request() - request originates from internal AWS Kubernetes subnet. Not a qualified request: %s",
                self.request_mixin_logger_prefix,
                self.url,
            )
            # internal processes running in a AWS kubernetes internal subnet.
            # definitely not a chatbot request.
            return False

        if path in self.amnesty_urls:
            logger.debug(
                "%s.qualified_request() - request path is in amnesty_urls. Not a qualified request: %s",
                self.request_mixin_logger_prefix,
                self.url,
            )
            # amnesty urls are not chatbot requests.
            return False

        if self.url_path_parts and self.url_path_parts[0] == "admin":
            logger.debug(
                f"{self.request_mixin_logger_prefix}.qualified_request() - request path starts with /admin/. Not a qualified request: {self.url}"
            )
            return False
        if self.url_path_parts and self.url_path_parts[0] == "docs":
            logger.debug(
                f"{self.request_mixin_logger_prefix}.qualified_request() - request path starts with /docs/. Not a qualified request: {self.url}"
            )
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
        if isinstance(path, str) and any(path.replace("/", "").endswith(ext) for ext in static_extensions):
            logger.debug(
                f"{self.request_mixin_logger_prefix}.qualified_request() - request path ends with a static file extension. Not a qualified request: {self.url}"
            )
            # static asset requests are not chatbot requests.
            return False

        logger.debug(
            "%s.qualified_request() - request is qualified: %s",
            self.request_mixin_logger_prefix,
            self.url,
        )
        return True

    @property
    def url(self) -> Optional[str]:
        """
        The string representation of the ParseResult object stored in _parsed_url.

        :return: The URL as a string.

        Example::

            request_mixin = SmarterRequestMixin(request)
            url_str = request_mixin.url
            print(url_str)  # e.g., 'https://example.com/path/'

        """
        if self._url:
            if isinstance(self._url, ParseResult):
                return self._url.geturl()
            try:
                url = SmarterValidator.urlify(self._url)
                parsed = urlparse(url)
                base_url = parsed._replace(query="", fragment="").geturl()
                if isinstance(base_url, ParseResult):
                    raise Exception("Unexpected ParseResult type for base_url.")
                return base_url
            except SmarterValueError as e:
                logger.error(
                    "%s.url() property encountered an error while validating URL: %s",
                    self.request_mixin_logger_prefix,
                    e,
                )
                return None

        logger.warning(
            "%s.url() property was accessed before it was initialized. request: %s",
            self.request_mixin_logger_prefix,
            self.smarter_request,
        )

    @property
    def parsed_url(self) -> Optional[ParseResult]:
        """
        Expose the private ParseResult URL object as a public property.

        :return: The parsed URL as a `ParseResult` object.

        Example::

            request_mixin = SmarterRequestMixin(request)
            parsed = request_mixin.parsed_url
            print(parsed.netloc)  # e.g., 'example.com'

        """
        if self._parsed_url is None and self.url is not None:
            logger.debug(
                "%s.parsed_url() - parsing URL: %s %s", self.request_mixin_logger_prefix, self.url, type(self.url)
            )
            if isinstance(self.url, ParseResult):
                self._parsed_url = self.url
            else:
                self._parsed_url = urlparse(self.url) if isinstance(self.url, str) else None
            logger.debug(
                "%s.parsed_url() - parsed URL: %s",
                self.request_mixin_logger_prefix,
                self._parsed_url,
            )
        return self._parsed_url

    @cached_property
    def url_path_parts(self) -> list[str]:
        """
        Extract the path parts from the URL.

        :return: A list of strings representing each part of the URL path.

        Example::

            request_mixin = SmarterRequestMixin(request)
            parts = request_mixin.url_path_parts
            print(parts)  # e.g., ['api', 'v1', 'workbench', '1', 'chat']

        """
        if not self.parsed_url:
            return []
        path = self.parsed_url.path
        if isinstance(path, bytes):
            path = path.decode("utf-8")
        return path.strip("/").split("/")

    @property
    def params(self) -> QueryDict:
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
        if not self.smarter_request:
            logger.warning(
                "%s.params() - request is None or not set. Cannot extract query string parameters.",
                self.request_mixin_logger_prefix,
            )
            return QueryDict("")
        if not hasattr(self.smarter_request, "META"):
            logger.warning(
                "%s.params() - request does not have META attribute. Cannot extract query string parameters.",
                self.request_mixin_logger_prefix,
            )
            return QueryDict("")
        if self.smarter_request.META is None:
            logger.warning(
                "%s.params() - request.META is None. Cannot extract query string parameters.",
                self.request_mixin_logger_prefix,
            )
            return QueryDict("")
        # Always construct QueryDict, even if QUERY_STRING is empty
        query_string = self.smarter_request.META.get("QUERY_STRING", "")
        if not query_string:
            logger.debug(
                "%s.params() - request has no query string parameters.",
                self.request_mixin_logger_prefix,
            )
        if not self._params:
            try:
                self._params = QueryDict(query_string)  # type: ignore
                if not self._params:
                    raise AttributeError("No query string parameters found.")
            except AttributeError:
                return QueryDict("")
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
            logger.debug(
                "%s.cache_key() - returning cached cache key: %s",
                self.request_mixin_logger_prefix,
                self._cache_key,
            )
            return self._cache_key

        if not self.smarter_request:
            logger.warning(
                "%s.cache_key() - request is None or not set. Cannot generate cache key.",
                self.request_mixin_logger_prefix,
            )
            return None

        uid = self.uid or "unknown_uid"
        username = getattr(self.smarter_request, "user", "Anonymous") if self.smarter_request else "Anonymous"
        raw_string = f"{self.__class__.__name__}_{str(username)}_cache_key()_{str(uid)}"
        hash_object = hashlib.sha256()
        hash_object.update(raw_string.encode())
        hash_string = hash_object.hexdigest()
        self._cache_key = hash_string

        logger.debug(
            "%s.cache_key() - generated cache key: %s",
            self.request_mixin_logger_prefix,
            self._cache_key,
        )

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
            logger.debug(
                "%s.session_key() - setting session_key to %s", self.request_mixin_logger_prefix, self._session_key
            )
        return self._session_key

    @property
    def smarter_request_chatbot_id(self) -> Optional[int]:
        """
        Extract the chatbot id from the URL.

        Example:
            http://localhost:9357/api/v1/workbench/1912/chat/config/

            return 1912

        :return: The chatbot id as an integer, or None if not found.
        """
        if not self.smarter_request:
            return None
        if not self.qualified_request:
            return None

        if self.is_chatbot_smarter_api_url:
            path_parts = self.url_path_parts
            return int(path_parts[3]) if isinstance(path_parts, list) and len(path_parts) > 3 else None

        if self.is_chatbot_named_url:
            # can't get from ChatBot bc of circular import
            return None

    @property
    def url_account_number(self) -> Optional[str]:
        """
        Extract the account number from the URL using the pattern defined in
        SmarterValidator.VALID_ACCOUNT_NUMBER_PATTERN.

        Example:
            http://example.3141-5926-5359.api.localhost:9357/config

            returns "3141-5926-5359"

        :return: The account number as a string, or None if not found.
        """
        if self._url_account_number:
            return self._url_account_number

        if not self.smarter_request:
            return None
        if not self.qualified_request:
            return None
        self._url_account_number = account_number_from_url(self.url)  # type: ignore
        return self._url_account_number

    @cached_property
    def smarter_request_chatbot_name(self) -> Optional[str]:
        """
        Extract the chatbot name from the URL.

        Example:
            http://example.3141-5926-5359.api.localhost:9357/config

            returns "example"

        :return: The chatbot name as a string, or None if not found.
        """
        if not self.is_chatbot:
            logger.debug(
                "%s.smarter_request_chatbot_name() - request is not a chatbot url: %s",
                self.request_mixin_logger_prefix,
                self.url,
            )
            return None

        # 1.) http://example.api.localhost:9357/config
        if self.is_chatbot_named_url and self.parsed_url is not None:
            netloc_parts = self.parsed_url.netloc.split(".") if self.parsed_url and self.parsed_url.netloc else None
            retval = netloc_parts[0] if netloc_parts else None
            retval = rfc1034_compliant_to_snake(retval) if isinstance(retval, str) else retval
            logger.debug(
                "%s.smarter_request_chatbot_name() - extracted chatbot name from named url: %s",
                self.request_mixin_logger_prefix,
                retval,
            )
            return retval

        # 2.) example: http://localhost:9357/workbench/<str:name>/config/
        if self.is_chatbot_sandbox_url:
            try:
                retval = self.url_path_parts[1]
                retval = rfc1034_compliant_to_snake(retval) if isinstance(retval, str) else retval
                logger.debug(
                    "%s.smarter_request_chatbot_name() - extracted chatbot name from sandbox url: %s",
                    self.request_mixin_logger_prefix,
                    retval,
                )
                return retval
            # pylint: disable=broad-except
            except Exception:
                logger.error(
                    "%s.smarter_request_chatbot_name() - failed to extract chatbot name from sandbox url: %s",
                    self.request_mixin_logger_prefix,
                    self.url,
                )
        # 3.) http://localhost:9357/api/v1/workbench/<int:chatbot_id>
        # no name. nothing to do in this case.
        if self.is_chatbot_smarter_api_url:
            logger.debug(
                "%s.smarter_request_chatbot_name() - smarter api url has no chatbot name: %s",
                self.request_mixin_logger_prefix,
                self.url,
            )
            return None

        # 4.) http://localhost:9357/api/v1/cli/chat/config/<str:name>/
        #     http://localhost:9357/api/v1/cli/chat/<str:name>/
        if self.is_chatbot_cli_api_url:
            try:
                retval = self.url_path_parts[-1]
                retval = rfc1034_compliant_to_snake(retval) if isinstance(retval, str) else retval
                logger.debug(
                    "%s.smarter_request_chatbot_name() - extracted chatbot name from cli api url: %s",
                    self.request_mixin_logger_prefix,
                    retval,
                )
                return retval
            # pylint: disable=broad-except
            except Exception:
                logger.error(
                    "%s.smarter_request_chatbot_name() - failed to extract chatbot name from cli url: %s",
                    self.request_mixin_logger_prefix,
                    self.url,
                )

        logger.debug(
            "%s.smarter_request_chatbot_name() - could not extract chatbot name from url: %s",
            self.request_mixin_logger_prefix,
            self.url,
        )
        return None

    @property
    def timestamp(self):
        """
        Create a consistent timestamp based on the time that this object was instantiated.

        :return: The timestamp as a `datetime` object.

        Example::

            request_mixin = SmarterRequestMixin(request)
            ts = request_mixin.timestamp
            print(ts)  # e.g., 2025-12-01 12:34:56.789012

        """
        return self._timestamp

    @cached_property
    def data(self) -> Optional[Union[dict, list, str]]:
        """
        Get the request body data as a dictionary, list or str.

        Used for setting the session_key.

        :return: The request body data as a dict, list, or str, or None if not available.

        Example::

            request_mixin = SmarterRequestMixin(request)
            data = request_mixin.data
            print(data)  # e.g., {'session_key': 'abc123', ...}

        """
        if self._data:
            return self._data

        if not self.smarter_request:
            logger.debug(
                "%s.data() - request is None. Cannot parse request body.",
                self.request_mixin_logger_prefix,
            )
            return None
        if not self.qualified_request:
            logger.debug(
                "%s.data() - request is not a qualified_request. Cannot parse request body: %s",
                self.request_mixin_logger_prefix,
                self.url,
            )
            return None

        body = self.smarter_request.body if hasattr(self.smarter_request, "body") else None
        if not isinstance(body, (str, bytearray, bytes)):
            logger.debug(
                "%s.data() - request body is not a string or bytes. Cannot parse request body: %s",
                self.request_mixin_logger_prefix,
                body,
            )
            return None
        body_str = body.decode("utf-8").strip()
        if body_str is not None:
            try:
                self._data = json.loads(body_str) if isinstance(body_str, (str, bytearray, bytes)) else None
                logger.debug(
                    "%s.data() - initialized json from request body: %s",
                    self.request_mixin_logger_prefix,
                    json.dumps(self._data, indent=4),
                )
            except json.JSONDecodeError:
                try:
                    self._data = yaml.safe_load(body_str) if body_str else None
                    if isinstance(self._data, (dict, list)):
                        logger.debug(
                            "%s.data() - initialized json from parsed yaml request body: %s",
                            self.request_mixin_logger_prefix,
                            json.dumps(self._data, indent=4),
                        )
                except yaml.YAMLError:
                    logger.error(
                        "%s.data() - failed to parse request body: %s",
                        self.request_mixin_logger_prefix,
                        body_str,
                    )
        if self._data is not None:
            logger.debug(
                "%s.data() - request body parsed successfully: %s",
                self.request_mixin_logger_prefix,
                json.dumps(self._data, indent=4),
            )
        else:
            logger.debug(
                "%s.data() - request body is empty or could not be parsed and has been defaulted to {}",
                self.request_mixin_logger_prefix,
            )

        self._data = self._data or {}
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

        Example::

            request_mixin = SmarterRequestMixin(request)
            unique_str = request_mixin.unique_client_string
            print(unique_str)

        """
        if not self.smarter_request:
            return "unique_client_string"
        account_number = self.account.account_number if self.account else "####-####-####"
        url = self.url if self.url else "http://localhost:9357/"
        timestamp = self.timestamp.isoformat()
        return f"{account_number}.{url}.{self.user_agent}.{self.ip_address}.{timestamp}"

    @cached_property
    def ip_address(self) -> Optional[str]:
        """
        Get the client's IP address from the request object.

        This property attempts to extract the IP address from the request's META dictionary,
        using the "REMOTE_ADDR" key. If the IP address is not available, it returns None.

        Returns:
            Optional[str]: The client's IP address as a string, or None if not found.

        Example::

            request_mixin = SmarterRequestMixin(request)
            ip = request_mixin.ip_address
            print(ip)  # e.g., '192.168.1.100'

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

        Example::

            request_mixin = SmarterRequestMixin(request)
            ua = request_mixin.user_agent
            print(ua)  # e.g., 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)...'

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

    @cached_property
    def is_config(self) -> bool:
        """
        Returns True if the URL resolves to a config endpoint.

        Examples:
            http://testserver/api/v1/cli/chat/config/testc7098865f39202d5/
            http://localhost:9357/workbench/example/config/?session_key=1aeee4c1f183354247f43f80261573da921b0167c7c843b28afd3cb5ebba0d9a
            http://localhost:9357/api/v1/workbench/<int:chatbot_id>/chat/config/
            http://example.api.localhost:9357/config

        Returns:
            bool: True if the URL is a config endpoint, otherwise False.
        """
        if not self.is_chatbot:
            logger.debug("%s.is_config() - not a chatbot url: %s", self.request_mixin_logger_prefix, self.url)
            return False
        if not isinstance(self.url_path_parts, list):
            logger.debug(
                "%s.is_config() - url_path_parts is not a list: %s",
                self.request_mixin_logger_prefix,
                self.url_path_parts,
            )
            return False
        if "config" not in self.url_path_parts:
            logger.debug(
                "%s.is_config() - 'config' not in url_path_parts: %s",
                self.request_mixin_logger_prefix,
                self.url_path_parts,
            )
            return False
        logger.debug("%s.is_config() - url is a config endpoint: %s", self.request_mixin_logger_prefix, self.url)
        return True

    @cached_property
    def is_dashboard(self) -> bool:
        """
        Returns True if the URL resolves to a dashboard endpoint.

        Returns:
            bool: True if the URL is a dashboard endpoint, otherwise False.
        """
        if not self.smarter_request:
            logger.debug("%s.is_dashboard() - smarter_request is None", self.request_mixin_logger_prefix)
            return False
        if not isinstance(self.url_path_parts, list):
            logger.debug("%s.is_dashboard() - url_path_parts is not a list", self.request_mixin_logger_prefix)
            return False
        if len(self.url_path_parts) == 0:
            logger.debug("%s.is_dashboard() - url_path_parts is empty", self.request_mixin_logger_prefix)
            return False
        try:
            if self.url_path_parts[-1] != "dashboard":
                logger.debug(
                    "%s.is_dashboard() - last url_path_part is not 'dashboard': %s",
                    self.request_mixin_logger_prefix,
                    self.url_path_parts[-1],
                )
                return False
            if "/dashboard/" not in self.parsed_url.path:
                logger.debug(
                    "%s.is_dashboard() - '/dashboard/' not in url path: %s",
                    self.request_mixin_logger_prefix,
                    self.parsed_url.path,
                )
                return False
            return True
        except IndexError:
            return False

    @cached_property
    def is_workbench(self) -> bool:
        """
        Returns True if the URL resolves to a workbench endpoint.

        Returns:
            bool: True if the URL is a workbench endpoint, otherwise False.
        """
        if not self.smarter_request:
            logger.debug("%s.is_dashboard() - smarter_request is None", self.request_mixin_logger_prefix)
            return False
        if not isinstance(self.url_path_parts, list):
            logger.debug("%s.is_dashboard() - url_path_parts is not a list", self.request_mixin_logger_prefix)
            return False
        if len(self.url_path_parts) == 0:
            logger.debug("%s.is_dashboard() - url_path_parts is empty", self.request_mixin_logger_prefix)
            return False
        try:
            if self.url_path_parts[-1] != "workbench":
                logger.debug(
                    "%s.is_workbench() - last url_path_part is not 'workbench': %s",
                    self.request_mixin_logger_prefix,
                    self.url_path_parts[-1],
                )
                return False
            if "/workbench/" not in self.parsed_url.path:
                logger.debug(
                    "%s.is_workbench() - '/workbench/' not in url path: %s",
                    self.request_mixin_logger_prefix,
                    self.parsed_url.path,
                )
                return False
            return True
        except IndexError:
            return False

    @cached_property
    def is_environment_root_domain(self) -> bool:
        """
        Returns True if the URL resolves to the environment root domain.

        Returns:
            bool: True if the URL is the environment root domain, otherwise False.
        """
        if not self.smarter_request:
            logger.debug("%s.is_environment_root_domain() - smarter_request is None", self.request_mixin_logger_prefix)
            return False
        if not self.parsed_url:
            logger.debug("%s.is_environment_root_domain() - parsed_url is None", self.request_mixin_logger_prefix)
            return False

        netloc_match = self.parsed_url.netloc == smarter_settings.environment_platform_domain
        if not netloc_match:
            logger.debug(
                "%s.is_environment_root_domain() - netloc does not match. expected=%s actual=%s",
                self.request_mixin_logger_prefix,
                smarter_settings.environment_platform_domain,
                self.parsed_url.netloc,
            )
            return False
        path_match = self.parsed_url.path == "/"
        if not path_match:
            logger.debug(
                "%s.is_environment_root_domain() - path does not match. expected='/' actual=%s",
                self.request_mixin_logger_prefix,
                self.parsed_url.path,
            )
            return False
        return netloc_match and path_match

    @cached_property
    def is_chatbot(self) -> bool:
        """
        Returns True if the URL resolves to a chatbot endpoint.

        Conditions are checked in a lazy sequence to avoid unnecessary processing.

        Examples:
            - http://localhost:9357/api/v1/prompt/1/chat/
            - http://localhost:9357/api/v1/cli/chat/example/
            - http://example.3141-5926-5359.api.localhost:9357/
            - http://localhost:9357/workbench/<str:name>/chat/
            - http://localhost:9357/api/v1/chatbots/1556/chat/

        Returns:
            bool: True if the URL is a chatbot endpoint, otherwise False.
        """

        retval = self.qualified_request and (
            self.is_chatbot_named_url
            or self.is_chatbot_sandbox_url
            or self.is_chatbot_smarter_api_url
            or self.is_chatbot_cli_api_url
        )
        logger.debug("%s.is_chatbot() - url is chatbot: %s -> %s", self.request_mixin_logger_prefix, self.url, retval)
        return retval

    @cached_property
    def is_smarter_api(self) -> bool:
        """
        Returns True if the URL is of the form http://localhost:9357/api/v1/.

        Examples:
            - path_parts: ['api', 'v1', 'chatbots', '1', 'chat']
            - http://api.localhost:9357/

        Returns:
            bool: True if the URL matches the smarter API pattern, otherwise False.
        """
        if not self.smarter_request:
            logger.debug("%s.is_smarter_api() - request is None", self.request_mixin_logger_prefix)
            return False
        if not self.url:
            logger.debug("%s.is_smarter_api() - url is None or empty", self.request_mixin_logger_prefix)
            return False

        # Check for 'api' in path parts or in the host (netloc)
        in_path = isinstance(self.url_path_parts, list) and "api" in self.url_path_parts
        in_host = self.parsed_url and "api" in self.parsed_url.netloc.split(".")
        if in_path or in_host:
            logger.debug(
                "%s.is_smarter_api() - url is a smarter api url: %s", self.request_mixin_logger_prefix, self.url
            )
            return True

        logger.debug(
            "%s.is_smarter_api() - url is not a smarter api url: %s", self.request_mixin_logger_prefix, self.url
        )
        return False

    @cached_property
    def is_chatbot_smarter_api_url(self) -> bool:
        """
        Returns True if the URL is of the form:

            - http://localhost:9357/api/v1/workbench/1/chat/
              path_parts: ['api', 'v1', 'workbench', '<int:pk>', 'chat']

            - http://localhost:9357/api/v1/chatbots/1556/chat/
              path_parts: ['api', 'v1', 'chatbots', '<int:pk>', 'chat']

        Returns:
            bool: True if the URL matches a smarter API chatbot endpoint, otherwise False.
        """
        if not self.smarter_request:
            logger.debug("%s.is_chatbot_smarter_api_url() - request is None", self.request_mixin_logger_prefix)
            return False
        if not self.qualified_request:
            logger.debug("%s.is_chatbot_smarter_api_url() - request is not qualified", self.request_mixin_logger_prefix)
            return False
        if not self.parsed_url:
            logger.debug("%s.is_chatbot_smarter_api_url() - url is None or empty", self.request_mixin_logger_prefix)
            return False

        if not isinstance(self.url_path_parts, list):
            logger.debug(
                "%s.is_chatbot_smarter_api_url() - url_path_parts is not a list", self.request_mixin_logger_prefix
            )
            return False
        if len(self.url_path_parts) != 5:
            logger.debug(
                "%s.is_chatbot_smarter_api_url() - url_path_parts does not have 5 parts: %s",
                self.request_mixin_logger_prefix,
                self.url_path_parts,
            )
            return False
        if self.url_path_parts[0] != "api":
            logger.debug(
                "%s.is_chatbot_smarter_api_url() - first part is not 'api': %s",
                self.request_mixin_logger_prefix,
                self.url_path_parts,
            )
            return False
        if self.url_path_parts[1] != "v1":
            logger.debug(
                "%s.is_chatbot_smarter_api_url() - second part is not 'v1': %s",
                self.request_mixin_logger_prefix,
                self.url_path_parts,
            )
            return False
        if self.url_path_parts[2] not in ["workbench", "chatbots"]:
            logger.debug(
                "%s.is_chatbot_smarter_api_url() - third part is not 'workbench' or 'chatbots': %s",
                self.request_mixin_logger_prefix,
                self.url_path_parts,
            )
            return False
        if not self.url_path_parts[3].isnumeric():
            # expecting <int:pk> to be numeric: ['api', 'v1', 'workbench', '<int:pk>', 'chat']
            logger.debug(
                "%s.is_chatbot_smarter_api_url() - fourth part is not numeric: %s",
                self.request_mixin_logger_prefix,
                self.url_path_parts,
            )
            return False
        if self.url_path_parts[4] != "chat":
            # expecting 'chat' at the end of the path_parts: ['api', 'v1', 'workbench', '<int:pk>', 'chat']
            logger.debug(
                "%s.is_chatbot_smarter_api_url() - fifth part is not 'chat': %s",
                self.request_mixin_logger_prefix,
                self.url_path_parts,
            )
            return False

        logger.debug(
            "%s.is_chatbot_smarter_api_url() - url is a smarter api chatbot url: %s",
            self.request_mixin_logger_prefix,
            self.url,
        )
        return True

    @cached_property
    def is_chatbot_cli_api_url(self) -> bool:
        """
        Returns True if the URL is of the form http://localhost:9357/api/v1/cli/chat/example/.

        The expected path parts are:
            ['api', 'v1', 'cli', 'chat', 'example']

        Returns:
            bool: True if the URL matches the CLI chatbot API pattern, otherwise False.
        """
        if not self.smarter_request:
            logger.debug("%s.is_chatbot_cli_api_url() - request is None", self.request_mixin_logger_prefix)
            return False
        if not self.is_smarter_api:
            logger.debug("%s.is_chatbot_cli_api_url() - request is not smarter api", self.request_mixin_logger_prefix)
            return False

        path_parts = self.url_path_parts
        try:
            if path_parts[2] != "cli":
                logger.debug(
                    "%s.is_chatbot_cli_api_url() - third part is not 'cli': %s",
                    self.request_mixin_logger_prefix,
                    path_parts,
                )
                return False
            if path_parts[3] != "chat":
                logger.debug(
                    "%s.is_chatbot_cli_api_url() - fourth part is not 'chat': %s",
                    self.request_mixin_logger_prefix,
                    path_parts,
                )
                return False
        except IndexError:
            logger.debug(
                "%s.is_chatbot_cli_api_url() - url_path_parts index out of range: %s",
                self.request_mixin_logger_prefix,
                path_parts,
            )
            return False

        logger.debug(
            "%s.is_chatbot_cli_api_url() - url is a cli chatbot api url: %s", self.request_mixin_logger_prefix, self.url
        )
        return True

    @cached_property
    def is_chatbot_named_url(self) -> bool:
        """
        Returns True if the url is of the form:

            - https://example.3141-5926-5359.api.example.com/
            - http://example.3141-5926-5359.api.localhost:9357/
            - http://example.3141-5926-5359.api.localhost:9357/config/

        Returns:
            bool: True if the URL matches the named chatbot pattern, otherwise False.
        """
        if not self.smarter_request:
            logger.debug("%s.is_chatbot_named_url() - request is None", self.request_mixin_logger_prefix)
            return False
        if not self.url:
            logger.debug("%s.is_chatbot_named_url() - url is None or empty", self.request_mixin_logger_prefix)
            return False
        if not smarter_settings.environment_api_domain in self.url:
            logger.debug(
                "%s.is_chatbot_named_url() - url %s does not contain environment_api_domain: %s",
                self.request_mixin_logger_prefix,
                self.url,
                smarter_settings.environment_api_domain,
            )
            return False
        account_number = self.url_account_number
        if account_number is not None:
            logger.debug(
                "%s.is_chatbot_named_url() - url %s is a named url with account number: %s",
                self.request_mixin_logger_prefix,
                self.url,
                account_number,
            )
            if self.account is None:
                # lazy load the account from the account number
                self.account = get_cached_account(account_number=account_number)
            return True

        # Accept root path or root with trailing slash
        if isinstance(self.parsed_url, ParseResult) and self.parsed_url.path not in ("", "/"):
            logger.debug(
                "%s.is_chatbot_named_url() - url %s path is not root or trailing slash: %s",
                self.request_mixin_logger_prefix,
                self.url,
                self.parsed_url.path,
            )
            return False

        if isinstance(self.parsed_url, ParseResult) and netloc_pattern_named_url.match(self.parsed_url.netloc):
            logger.debug(
                "%s.is_chatbot_named_url() - url %s is a named url without account number.",
                self.request_mixin_logger_prefix,
                self.url,
            )
            return True

        logger.debug(
            "%s.is_chatbot_named_url() - url %s is not a named url.",
            self.request_mixin_logger_prefix,
            self.url,
        )
        return False

    @cached_property
    def is_chatbot_sandbox_url(self) -> bool:
        """
        Example URLs for chatbot sandbox endpoints.

        Examples:

            https://alpha.platform.smarter.sh/workbench/example/
            https://<environment_domain>/workbench/<name>
            path_parts: ['workbench', 'example']

            http://localhost:9357/workbench/<str:name>/chat/
            https://alpha.platform.smarter.sh/workbench/example/config/
            https://<environment_domain>/workbench/<name>/config/
            path_parts: ['workbench', 'example', 'config']

            http://localhost:9357/api/v1/prompt/1/chat/
            http://<environment_domain>/api/v1/prompt/<int:chatbot_id>/chat/

        Returns:
            bool: True if the URL matches a chatbot sandbox endpoint, otherwise False.
        """
        if not self.smarter_request:
            logger.warning(
                "%s.is_chatbot_sandbox_url() - request is None or not set.", self.request_mixin_logger_prefix
            )
            return False
        if not self.qualified_request:
            logger.debug("%s.is_chatbot_sandbox_url() - request is not qualified.", self.request_mixin_logger_prefix)
            return False
        if not self.parsed_url:
            logger.warning("%s.is_chatbot_sandbox_url() - url is None or not set.", self.request_mixin_logger_prefix)
            return False

        # smarter api - http://localhost:9357/api/v1/prompt/1/chat/
        path_parts = self.url_path_parts
        if (
            len(path_parts) == 5
            and path_parts[0] == "api"
            and path_parts[1] == "v1"
            and path_parts[2] == "prompt"
            and path_parts[3].isnumeric()
            and path_parts[4] == "chat"
        ):
            logger.debug(
                "%s.is_chatbot_sandbox_url() - url %s is a chatbot sandbox smarter api url.",
                self.request_mixin_logger_prefix,
                self.url,
            )
            return True

        # ---------------------------------------------------------------------
        # workbench urls: http://localhost:9357/workbench/<str:name>/chat/
        # ---------------------------------------------------------------------

        # valid path_parts:
        #   ['workbench', '<slug>', 'chat']
        #   ['workbench', '<slug>', 'config']
        if self.parsed_url.netloc != smarter_settings.environment_platform_domain:
            logger.debug(
                "%s.is_chatbot_sandbox_url() - url %s netloc does not match environment platform domain: %s",
                self.request_mixin_logger_prefix,
                self.url,
                smarter_settings.environment_platform_domain,
            )
            return False
        if len(path_parts) != 3:
            logger.debug(
                "%s.is_chatbot_sandbox_url() - url %s does not have exactly 3 path parts: %s",
                self.request_mixin_logger_prefix,
                self.url,
                path_parts,
            )
            return False
        if path_parts[0] != "workbench":
            logger.debug(
                "%s.is_chatbot_sandbox_url() - url %s first path part is not 'workbench': %s",
                self.request_mixin_logger_prefix,
                self.url,
                path_parts,
            )
            return False
        if not path_parts[1].isalpha():
            # expecting <slug> to be alpha: ['workbench', '<slug>', 'config']
            logger.debug(
                "%s.is_chatbot_sandbox_url() - url %s second path part is not alphabetic slug: %s",
                self.request_mixin_logger_prefix,
                self.url,
                path_parts,
            )
            return False
        if path_parts[-1] in ["config", "chat"]:
            # expecting:
            #   ['workbench', '<slug>', 'chat']
            #   ['workbench', '<slug>', 'config']
            logger.debug(
                "%s.is_chatbot_sandbox_url() - url %s is a chatbot sandbox url.",
                self.request_mixin_logger_prefix,
                self.url,
            )
            return True

        logger.warning(
            "%s.is_chatbot_sandbox_url() - could not verify whether url is a chatbot sandbox url: %s",
            self.request_mixin_logger_prefix,
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
            logger.debug(
                "%s.is_default_domain() - request is None. Cannot determine default domain.",
                self.request_mixin_logger_prefix,
            )
            return False
        if not self.url:
            logger.debug(
                "%s.is_default_domain() - url is None or empty. Cannot determine default domain.",
                self.request_mixin_logger_prefix,
            )
            return False
        logger.debug(
            "%s.is_default_domain() - checking if url %s contains default domain %s",
            self.request_mixin_logger_prefix,
            self.url,
            smarter_settings.environment_api_domain,
        )
        return smarter_settings.environment_api_domain in self.url

    @cached_property
    def path(self) -> Optional[str]:
        """
        Extracts the path from the URL.

        :return:
            Optional[str]: The path as a string, or None if not found.

        Examples:
            - https://hr.3141-5926-5359.alpha.api.example.com/chatbot/
              returns '/chatbot/'
        """
        if not self.smarter_request:
            logger.debug("%s.path() - request is None. Cannot extract path.", self.request_mixin_logger_prefix)
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
            # For 'https://hr.3141-5926-5359.alpha.api.example.com/chatbot/' → 'smarter.sh'
            # For 'http://localhost:9357/' → 'localhost'

        """
        if not self.smarter_request:
            logger.debug(
                "%s.root_domain() - request is None. Cannot extract root domain.", self.request_mixin_logger_prefix
            )
            return None
        if not self.url:
            logger.debug(
                "%s.root_domain() - url is None or empty. Cannot extract root domain.", self.request_mixin_logger_prefix
            )
            return None
        url = SmarterValidator.urlify(self.url, environment=smarter_settings.environment)  # type: ignore
        if url:
            extracted = tldextract.extract(url)
            if extracted.domain and extracted.suffix:
                return f"{extracted.domain}.{extracted.suffix}"
            if extracted.domain:
                return extracted.domain
        logger.warning(
            "%s.root_domain() - failed to extract root domain from url: %s", self.request_mixin_logger_prefix, self.url
        )
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
                        # 'https://hr.3141-5926-5359.alpha.api.example.com/chatbot/'
        """
        if not self.smarter_request:
            return None
        if not self.url:
            return None
        extracted = tldextract.extract(self.url)
        return extracted.subdomain or None

    @cached_property
    def api_subdomain(self) -> Optional[str]:
        """
        Extracts the API subdomain from the URL.

        :return: The API subdomain or None if not found.

        example::

            - https://hr.3141-5926-5359.alpha.api.example.com/chatbot/
            returns 'hr'
        """
        if not self.smarter_request:
            return None
        if not self.is_chatbot:
            return None
        try:
            result = urlparse(self.url)
            netloc = result.netloc.decode() if isinstance(result.netloc, bytes) else result.netloc
            domain_parts = netloc.split(".")  # type: ignore
            return str(domain_parts[0]) if len(domain_parts) > 0 else None
        except TypeError:
            return None

    @cached_property
    def domain(self) -> Optional[str]:
        """
        Extracts the domain from the URL.

        :return: The domain or None if not found.

        examples::

            - https://hr.3141-5926-5359.alpha.api.example.com/chatbot/
              returns 'hr.3141-5926-5359.alpha.api.example.com'
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
        return f"{parent_class}.{SmarterRequestMixin.__name__}()"

    @cached_property
    def is_requestmixin_ready(self) -> bool:
        """
        Returns True if the request mixin is ready for processing.
        This is a convenience property to check if the request is ready.

        :return: True if the request mixin is ready, False otherwise.
        """
        # cheap and easy way to fail.
        if not self.is_accountmixin_ready:
            logger.warning(
                "%s.is_requestmixin_ready() - AccountMixin is not ready. Cannot process request.",
                self.request_mixin_logger_prefix,
            )
            return False
        if not isinstance(self.smarter_request, Union[HttpRequest, RestFrameworkRequest, WSGIRequest, MagicMock]):
            logger.warning(
                "%s.is_requestmixin_ready() - request is not a HttpRequest. Received %s. Cannot process request.",
                self.request_mixin_logger_prefix,
                type(self._smarter_request).__name__,
            )
            return False
        if not isinstance(self.parsed_url, ParseResult):
            logger.warning(
                "%s.is_requestmixin_ready() - _parsed_url is not a ParseResult. Received %s. Cannot process request.",
                self.request_mixin_logger_prefix,
                type(self._parsed_url).__name__,
            )
            return False
        if not isinstance(self.url, str):
            logger.warning(
                "%s.is_requestmixin_ready() - _url is not a string. Received %s. Cannot process request.",
                self.request_mixin_logger_prefix,
                type(self.url).__name__,
            )
            return False
        return True

    @property
    def request_mixin_ready_state(self) -> str:
        """
        Returns a string representation of the request mixin's ready state.

        :return: A string indicating whether the request mixin is ready or not.
        """
        return formatted_text_green("Ready") if self.is_requestmixin_ready else formatted_text_red("Not Ready")

    @property
    def ready(self) -> bool:
        """
        returns True if the request is ready for processing.

        :return: True if the request is ready, False otherwise.

        """
        retval = super().ready
        if not retval:
            logger.warning(
                "%s.ready() - returning False because AccountMixin is not ready.",
                self.request_mixin_logger_prefix,
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
        logger.debug(
            "%s.generate_session_key() Generated new session key: %s", self.request_mixin_logger_prefix, session_key
        )
        return session_key

    def find_session_key(self) -> Optional[str]:
        """
        Returns the unique chat session key value for this request.

        The session_key is managed by the /config/ endpoint for the chatbot. The React app calls this endpoint at app initialization to get a JSON dict that includes, among other info, this session_key, which uniquely identifies the device and the individual chatbot session for the device.

        For subsequent chat prompt requests, the session_key is intended to be sent in the body of the request as a key-value pair, e.g. {"session_key": "1234567890"}.

        This method will also check the request headers and cookies for the session_key. The session key can be found in one of the following:

         - URL parameter: http://localhost:9357/workbench/example/config/?session_key=1aeee4c1f183354247f43f80261573da921b0167c7c843b28afd3cb5ebba0d9a
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
        session_key = session_key_from_url(self.url)  # type: ignore
        if session_key:
            session_key = session_key.rstrip("/")
            SmarterValidator.validate_session_key(session_key)
            logger.debug(
                f"session_key() - initialized from url: {session_key}",
            )
            return session_key

        # next, we look for it in the request body data.
        if isinstance(self.data, dict):
            session_key = self.data.get(SMARTER_CHAT_SESSION_KEY_NAME)
            session_key = session_key.strip() if isinstance(session_key, str) else None
            if session_key:
                session_key = session_key.rstrip("/")
                SmarterValidator.validate_session_key(session_key)
                logger.debug(
                    f"session_key() - initialized from request body: {session_key}",
                )
                return session_key

        # next, we look for it in the cookie data.
        session_key = self.get_cookie_value(SMARTER_CHAT_SESSION_KEY_NAME)
        session_key = session_key.strip() if isinstance(session_key, str) else None
        if session_key:
            session_key = session_key.rstrip("/")
            SmarterValidator.validate_session_key(session_key)
            logger.debug(
                f"session_key() - initialized from cookie data of the request object: {session_key}",
            )
            return session_key

        # finally, we look for it in the GET parameters.
        session_key = self.smarter_request.GET.get(SMARTER_CHAT_SESSION_KEY_NAME) if self.smarter_request else None
        session_key = session_key.strip() if isinstance(session_key, str) else None
        if session_key:
            session_key = session_key.rstrip("/")
            SmarterValidator.validate_session_key(session_key)
            logger.debug(
                f"session_key() - initialized from the get() parameters of the request object: {session_key}",
            )
            return session_key

    def eval_chatbot_url(self):
        """
        If we are a chatbot, based on analysis of the URL format
        then we need to make a follow up check of the user and account.

        Examples:

            - http://example.3141-5926-5359.api.localhost:9357/
            - https://alpha.platform.smarter.sh/api/v1/workbench/1/chatbot/
            - http://localhost:9357/api/v1/cli/chat/example/

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
            # http://example.3141-5926-5359.api.localhost:9357/
            if not self.account:
                account_number = self.url_account_number
                if account_number:
                    self.account = get_cached_account(account_number=account_number)  # type: ignore
            if self.account and not self.user:
                self.user = get_cached_admin_user_for_account(account=self.account)  # type: ignore
        if self.is_chatbot_smarter_api_url:
            # https://alpha.platform.smarter.sh/api/v1/workbench/1/chatbot/
            pass
        if self.is_chatbot_cli_api_url:
            # http://localhost:9357/api/v1/cli/chat/example/
            pass

    # pylint: disable=W0221
    def authenticate(self) -> bool:
        """
        Authenticates the request using the provided API token.
        """
        if self.api_token:
            logger.debug("%s.authenticate() - authenticating with api_token.", self.request_mixin_logger_prefix)
            return super().authenticate(api_token=self.api_token)
        return False

    def clear_cached_properties(self):
        """
        Clears all cached properties in this mixin.
        """
        self._smarter_request = None
        self._url = None
        self._url_account_number = None
        self._parsed_url = None
        self._params = None
        self._session_key = None
        self._data = None
        self._cache_key = None

        # Clear cached_property values
        for cls in self.__class__.__mro__:
            for name, value in inspect.getmembers(cls):
                if isinstance(value, cached_property):
                    # name is the property name decorated with @cached_property
                    self.__dict__.pop(name, None)

    def log_request_mixin_ready_status(self):
        """
        Logs the ready status of the SmarterRequestMixin.
        """
        msg = f"{self.request_mixin_logger_prefix}.__init__() is {self.request_mixin_ready_state} - {self.url if self._url else 'URL not initialized'} - authenticated user: {self.user_profile if self.user_profile else 'Anonymous'}"
        if self.is_requestmixin_ready:
            logger.debug(msg)
        else:
            logger.warning(msg)

    def to_json(self) -> dict[str, Any]:
        """
        serializes the object.

        :return: A dictionary representation of the object.
        """
        retval = {
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
        return self.sorted_dict(retval)
