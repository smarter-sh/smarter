# pylint: disable=C0302
"""
Smarter request mixin.

This is a helper class for the Django request object that resolves
known url patterns for Smarter llmclients. Its key features are:

- lazy loading of the user, account, user profile and session_key.
- meta data for describing llmclient characteristics.
- session_key generation.
- url parsing and validation.
- url pattern recognition.
- logging.
"""

import hashlib
import re
import uuid
from datetime import datetime
from functools import cache, cached_property
from typing import Any, Optional, Union
from unittest.mock import MagicMock
from urllib.parse import ParseResult, urlparse

import tldextract
import yaml
from django.contrib.auth.models import AnonymousUser
from django.core.handlers.asgi import ASGIRequest
from django.http import HttpRequest, QueryDict
from django.http.request import RawPostDataException
from rest_framework.exceptions import ParseError
from rest_framework.request import Request as RestFrameworkRequest

from smarter.apps.account.mixins import AccountMixin, UserType
from smarter.apps.account.models import Account, User, UserProfile
from smarter.apps.account.utils import (
    account_number_from_url,
    get_cached_admin_user_for_account,
)
from smarter.common.conf import smarter_settings
from smarter.common.const import (
    SMARTER_CHAT_SESSION_KEY_NAME,
    SMARTER_IS_INTERNAL_API_REQUEST,
)
from smarter.common.exceptions import SmarterValueError
from smarter.common.helpers.url_helpers import session_key_from_url
from smarter.common.utils import (
    hash_factory,
    mask_string,
    rfc1034_compliant_to_snake,
    smarter_build_absolute_uri,
)
from smarter.lib import json, logging
from smarter.lib.django import waffle
from smarter.lib.django.models import TimestampedModel
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.typing import SmarterDictType

# Match netloc: llmclient_name.account_number.api.environment_api_domain
netloc_pattern_named_url = re.compile(
    rf"^(?P<llmclient_name>[a-zA-Z0-9\-]+)\.(?P<account_number>\d{{4}}-\d{{4}}-\d{{4}})\.api\.{re.escape(smarter_settings.environment_platform_domain)}(:\d+)?$"
)


NAMED_URL_PATHS = ("", "/config", "/prompt")
"""The paths, without a trailing slash, that a deployed LLMClient's own host serves.

See ``smarter.urls.llmclients``.
"""


STATIC_FILE_EXTENSIONS = (
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
)
"""The extensions of the static files that are never an llmclient request."""


# pylint: disable=W0613
def should_log(level: int) -> bool:
    """
    Check if logging should be done based on the waffle switch.

    :param level: The log level of the message. It is ignored: the switch turns every level on or off.
    :returns: True if the ``REQUEST_MIXIN_LOGGING`` waffle switch is active.
    """
    return waffle.switch_is_active(SmarterWaffleSwitches.REQUEST_MIXIN_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)

SmarterRequestType = Optional[Union[RestFrameworkRequest, HttpRequest, ASGIRequest, MagicMock]]
"""Type alias for all Smarter request types."""

SMARTER_REQUEST_CLASSES = (RestFrameworkRequest, HttpRequest, ASGIRequest, MagicMock)
"""The classes of :data:`SmarterRequestType`, for ``isinstance()``."""


@cache
def cached_property_names(cls: type) -> frozenset[str]:
    """
    Return the names of a class's ``@cached_property`` attributes, including inherited ones.

    A class's attributes don't change after it is defined, so each class is inspected once.

    :param cls: The class.
    :returns: The attribute names.
    """
    names = set()
    for klass in cls.__mro__:
        for name, value in vars(klass).items():
            if isinstance(value, cached_property):
                names.add(name)
    return frozenset(names)


class SmarterRequestMixin(AccountMixin):
    """
    Helper class for the Django request object that enforces authentication and provides lazy loading of the user, account, user profile, and session_key.

    This mixin works with any Django request object and any valid URL, but is designed
    as a helper class for Smarter LLMClient URLs.

    .. note::
        The request object is an optional positional argument due to Django view lifecycles,
        which do not recognize the request object until after class ``__init__()``.
        ``SmarterRequestMixin`` is included as a mixin in the Smarter base view classes.

    **Valid endpoints:**

    1. Root endpoints for named URLs (public or authenticated chats)
       (``self.is_llmclient_named_url == True``)

       - ``http://example.3141-5926-5359.api.localhost:9357/`` → ``smarter.apps.llmclient.api.v1.views.default.DefaultLLMClientApiView``
       - ``http://example.3141-5926-5359.api.localhost:9357/config`` → ``smarter.apps.prompt.views.PromptConfigView``

    2. Authenticated sandbox endpoints (authenticated chats)
       (``self.is_llmclient_sandbox_url == True``)

       - ``http://localhost:9357/workbench/<str:name>/`` → ``smarter.apps.prompt.views.PromptWorkbenchView``
       - ``http://localhost:9357/workbench/<str:name>/config/`` → ``smarter.apps.prompt.views.PromptConfigView``

    3. smarter.sh/v1 endpoints (public or authenticated chats)
       (``self.is_llmclient_smarter_api_url == True``)

       - ``http://localhost:9357/api/v1/workbench/<int:llmclient_id>/prompt/`` → ``smarter.apps.llmclient.api.v1.views.default.DefaultLLMClientApiView``
       - ``http://localhost:9357/api/v1/workbench/<int:llmclient_id>/prompt/config/`` → ``smarter.apps.prompt.views.PromptConfigView``

    4. Command-line interface API endpoints (authenticated chats)
       (``self.is_llmclient_cli_api_url == True``)

       - ``http://localhost:9357/api/v1/cli/prompt/<str:name>/`` → ``smarter.apps.llmclient.api.v1.cli.views.nonbrokered.prompt.ApiV1CliPromptApiView``
       - ``http://localhost:9357/api/v1/cli/prompt/config/<str:name>/`` → ``smarter.apps.llmclient.api.v1.cli.views.nonbrokered.chat_config.ApiV1CliPromptConfigApiView``

    5. Other endpoints (possibly deprecated or unused)
       - ``http://localhost:9357/api/v1/prompt/``

    **Example URLs:**

    - ``http://testserver``
    - ``http://localhost:9357/``
    - ``http://localhost:9357/docs/``
    - ``http://localhost:9357/dashboard/``
    - ``https://alpha.platform.smarter.sh/api/v1/workbench/1/llm-client/``
    - ``http://example.com/contact/``
    - ``http://localhost:9357/workbench/example/config/?session_key=...``
    - ``https://hr.3141-5926-5359.alpha.api.example.com/``
    - ``https://hr.3141-5926-5359.alpha.api.example.com/config/?session_key=...``
    - ``http://example.3141-5926-5359.api.localhost:9357/``
    - ``http://example.3141-5926-5359.api.localhost:9357/?session_key=...``
    - ``http://example.3141-5926-5359.api.localhost:9357/config/``
    - ``http://example.3141-5926-5359.api.localhost:9357/config/?session_key=...``
    - ``http://localhost:9357/api/v1/workbench/1/prompt/``
    - ``http://localhost:9357/api/v1/cli/prompt/smarter/?new_session=false&uid=mcdaniel``
    - ``https://hr.smarter.sh/``

    :ivar session_key: Unique identifier for a prompt session, generated by :meth:`generate_session_key`.
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
        "_srm_ready",
    )

    # pylint: disable=W0613
    def __init__(self, *args, request: Optional[HttpRequest] = None, **kwargs):
        self._instance_id = id(self)
        self._smarter_request: Optional[HttpRequest] = None
        self._smarter_request_user: Optional[UserType] = None
        self._timestamp = datetime.now()
        self._url: Optional[ParseResult] = None
        self._url_account_number: Optional[str] = None
        self._parsed_url: Optional[ParseResult] = None
        self._params: Optional[QueryDict] = None
        self._session_key: Optional[str] = kwargs.pop("session_key", None)
        self._data: Optional[SmarterDictType] = None
        self._cache_key: Optional[str] = None
        self._srm_ready: bool = False

        # Each of these is taken from its keyword argument, or else from the first positional
        # argument of its class.
        if not request:
            request = next((arg for arg in args if isinstance(arg, SMARTER_REQUEST_CLASSES)), None)
        # the arguments that are passed to the parent AccountMixin class.
        user = kwargs.pop("user", None)
        if not user:
            user = next((arg for arg in args if isinstance(arg, User)), None)
        if user:
            self._smarter_request_user = user
        user_profile = kwargs.pop("user_profile", None)
        if not user_profile:
            user_profile = next((arg for arg in args if isinstance(arg, UserProfile)), None)
        account = kwargs.pop("account", None)
        if not account:
            account = next((arg for arg in args if isinstance(arg, Account)), None)
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
            return None

        if not self.smarter_request:
            raise SmarterValueError(
                f"{self.srm_formatted_class_name}.__init__() - did not find a request object. SmarterRequestMixin cannot be initialized."
            )

        # A deployed LLMClient's host is public: a caller who is signed in to another account keeps
        # its own account. Only an anonymous caller takes the url's account (see eval_llmclient_url).
        if self.parsed_url and self.is_llmclient_named_url:
            self._url_account_number = self.url_account_number

        self.eval_llmclient_url()
        self._srm_log_ready_status()

    def __str__(self) -> str:
        """
        String representation of the instance, naming its concrete class.

        :returns: A string describing the instance.
        """
        return (
            f"{self.__class__.__name__}[{id(self)}](request={self.smarter_request}, user_profile={self.user_profile})"
        )

    def __repr__(self) -> str:
        """
        Developer representation of the instance, which is the same as :meth:`__str__`.

        :returns: A string representation suitable for debugging.
        """
        return self.__str__()

    def __bool__(self) -> bool:
        """
        Boolean representation of the SmarterRequestMixin instance.

        :returns: True if the instance is srm_ready, False otherwise, including when checking raises.
        """
        try:
            return self.srm_ready
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.__bool__() - encountered an error while checking srm_ready: %s",
                self.srm_formatted_class_name,
                e,
                exc_info=True,
            )
            return False

    def __hash__(self) -> int:
        """
        Hash representation of the SmarterRequestMixin instance.

        :returns: An integer hash of the instance's url and user profile.
        """
        return hash(
            (
                self.url,
                self.user_profile,
            )
        )

    def __eq__(self, other: object) -> bool:
        """
        Equality comparison for SmarterRequestMixin instances, by url and user_profile.

        :param other: Another object to compare.
        :returns: True if the instances are equal, or ``NotImplemented`` if
            ``other`` is not a :class:`SmarterRequestMixin`.
        """
        if not isinstance(other, SmarterRequestMixin):
            return NotImplemented
        return self.url == other.url and self.user_profile == other.user_profile

    def setup(self, *args, request: Optional[HttpRequest] = None, user: Optional[UserType] = None, **kwargs):
        """
        Setup method to initialize the SmarterRequestMixin with the request and user.

        This method is called during the setup phase of a Django view. It initializes
        the request and user attributes of the mixin. The request is set using the
        smarter_request property setter, which also handles URL parsing and user authentication.

        :param args: Positional arguments passed to the setup method.
        :param request: The HTTP request object to be associated with this mixin instance.
        :param user: The user associated with the request, if available.
        :param kwargs: Keyword arguments passed to the setup method.
        """
        logger.debug(
            "%s.setup() called with args: %s, kwargs: %s, request: %s, user: %s",
            self.srm_formatted_class_name,
            args,
            kwargs,
            request,
            user,
        )
        self.smarter_request = request
        super().setup(*args, user=user, **kwargs)

    def invalidate_cached_properties(self):
        """
        Invalidates all cached properties on the instance to force re-evaluation.

        This method removes all attributes cached by ``@cached_property`` decorators
        from the instance's ``__dict__``. It is useful for testing or when the request
        object changes and you need to ensure that all dependent properties are recalculated.

        Example::

            from smarter.lib.django.request import SmarterRequestMixin

            class Foo(SmarterRequestMixin):
                pass

            foo = Foo(request)
            foo.invalidate_cached_properties()
        """
        for name in cached_property_names(type(self)):
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

        :returns: The current request object.
        """
        return self._smarter_request

    @smarter_request.setter
    def smarter_request(self, request: SmarterRequestType):
        """
        Set the request, clear the cached properties and parsed data, and resolve the request's user.

        :param request: The request, or None.
        :raises SmarterValueError: If the request's absolute url can't be built, or its user differs
            from the user already set.
        """
        self.clear_cached_properties()
        self._smarter_request = request
        self._data = None
        if request is not None:
            url = smarter_build_absolute_uri(request)
            if not url:
                raise SmarterValueError(
                    f"{self.srm_formatted_class_name}.smarter_request setter - could not build url from request: {request}"
                )
            self._url = urlparse(url)

            if self.is_authenticated:
                if not self.user:
                    self._smarter_request_user = request.user  # type: ignore
                    self.user = self._smarter_request_user
                else:
                    if (self.user != request.user) and not isinstance(self.user, AnonymousUser):
                        raise SmarterValueError(
                            f"{self.srm_formatted_class_name}.smarter_request setter - user mismatch: existing user: {self.user}, request user: {request.user}"
                        )
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
        Returns the user associated with the request.

        This property is named to avoid potential name collisions in child classes.
        It retrieves the user from the request object if available.

        Example::

            request_mixin = SmarterRequestMixin(request)
            user = request_mixin.smarter_request_user

        :returns: The user associated with the request, or None if not available.
        """
        return self._smarter_request_user

    def _header(self, name: str) -> Optional[str]:
        """
        Return the value of a request header.

        :param name: The header's name, e.g. ``"Authorization"``.
        :returns: The header's value, or None if there is no request, the request has no
            headers, or the header is missing.
        """
        if not self._smarter_request:
            return None
        if not hasattr(self._smarter_request, "headers"):
            return None
        return self._smarter_request.headers.get(name)

    @property
    def smarter_client(self) -> Optional[str]:
        """
        Get the smarter client name from the request.

        This property checks for the "X-Smarter-Client" header in the request headers.

        Example::

            request_mixin = SmarterRequestMixin(request)
            client_name = request_mixin.smarter_client

        :returns: The value of the "X-Smarter-Client" header as a string, or None if not present.
        """
        return self._header("X-Smarter-Client")

    @property
    def smarter_client_version(self) -> Optional[str]:
        """
        Get the smarter client version from the request.

        This property checks for the "X-Smarter-ClientVersion" header in the request headers.

        Example::

            request_mixin = SmarterRequestMixin(request)
            client_version = request_mixin.smarter_client_version

        :returns: The value of the "X-Smarter-ClientVersion" header as a string, or None if not present.
        """
        return self._header("X-Smarter-ClientVersion")

    @property
    def smarter_client_type(self) -> Optional[str]:
        """
        Get the smarter client type from the request.

        This property checks for the "X-Smarter-ClientType" header in the request headers.

        Example::

            request_mixin = SmarterRequestMixin(request)
            client_type = request_mixin.smarter_client_type

        :returns: The value of the "X-Smarter-ClientType" header as a string, or None if not present.
        """
        return self._header("X-Smarter-ClientType")

    @property
    def smarter_request_id(self) -> Optional[str]:
        """
        Get the smarter request ID from the request.

        This property checks for the "X-Smarter-RequestId" header in the request headers.

        Example::

            request_mixin = SmarterRequestMixin(request)
            request_id = request_mixin.smarter_request_id

        :returns: The value of the "X-Smarter-RequestId" header as a string, or None if not present.
        """
        return self._header("X-Smarter-RequestId")

    def generate_smarter_request_id(self) -> str:
        """
        Generate a unique identifier for the request.

        :returns: A random uuid4, as 32 hexadecimal characters.
        """
        return uuid.uuid4().hex

    @property
    def smarter_capabilities(self) -> Optional[str]:
        """
        Get the smarter capabilities from the request.

        This property checks for the "X-Smarter-Capabilities" header in the request headers.

        Example::

            request_mixin = SmarterRequestMixin(request)
            capabilities = request_mixin.smarter_capabilities

        :returns: The value of the "X-Smarter-Capabilities" header as a string, or None if not present.
        """
        return self._header("X-Smarter-Capabilities")

    @property
    def auth_header(self) -> Optional[str]:
        """
        Get the Authorization header from the request.

        Example::

            request_mixin = SmarterRequestMixin(request)
            print(request_mixin.auth_header)

        This property checks for the "Authorization" header in the request headers.

        :returns: The value of the "Authorization" header as a string, or None if not present.
        """
        return self._header("Authorization")

    @cached_property
    def api_token(self) -> Optional[bytes]:
        """
        Get the API token from the request's ``Authorization`` header.

        The header's value is ``Token <key>`` or ``Bearer <key>``.

        Example::

            request_mixin = SmarterRequestMixin(request)
            token = request_mixin.api_token

        :returns: The API token as bytes, or None if the header is missing or has neither prefix.
        """
        if isinstance(self.auth_header, str) and self.auth_header.startswith("Token "):
            return self.auth_header.split("Token ")[1].encode()

        if isinstance(self.auth_header, str) and self.auth_header.startswith("Bearer "):
            return self.auth_header.split("Bearer ")[1].encode()
        return None

    @cached_property
    def qualified_request(self) -> bool:
        """
        A cursory screening of the WSGI request object to look for any disqualifying conditions that confirm this is not a request that we are interested in.

        The request is considered "qualified" if **all** of the following are true:

        - The request object (``self._smarter_request``) is present.
        - The URL path is present and non-empty.
        - The request does **not** originate from an internal AWS Kubernetes subnet (netloc starts with ``192.168``).
        - The path is **not** in the list of ``amnesty_urls``.
        - The path does **not** start with ``/admin/``.
        - The path does **not** start with ``/docs/``.
        - The path does **not** end with a static file extension (see :data:`STATIC_FILE_EXTENSIONS`).

        Example::

            # True case: a valid llmclient request
            request_mixin = SmarterRequestMixin(request)
            if request_mixin.qualified_request:
                print("This is a qualified llmclient request.")

            # False case: a static asset or admin/docs request
            static_request = SmarterRequestMixin(static_asset_request)
            if not static_request.qualified_request:
                print("This request is not of interest.")

        :returns: True if the request passes all checks and is of interest, otherwise False.
        """
        if not self._smarter_request:
            return False
        parsed_url = self.parsed_url
        path = parsed_url.path if parsed_url else None
        if not path:
            return False

        if parsed_url and parsed_url.netloc.startswith("192.168"):
            # internal processes running in a AWS kubernetes internal subnet.
            # definitely not an llmclient request.
            return False

        if path in self.amnesty_urls:
            # amnesty urls are not llmclient requests.
            return False

        if self.url_path_parts and self.url_path_parts[0] in ("admin", "docs"):
            return False

        if isinstance(path, str) and path.replace("/", "").endswith(STATIC_FILE_EXTENSIONS):
            # static asset requests are not llmclient requests.
            return False

        return True

    @property
    def url(self) -> Optional[str]:
        """
        The string representation of the ParseResult object stored in _parsed_url.

        Example::

            request_mixin = SmarterRequestMixin(request)
            url_str = request_mixin.url
            print(url_str)  # e.g., 'https://example.com/path/'

        :returns: The URL as a string.
        """
        if not self.smarter_request:
            return None
        if self._url:
            if isinstance(self._url, ParseResult):
                return self._url.geturl()
            try:
                url = SmarterValidator.urlify(self._url)
                parsed = urlparse(url)
                base_url = parsed._replace(query="", fragment="").geturl()
                if isinstance(base_url, ParseResult):
                    raise SmarterValueError("Unexpected ParseResult type for base_url.")
                return base_url
            except SmarterValueError as e:
                logger.error(
                    "%s.url() property encountered an error while validating URL: %s",
                    self.srm_formatted_class_name,
                    e,
                )
                return None

        logger.warning(
            "%s.url() property was accessed before it was initialized. request: %s",
            self.srm_formatted_class_name,
            self.smarter_request,
        )
        return None

    @property
    def parsed_url(self) -> Optional[ParseResult]:
        """
        Expose the private ParseResult URL object as a public property.

        Example::

            request_mixin = SmarterRequestMixin(request)
            parsed = request_mixin.parsed_url
            print(parsed.netloc)  # e.g., 'example.com'

        :returns: The parsed URL, or None if there is no url.
        """
        if self._parsed_url is None:
            if isinstance(self._url, ParseResult) and self.smarter_request:
                # already parsed by the smarter_request setter, or by a subclass.
                self._parsed_url = self._url
            else:
                url = self.url
                self._parsed_url = urlparse(url) if isinstance(url, str) else None
        return self._parsed_url

    @cached_property
    def url_path_parts(self) -> list[str]:
        """
        Extract the path parts from the URL.

        Example::

            request_mixin = SmarterRequestMixin(request)
            parts = request_mixin.url_path_parts
            print(parts)  # e.g., ['api', 'v1', 'workbench', '1', 'prompt']

        :returns: A list of strings representing each part of the URL path.
        """
        if not self.parsed_url:
            return []
        path = self.parsed_url.path
        if isinstance(path, bytes):
            path = path.decode("utf-8")
        return path.strip("/").split("/")

    @cached_property
    def params(self) -> QueryDict:
        """
        The query string parameters from the Django request object.

        This extracts the query string parameters from the request object and converts them to a dictionary.
        Used in child views to pass optional command-line parameters to the broker.

        Example::

            request_mixin = SmarterRequestMixin(request)
            params = request_mixin.params
            print(params)  # e.g., {'session_key': 'abc123', 'uid': 'xyz'}

        :returns: QueryDict containing the query string parameters.
        """
        if not self.smarter_request:
            logger.warning(
                "%s.params() - request is None or not set. Cannot extract query string parameters.",
                self.srm_formatted_class_name,
            )
            return QueryDict("")
        if not hasattr(self.smarter_request, "META"):
            logger.warning(
                "%s.params() - request does not have META attribute. Cannot extract query string parameters.",
                self.srm_formatted_class_name,
            )
            return QueryDict("")
        if self.smarter_request.META is None:
            logger.warning(
                "%s.params() - request.META is None. Cannot extract query string parameters.",
                self.srm_formatted_class_name,
            )
            return QueryDict("")
        # Always construct QueryDict, even if QUERY_STRING is empty
        query_string = self.smarter_request.META.get("QUERY_STRING", "")
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

        Example::

            request_mixin = SmarterRequestMixin(request)
            uid = request_mixin.uid
            print(uid)  # e.g., '00:1A:2B:3C:4D:5E-myhost'

        :returns: The client UID as a string, or None if not available.
        """
        return self.params.get("uid") if isinstance(self.params, QueryDict) else None

    @cached_property
    def cache_key(self) -> Optional[str]:
        """
        Returns a cache key for the request.

        This is used to cache the prompt request thread. The key is the sha256 hash of:

        - the class name,
        - the request's user, or ``"Anonymous"``,
        - and the client UID (:attr:`uid`), or ``"unknown_uid"``.

        Currently used by the ApiV1CliPromptConfigApiView and ApiV1CliPromptApiView as a means of sharing the session_key.

        Example::

            request_mixin = SmarterRequestMixin(request)
            key = request_mixin.cache_key
            print(key)  # e.g., 'a1b2c3d4e5f6...'

        :returns: A unique cache key string, or None if there is no request.
        """
        if self._cache_key:
            return self._cache_key

        if not self.smarter_request:
            logger.warning(
                "%s.cache_key() - request is None or not set. Cannot generate cache key.",
                self.srm_formatted_class_name,
            )
            return None

        uid = self.uid or "unknown_uid"
        username = getattr(self.smarter_request, "user", "Anonymous")
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

        The session_key is a unique identifier for a prompt session.
        It is used to identify the prompt session across multiple requests.
        If the session_key is not already set, it attempts to find it
        in the request (see :meth:`find_session_key`). Barring that, it generates a new one.

        Example::

            request_mixin = SmarterRequestMixin(request)
            session_key = request_mixin.session_key
            print(session_key)  # e.g., '38486326c21ef4bcb7e7bc305bdb062f16ee97ed8d2462dedb4565c860cd8ecc'

        :returns: The session key as a string.
        """
        if not self._session_key:
            session_key = self.find_session_key()
            if not session_key:
                session_key = self.generate_session_key()
            self._session_key = session_key
            SmarterValidator.validate_session_key(self._session_key)
        return self._session_key

    @cached_property
    def smarter_request_llmclient_id(self) -> Optional[int]:
        """
        Extract the llmclient id from the URL.

        For example, for this url the property decodes the hashed id ``rMTAwMDAyNwx`` into the
        llmclient's id::

            http://localhost:9357/workbench/llm-clients/rMTAwMDAyNwx/prompt/

        :returns: The llmclient id as an integer, or None if not found. A named url and a sandbox
            url without a hashed id return None.
        """
        if not self.is_llmclient:
            return None

        # Search only the path: a host name such as repo-explorer is never a hashed id.
        hashed_id = None
        if self.parsed_url:
            hashed_id = TimestampedModel.find_hash(self.parsed_url.path)
        if hashed_id:
            return TimestampedModel.id_from_hashed_id(hashed_id)

        if self.is_llmclient_smarter_api_url:
            path_parts = self.url_path_parts
            if not isinstance(path_parts, list):
                return None
            if len(path_parts) <= 3:
                return None
            return int(path_parts[3])

        if self.is_llmclient_named_url:
            # can't get from LLMClient bc of circular import
            return None

        if self.is_llmclient_sandbox_url:
            return None

        return None

    @property
    def url_account_number(self) -> Optional[str]:
        """
        Extract the account number from the URL, using ``SmarterValidator.VALID_ACCOUNT_NUMBER_PATTERN``.

        For example, this url returns ``"3141-5926-5359"``::

            http://example.3141-5926-5359.api.localhost:9357/config

        :returns: The account number as a string, or None if there is no request, the request is
            not qualified, or the url has no account number.
        """
        if self._url_account_number:
            return self._url_account_number

        if not self.smarter_request:
            return None
        if not self.qualified_request:
            return None
        self._url_account_number = account_number_from_url(url=self.url)
        return self._url_account_number

    @cached_property
    def smarter_request_llmclient_name(self) -> Optional[str]:
        """
        Extract the llmclient name from the URL.

        For example, this url returns ``"example"``::

            http://example.3141-5926-5359.api.localhost:9357/config

        :returns: The llmclient name as a string, or None if not found.
        """
        if not self.is_llmclient:
            return None

        # 1.) http://example-username.api.localhost:9357/config
        if self.is_llmclient_named_url and self.parsed_url is not None:
            netloc = self.parsed_url.netloc
            first_label = None
            if netloc:
                first_label = netloc.split(".")[0]
            return self._llmclient_name_from_url_part(first_label)

        # 2.) example: http://localhost:9357/workbench/<str:name>/config/
        if self.is_llmclient_sandbox_url:
            try:
                return self._llmclient_name_from_url_part(self.url_path_parts[1])
            # pylint: disable=broad-except
            except Exception:
                logger.error(
                    "%s.smarter_request_llmclient_name() - failed to extract llmclient name from sandbox url: %s",
                    self.srm_formatted_class_name,
                    self.url,
                )

        # 3.) http://localhost:9357/api/v1/workbench/<int:llmclient_id>
        # no name. nothing to do in this case.
        if self.is_llmclient_smarter_api_url:
            return None

        # 4.) http://localhost:9357/api/v1/cli/prompt/config/<str:name>/
        #     http://localhost:9357/api/v1/cli/prompt/<str:name>/
        if self.is_llmclient_cli_api_url:
            try:
                return self._llmclient_name_from_url_part(self.url_path_parts[-1])
            # pylint: disable=broad-except
            except Exception:
                logger.error(
                    "%s.smarter_request_llmclient_name() - failed to extract llmclient name from cli url: %s",
                    self.srm_formatted_class_name,
                    self.url,
                )

        return None

    @staticmethod
    def _llmclient_name_from_url_part(part: Optional[str]) -> Optional[str]:
        """
        Convert a part of a url, a host label or a path segment, to an llmclient name.

        A hyphenated part is cut at its first hyphen, and the rest is converted from an
        RFC 1034 compliant name to snake case.

        :param part: The url part, or None.
        :returns: The llmclient name, or None if ``part`` is None.
        """
        name = part
        if name and "-" in name:
            name = name.split("-")[0]
        if isinstance(name, str):
            name = rfc1034_compliant_to_snake(name)
        return name

    @property
    def timestamp(self) -> datetime:
        """
        Create a consistent timestamp based on the time that this object was instantiated.

        Example::

            request_mixin = SmarterRequestMixin(request)
            ts = request_mixin.timestamp
            print(ts)  # e.g., 2025-12-01 12:34:56.789012

        :returns: The time at which this object was instantiated.
        """
        return self._timestamp

    @cached_property
    def data(self) -> Optional[Union[SmarterDictType, list[Any], str]]:
        """
        Get the request body data as a dictionary, list or str.

        Used for setting the session_key.

        Example::

            request_mixin = SmarterRequestMixin(request)
            data = request_mixin.data
            print(data)  # e.g., {'session_key': 'abc123', ...}

        :returns: The request body parsed as json or yaml, an empty dict if the body is empty or
            can't be parsed, or None if there is no request or the request is not qualified.
        """
        if self._data:
            return self._data

        body: Union[SmarterDictType, bytes, str, bytearray, None] = None
        body_str: Union[SmarterDictType, bytes, str, bytearray, None] = None

        if not self.smarter_request:
            return None
        if not self.qualified_request:
            return None
        if isinstance(self.smarter_request, RestFrameworkRequest) and "multipart" not in (
            self.smarter_request.content_type or ""
        ):
            # DRF's .data consumes the request stream. Read the raw body first, which Django
            # caches, so that plan-B below can still parse it if DRF's parser rejects it.
            # For example, the cli sends yaml manifests with a json content type.
            try:
                self.smarter_request.body  # pylint: disable=pointless-statement
            except RawPostDataException:
                pass
        try:
            # plan-A is to use .data attribute if available (DRF Request)
            # and created with our custom smarter.lib.drf.parsers.YAMLParser()
            # which populates .data with parsed YAML or JSON.
            body_str = self.smarter_request.data  # type: ignore
        except (AttributeError, ParseError):
            body_str = None
        if not body_str and "multipart" not in (getattr(self.smarter_request, "content_type", None) or ""):
            # after a ParseError, DRF caches empty data, so later calls get {} instead of an error.
            try:
                body = self.smarter_request.body
            except RawPostDataException as e:
                logger.error(
                    "%s.data() - failed to read request body due to RawPostDataException: %s",
                    self.srm_formatted_class_name,
                    e,
                )
            if not isinstance(body, (str, bytearray, bytes)):
                logger.warning(
                    "%s.data() - request body is not a string or bytes. Cannot parse request body: %s",
                    self.srm_formatted_class_name,
                    body,
                )
            try:
                if isinstance(body, (bytearray, bytes)):
                    body_str = body.decode("utf-8").strip()
            except (AttributeError, UnicodeDecodeError):
                logger.warning(
                    "%s.data() - request body could not be decoded as utf-8: %s", self.srm_formatted_class_name, body
                )
                body_str = body if isinstance(body, str) else None

        if body_str is not None:
            try:
                if isinstance(body_str, (dict, list)):
                    self._data = body_str  # type: ignore
                elif isinstance(body_str, (str, bytearray, bytes)):
                    self._data = json.loads(body_str)
                else:
                    self._data = None
            except json.JSONDecodeError:
                try:
                    if isinstance(body_str, bytearray):
                        # yaml reads str or bytes, not bytearray.
                        body_str = bytes(body_str)
                    self._data = yaml.safe_load(body_str) if isinstance(body_str, (str, bytes)) else None
                except yaml.YAMLError:
                    logger.error(
                        "%s.data() - failed to parse request body: %s",
                        self.srm_formatted_class_name,
                        body_str,
                    )

        self._data = self._data or {}
        return self._data

    @property
    def unique_client_string(self) -> str:
        """
        Generate a unique string based on several request attributes.

        This string is used for generating ``session_key`` and ``client_key``.

        The unique string is composed of:

        - Account number, when there is an account
        - URL
        - User agent
        - IP address

        Example::

            request_mixin = SmarterRequestMixin(request)
            unique_str = request_mixin.unique_client_string
            print(unique_str)

        :returns: A unique string representing the client and request context.
        """
        if not self.account:
            return f"{self.url}{self.user_agent}{self.ip_address}"
        return f"{self.account.account_number}{self.url}{self.user_agent}{self.ip_address}"

    @cached_property
    def ip_address(self) -> Optional[str]:
        """
        Get the client's IP address from the request object.

        This property attempts to extract the IP address from the request's META dictionary,
        using the ``REMOTE_ADDR`` key.

        Example::

            request_mixin = SmarterRequestMixin(request)
            ip = request_mixin.ip_address
            print(ip)  # e.g., '192.168.1.100'

        :returns: The client's IP address, the placeholder ``"ip_address"`` if ``REMOTE_ADDR`` is
            missing or empty, or None if the request has no META dictionary.
        """
        if (
            self.smarter_request is not None
            and hasattr(self.smarter_request, "META")
            and isinstance(self.smarter_request.META, dict)
        ):
            return self.smarter_request.META.get("REMOTE_ADDR", "") or "ip_address"
        return None

    @property
    def user_agent(self) -> Optional[str]:
        """
        Get the client's user agent string from the request object.

        This property attempts to extract the user agent from the request's META dictionary,
        using the ``HTTP_USER_AGENT`` key.

        Example::

            request_mixin = SmarterRequestMixin(request)
            ua = request_mixin.user_agent
            print(ua)  # e.g., 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)...'

        :returns: The client's user agent string, the placeholder ``"user_agent"`` if the header is
            missing, or None if the request has no META dictionary.
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
        Return True if the URL resolves to a config endpoint.

        Examples::

            http://testserver/api/v1/cli/prompt/config/testc7098865f39202d5/
            http://localhost:9357/workbench/example/config/?session_key=1aeee4c1f183354247f43f80261573da921b0167c7c843b28afd3cb5ebba0d9a
            http://localhost:9357/api/v1/workbench/<int:llmclient_id>/prompt/config/
            http://example.api.localhost:9357/config

        :returns: True if the URL is an llmclient url whose path includes ``config``, otherwise False.
        """
        if not self.is_llmclient:
            return False
        if not isinstance(self.url_path_parts, list):
            return False
        if "config" not in self.url_path_parts:
            return False
        return True

    @cached_property
    def is_dashboard(self) -> bool:
        """
        Return True if the URL resolves to a dashboard endpoint.

        :returns: True if the URL's path ends with ``/dashboard/``, otherwise False.
        """
        if not self.smarter_request:
            return False
        if not isinstance(self.url_path_parts, list):
            return False
        if len(self.url_path_parts) == 0:
            return False
        try:
            if self.url_path_parts[-1] != "dashboard":
                return False
            if self.parsed_url and "/dashboard/" not in self.parsed_url.path:
                return False
            return True
        except IndexError:
            return False

    @cached_property
    def is_workbench(self) -> bool:
        """
        Return True if the URL resolves to a workbench endpoint.

        :returns: True if the URL's path ends with ``/workbench/``, otherwise False.
        """
        if not self.smarter_request:
            return False
        if not isinstance(self.url_path_parts, list):
            return False
        if len(self.url_path_parts) == 0:
            return False
        try:
            if self.url_path_parts[-1] != "workbench":
                return False
            if self.parsed_url and "/workbench/" not in self.parsed_url.path:
                return False
            return True
        except IndexError:
            return False

    @cached_property
    def is_environment_root_domain(self) -> bool:
        """
        Return True if the URL resolves to the environment root domain.

        :returns: True if the URL's host is the environment's platform domain and its path is
            ``/``, otherwise False.
        """
        if not self.smarter_request:
            return False
        if not self.parsed_url:
            return False
        if self.parsed_url.netloc != smarter_settings.environment_platform_domain:
            return False
        if self.parsed_url.path != "/":
            return False
        return True

    @cached_property
    def is_llmclient(self) -> bool:
        """
        Return True if the URL resolves to an llmclient endpoint.

        Conditions are checked in a lazy sequence to avoid unnecessary processing. The order
        matters: :attr:`is_llmclient_named_url` loads the url's account as a side effect.

        Examples::

            http://localhost:9357/api/v1/prompt/1/prompt/
            http://localhost:9357/api/v1/cli/prompt/example/
            http://example.3141-5926-5359.api.localhost:9357/
            http://localhost:9357/api/v1/llm-clients/1556/prompt/
            http://localhost:9357/workbench/llm-clients/<str:hashed_id>/prompt/
            http://localhost:9357/workbench/llm-clients/<str:hashed_id>/config/
            http://localhost:9357/workbench/llm-clients/<str:hashed_id>/manifest/

        :returns: True if the request is qualified and its URL is a named, sandbox, smarter api
            or cli api llmclient url, otherwise False.
        """
        if not self.qualified_request:
            return False
        if self.is_llmclient_named_url:
            return True
        if self.is_llmclient_sandbox_url:
            return True
        if self.is_llmclient_smarter_api_url:
            return True
        if self.is_llmclient_cli_api_url:
            return True
        return False

    @cached_property
    def is_smarter_api(self) -> bool:
        """
        Return True if the URL is of the form ``http://localhost:9357/api/v1/``.

        Examples::

            path_parts: ['api', 'v1', 'llm-clients', '1', 'prompt']
            http://api.localhost:9357/

        :returns: True if ``api`` is a segment of the URL's path or a label of its host, otherwise False.
        """
        if not self.smarter_request:
            return False
        if not self.url:
            return False

        # Check for 'api' in path parts or in the host (netloc)
        in_path = isinstance(self.url_path_parts, list) and "api" in self.url_path_parts
        in_host = self.parsed_url and "api" in self.parsed_url.netloc.split(".")
        if in_path or in_host:
            return True

        return False

    @cached_property
    def is_llmclient_smarter_api_url(self) -> bool:
        """
        Return True if the URL is a smarter api llmclient endpoint.

        These are the forms of the url::

            http://localhost:9357/api/v1/llm-clients/32/config/

            http://localhost:9357/api/v1/workbench/1/prompt/
            path_parts: ['api', 'v1', 'workbench', '<int:pk>', 'prompt']

            http://localhost:9357/api/v1/llm-clients/1556/prompt/
            path_parts: ['api', 'v1', 'llm-clients', '<int:pk>', 'prompt']

            http://localhost:9357/api/v1/llm-clients/rMTAwMDAwNwx/prompt/
            path_parts: ['api', 'v1', 'llm-clients', '<str:hashed_id>', 'prompt']

        :returns: True if the URL matches a smarter API llmclient endpoint, otherwise False.
        """
        if not self.qualified_request:
            return False
        if not self.parsed_url:
            return False

        if not isinstance(self.url_path_parts, list):
            return False
        if len(self.url_path_parts) != 5:
            return False
        if self.url_path_parts[0] != "api":
            return False
        if self.url_path_parts[1] != "v1":
            return False
        if self.url_path_parts[2] not in ["workbench", "llm-clients"]:
            return False
        if not (self.url_path_parts[3].isnumeric() or TimestampedModel.hash_regex().fullmatch(self.url_path_parts[3])):
            # expecting <int:pk> or <str:hashed_id>: ['api', 'v1', 'llm-clients', '<int:pk>', 'prompt']
            return False
        if self.url_path_parts[4] not in ["prompt", "config"]:
            # expecting 'prompt' or 'config' at the end of the path_parts: ['api', 'v1', 'workbench', '<int:pk>', 'prompt']
            return False

        return True

    @cached_property
    def is_llmclient_cli_api_url(self) -> bool:
        """
        Return True if the URL is of the form ``http://localhost:9357/api/v1/cli/prompt/example/``.

        The expected path parts are::

            ['api', 'v1', 'cli', 'prompt', 'example']

        :returns: True if the URL matches the CLI llmclient API pattern, otherwise False.
        """
        if not self.smarter_request:
            return False
        if not self.is_smarter_api:
            return False

        path_parts = self.url_path_parts
        try:
            if path_parts[2] != "cli":
                return False
            if path_parts[3] != "prompt":
                return False
        except IndexError:
            return False

        return True

    @cached_property
    def is_llmclient_named_url(self) -> bool:
        """
        Return True if the url is a deployed LLMClient's own host.

        These are the forms of the url::

            https://example-username.3141-5926-5359.api.example.com/
            http://example-username.3141-5926-5359.api.localhost:9357/
            http://example-username.3141-5926-5359.api.localhost:9357/config/
            http://example-username.3141-5926-5359.api.localhost:9357/prompt/

        As a side effect, when the url has an account number and :attr:`account` is not set,
        the account is loaded from the account number.

        :returns: True if the URL matches the named llmclient pattern, otherwise False.
        """
        if not self.qualified_request:
            return False
        if not self.url:
            return False
        if smarter_settings.environment_api_domain not in self.url:
            return False

        # Accept only the paths that a deployed LLMClient's own host serves, with or without a
        # trailing slash. This comes before the account number, which every path of the host has.
        if isinstance(self.parsed_url, ParseResult) and self.parsed_url.path.rstrip("/") not in NAMED_URL_PATHS:
            return False

        account_number = self.url_account_number
        if account_number is not None:
            if self.account is None:
                # lazy load the account from the account number
                self.account = Account.get_cached_object(account_number=account_number)
            return True

        if isinstance(self.parsed_url, ParseResult) and netloc_pattern_named_url.match(self.parsed_url.netloc):
            return True

        return False

    @cached_property
    def is_llmclient_sandbox_url(self) -> bool:
        """
        Return True if the URL is an llmclient sandbox endpoint.

        Web console urls::

            http://localhost:9357/workbench/llm-clients/<str:hashed_id>/prompt/
            http://localhost:9357/workbench/llm-clients/<str:hashed_id>/config/
            http://localhost:9357/workbench/llm-clients/<str:hashed_id>/manifest/

        Api urls::

            http://localhost:9357/api/v1/prompt/1/prompt/

        :returns: True if the URL matches an llmclient sandbox endpoint, otherwise False.
        """
        if not self.qualified_request:
            return False
        if not self.parsed_url:
            logger.warning("%s.is_llmclient_sandbox_url() - url is None or not set.", self.srm_formatted_class_name)
            return False

        # smarter api - http://localhost:9357/api/v1/prompt/1/prompt/
        path_parts = self.url_path_parts
        if (
            len(path_parts) == 5
            and path_parts[0] == "api"
            and path_parts[1] == "v1"
            and path_parts[2] == "prompt"
            and path_parts[3].isnumeric()
            and path_parts[4] == "prompt"
        ):
            return True

        # ---------------------------------------------------------------------
        # workbench urls: http://localhost:9357/workbench/llm-clients/<str:hashed_id>/prompt/
        # ---------------------------------------------------------------------
        hashed_id = None
        if self.parsed_url:
            hashed_id = TimestampedModel.find_hash(self.parsed_url.path)
        if hashed_id is None:
            return False

        # valid path_parts:
        #   ['workbench', 'llm-clients', '<str:hashed_id>', 'prompt']
        #   ['workbench', 'llm-clients', '<str:hashed_id>', 'config']
        if self.parsed_url.netloc != smarter_settings.environment_platform_domain:
            return False
        if len(path_parts) != 4:
            return False
        if path_parts[0] != "workbench":
            return False
        if path_parts[1] != "llm-clients":
            return False
        if path_parts[-1] in ["config", "prompt", "manifest"]:
            # expecting:
            #   ['workbench', '<slug>', 'prompt']
            #   ['workbench', '<slug>', 'config']
            return True

        return False

    @cached_property
    def is_default_domain(self) -> bool:
        """
        Return True if the URL is on the default api domain for the environment, e.g. ``api.alpha.platform.smarter.sh``.

        :returns: True if the URL contains the environment's api domain, otherwise False.
        """
        if not self.smarter_request:
            return False
        if not self.url:
            return False
        return smarter_settings.environment_api_domain in self.url

    @cached_property
    def path(self) -> Optional[str]:
        """
        Extract the path from the URL.

        For example, this url returns ``'/llm-client/'``::

            https://hr.3141-5926-5359.alpha.api.example.com/llm-client/

        :returns: The path, ``/`` for an empty path, or None if there is no request or url.
        """
        if not self.smarter_request:
            return None
        if self.parsed_url and self.parsed_url.path == "":
            return "/"
        return self.parsed_url.path if self.parsed_url else None

    @cached_property
    def root_domain(self) -> Optional[str]:
        """
        Extract the root domain from the URL.

        Example::

            request_mixin = SmarterRequestMixin(request)
            print(request_mixin.root_domain)
            # For 'https://hr.3141-5926-5359.alpha.api.example.com/llm-client/' → 'example.com'
            # For 'http://localhost:9357/' → 'localhost'

        :returns: The root domain, or None if not found.
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
        logger.warning(
            "%s.root_domain() - failed to extract root domain from url: %s", self.srm_formatted_class_name, self.url
        )
        return None

    @cached_property
    def subdomain(self) -> Optional[str]:
        """
        Extract the subdomain from the URL.

        Example::

            request_mixin = SmarterRequestMixin(request)
            sub = request_mixin.subdomain
            print(sub)  # e.g., 'hr.3141-5926-5359.alpha' for
                        # 'https://hr.3141-5926-5359.alpha.api.example.com/llm-client/'

        :returns: The subdomain, or None if not found.
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
        Extract the API subdomain, the first label of the host, from an llmclient URL.

        For example, this url returns ``'hr'``::

            https://hr.3141-5926-5359.alpha.api.example.com/llm-client/

        :returns: The API subdomain, or None if the url is not an llmclient url.
        """
        if not self.smarter_request:
            return None
        if not self.is_llmclient:
            return None
        if not self.parsed_url:
            return None
        return self.parsed_url.netloc.split(".")[0] or None

    @cached_property
    def domain(self) -> Optional[str]:
        """
        Extract the domain, the host and port, from the URL.

        For example, this url returns ``'hr.3141-5926-5359.alpha.api.example.com'``::

            https://hr.3141-5926-5359.alpha.api.example.com/llm-client/

        :returns: The domain, or None if there is no request or url.
        """
        if not self.smarter_request:
            return None
        if not self.parsed_url:
            return None
        return self.parsed_url.netloc

    @cached_property
    def srm_formatted_class_name(self) -> str:
        """
        Returns the class name in a formatted string along with the name of this mixin.

        :returns: Formatted class name string.
        """
        class_name = f"{__name__}.{SmarterRequestMixin.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    @property
    def srm_ready(self) -> bool:
        """
        Returns True if the request mixin is srm_ready for processing.

        This is a convenience property to check if the request is srm_ready.

        :returns: True if the request mixin is srm_ready, False otherwise.
        """
        if self._srm_ready:
            return self._srm_ready
        # cheap and easy way to fail.
        if not self.am_ready:
            # AccountMixin is legitimately not ready for anonymous requests
            # (e.g. CORS preflight OPTIONS probes, unauthenticated callers).
            # That's an expected, routine state, not a problem, so this
            # doesn't warrant WARNING-level attention.
            logger.debug(
                "%s.srm_ready() - AccountMixin is not srm_ready. Cannot process request.",
                self.srm_formatted_class_name,
            )
            return False
        if not isinstance(self.smarter_request, SMARTER_REQUEST_CLASSES):
            return False
        if not isinstance(self.parsed_url, ParseResult):
            logger.warning(
                "%s.srm_ready() - _parsed_url is not a ParseResult. Received %s. Cannot process request.",
                self.srm_formatted_class_name,
                type(self._parsed_url).__name__,
            )
            return False
        if not isinstance(self.url, str):
            logger.warning(
                "%s.srm_ready() - _url is not a string. Received %s. Cannot process request.",
                self.srm_formatted_class_name,
                type(self.url).__name__,
            )
            return False
        self._srm_ready = True
        return self._srm_ready

    @property
    def _srm_ready_state(self) -> str:
        """
        Returns a string representation of the request mixin's srm_ready state.

        :returns: A string indicating whether the request mixin is srm_ready or not.
        """

        return self.formatted_state_ready if self.srm_ready else self.formatted_state_not_ready

    # --------------------------------------------------------------------------
    # instance methods
    # --------------------------------------------------------------------------
    def get_cookie_value(self, cookie_name: str) -> Optional[str]:
        """
        Retrieve the value of a cookie from the request object.

        :param cookie_name: Name of the cookie to retrieve.
        :returns: Value of the cookie, or None if there is no request or the cookie does not exist.
        """
        if self.smarter_request and self.smarter_request.COOKIES:
            return self.smarter_request.COOKIES.get(cookie_name)
        return None

    def generate_session_key(self) -> str:
        """
        Generate a new, random session_key.

        :returns: A random 64 character session key.
        """
        session_key = hash_factory(length=64)
        return session_key

    def accepted_session_key(self, session_key: Optional[str], source: str) -> Optional[str]:
        """
        Return a session key that the request carries, if it is well formed.

        The key comes from the client: the url, the request body, a cookie or a get() parameter.
        A malformed key, e.g. a cookie of the same name that another application set on a parent
        domain, is ignored rather than raised, so that the request starts a new session instead
        of failing.

        :param session_key: The raw value that the request carries, or None.
        :param source: Where the value came from, for the log, e.g. ``"cookie"``.
        :returns: The session key, stripped of whitespace and of a trailing slash, or None if
            the value is missing or malformed.
        """
        if not isinstance(session_key, str):
            return None
        session_key = session_key.strip().rstrip("/")
        if not session_key:
            return None
        if not SmarterValidator.is_valid_session_key(session_key):
            logger.warning(
                "%s.accepted_session_key() - ignoring a malformed session key from the %s of the request.",
                self.srm_formatted_class_name,
                source,
            )
            return None
        return session_key

    def find_session_key(self) -> Optional[str]:
        """
        Return the unique prompt session key value for this request.

        The session_key is managed by the /config/ endpoint for the llmclient. The React app calls this endpoint at app initialization to get a JSON dict that includes, among other info, this session_key, which uniquely identifies the device and the individual llmclient session for the device.

        For subsequent prompt requests, the session_key is intended to be sent in the body of the request as a key-value pair, e.g. ``{"session_key": "1234567890"}``.

        The session key is looked for in these places, in this order, and the first well formed
        one (see :meth:`accepted_session_key`) is returned:

        - The URL, e.g. ``http://localhost:9357/workbench/example/config/?session_key=1aeee4c1f183354247f43f80261573da921b0167c7c843b28afd3cb5ebba0d9a``
        - The request body: ``{'session_key': '1aeee4c1f183354247f43f80261573da921b0167c7c843b28afd3cb5ebba0d9a'}``
        - A cookie
        - The request's GET parameters

        :returns: The session key as a string, or None if not found.
        """
        if self._session_key:
            return self._session_key

        session_key: Optional[str]

        # this is our expected case. we look for the session key in the parsed url.
        url_session_key = None
        if self.url:
            url_session_key = session_key_from_url(self.url)
        session_key = self.accepted_session_key(url_session_key, "url")
        if session_key:
            return session_key

        # next, we look for it in the request body data.
        if isinstance(self.data, dict):
            session_key = self.accepted_session_key(self.data.get(SMARTER_CHAT_SESSION_KEY_NAME), "request body")
            if session_key:
                return session_key

        # next, we look for it in the cookie data.
        session_key = self.accepted_session_key(self.get_cookie_value(SMARTER_CHAT_SESSION_KEY_NAME), "cookie")
        if session_key:
            return session_key

        # finally, we look for it in the GET parameters.
        get_session_key = None
        if self.smarter_request:
            get_session_key = self.smarter_request.GET.get(SMARTER_CHAT_SESSION_KEY_NAME)
        session_key = self.accepted_session_key(get_session_key, "get() parameters")
        if session_key:
            return session_key

        return None

    def eval_llmclient_url(self) -> None:
        """
        Resolve the account and user of a request to a deployed LLMClient's own host.

        For a named url, e.g. ``http://example.3141-5926-5359.api.localhost:9357/``, the account
        is loaded from the url's account number when :attr:`account` is not already set, and then,
        when :attr:`user` is not set, the user becomes that account's admin user.

        Other llmclient urls, the smarter api and cli api urls, need no follow up here. A request
        that is not an llmclient request is left as it is.

        :returns: None. Sets :attr:`account` and :attr:`user` as a side effect.
        """
        if not self.is_llmclient:
            return
        if self.is_llmclient_named_url:
            # http://example.3141-5926-5359.api.localhost:9357/
            if not self.account:
                account_number = self.url_account_number
                if account_number:
                    self.account = Account.get_cached_object(account_number=account_number)  # type: ignore
            if self.account and not self.user:
                self.user = get_cached_admin_user_for_account(account=self.account)  # type: ignore

    # pylint: disable=W0221
    def authenticate(self) -> bool:
        """
        Authenticate the request using the API token in its ``Authorization`` header.

        The request is passed along, so that a token that was already authenticated for it, e.g.
        by the token middleware or by :class:`~smarter.apps.account.mixins.AccountMixin`'s own
        initialization, is not authenticated again.

        :returns: True if the request carries an API token and the parent's ``authenticate()``
            accepts it, otherwise False.
        """
        if not self.api_token:
            return False
        is_authenticated = super().authenticate(api_token=self.api_token, request=self._smarter_request)
        return is_authenticated

    def clear_cached_properties(self) -> None:
        """
        Clear the request, its parsed values, and all cached properties in this mixin.

        :returns: None.
        """
        self._smarter_request = None
        self._url = None
        self._url_account_number = None
        self._parsed_url = None
        self._params = None
        self._session_key = None
        self._data = None
        self._cache_key = None
        self.invalidate_cached_properties()

    def _srm_log_ready_status(self):
        """
        Logs the srm_ready status of the SmarterRequestMixin.

        Not ready is logged at WARNING only when something is wrong with the
        request itself. An anonymous caller, such as a deployed LLMClient's
        public ``/config/`` endpoint, leaves the AccountMixin not ready by
        design, so that case is logged at DEBUG. The message is only built when it will be
        logged, because it reads the user profile.
        """
        ready = self.srm_ready
        is_debug = ready or not self.am_ready
        if is_debug and not logger.should_log(logging.DEBUG):
            return
        log = logger.debug if is_debug else logger.warning
        log(
            "%s._srm_log_ready_status() is %s - %s - authenticated user: %s",
            self.srm_formatted_class_name,
            self.formatted_state_ready if ready else self.formatted_state_not_ready,
            self.url if self._url else "URL not initialized",
            self.user_profile if self.user_profile else "Anonymous",
        )

    def log_ready_status(self) -> None:
        """
        Log the ready status of the instance, at INFO.

        :returns: None.
        """
        logger.info("%s.log_ready_status() is %s", self.formatted_class_name, self.ready_state)

    def to_json(self) -> SmarterDictType:
        """
        Serialize the object.

        :returns: A dictionary representation of the object, with the auth header and api token masked.
        """
        retval = {
            "srm_ready": self.srm_ready,
            "url": self.url,
            "session_key": self.session_key,
            "auth_header": self.auth_header[:10] + "****" if self.auth_header else None,
            "api_token": mask_string(self.api_token.decode()) if self.api_token else None,
            "data": self.data,
            "llmclient_id": self.smarter_request_llmclient_id,
            "llmclient_name": self.smarter_request_llmclient_name,
            "is_smarter_api": self.is_smarter_api,
            "is_llmclient": self.is_llmclient,
            "is_llmclient_smarter_api_url": self.is_llmclient_smarter_api_url,
            "is_llmclient_named_url": self.is_llmclient_named_url,
            "is_llmclient_sandbox_url": self.is_llmclient_sandbox_url,
            "is_llmclient_cli_api_url": self.is_llmclient_cli_api_url,
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

    def is_internal_api_request(self, request: HttpRequest) -> bool:
        """
        Check if the request is an internal API request.

        This method checks for a custom attribute on the request object that indicates
        whether the request is an internal API request. This can be used to bypass
        certain authentication or permission checks for internal requests.

        :param request: The Django request object.
        :returns: True if it's an internal API request, False otherwise.
        """
        retval = getattr(request, SMARTER_IS_INTERNAL_API_REQUEST, False)
        logger.debug(
            "%s.is_internal_api_request() - request %s internal API request: %s",
            self.srm_formatted_class_name,
            request,
            retval,
        )
        return retval

    def set_is_internal_api_request(self, request: HttpRequest, value: bool = True) -> HttpRequest:
        """
        Set the internal API request attribute on the request object.

        This method allows you to mark a request as an internal API request by setting
        a custom attribute on the request object. This can be used in middleware or views
        to indicate that the request should be treated as internal.

        :param request: The Django request object, or a DRF request, whose wrapped Django request
            is flagged too.
        :param value: The value to set for the internal API request attribute (default is True).
        :returns: The modified request object.
        :raises SmarterValueError: If ``request`` is not a Django ``HttpRequest`` or a DRF ``Request``.
        """
        if not isinstance(request, (HttpRequest, RestFrameworkRequest)):
            raise SmarterValueError(f"Expected request to be an instance of HttpRequest, got {type(request).__name__}")

        logger.debug(
            "%s.set_is_internal_api_request() - setting request %s internal API request to: %s",
            self.srm_formatted_class_name,
            request.path,
            value,
        )
        setattr(request, SMARTER_IS_INTERNAL_API_REQUEST, value)
        if isinstance(request, RestFrameworkRequest):
            # a DRF Request that is passed on to a nested Django view: flag the wrapped HttpRequest too.
            setattr(request._request, SMARTER_IS_INTERNAL_API_REQUEST, value)  # pylint: disable=protected-access
        return request

    @property
    def is_authenticated(self) -> bool:
        """
        Return True if the request's user is authenticated.

        :returns: The request user's ``is_authenticated``, or False if there is no request or
            user, or checking it raises.
        """
        try:
            return self.smarter_request.user.is_authenticated  # type: ignore
        except AttributeError:
            logger.debug(
                "%s.is_authenticated() - request.user is not set or does not have is_authenticated attribute.",
                self.srm_formatted_class_name,
            )
            return False
        # pylint: disable=broad-except
        except Exception as e:
            logger.warning(
                "%s.is_authenticated() - unexpected error while checking authentication: %s",
                self.srm_formatted_class_name,
                str(e),
            )

        return False
