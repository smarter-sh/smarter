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
from django.core.serializers.json import DjangoJSONEncoder
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


class SmarterRequestMixin(AccountMixin):
    """
    Helper class for the Django request object that enforces authentication and
    provides lazy loading of the user, account, user profile and session_key.

    Works with any Django request object and any valid url, but is designed
    as a helper class for Smarter ChatBot urls.

    Fix note: we've been boxed into making the request object an optional positional
    argument, because Django view lifecycles do not recognize the request object
    until well after class __init__(). Meanwhile, SmarterRequestMixin is
    included as a mixin in the Smarter base view classes.

    valid end points:
        1.) root end points for named urls. Public or authenticated chats
            self.is_chatbot_named_url==True
        --------
        - http://example.3141-5926-5359.api.localhost:8000/			            -> smarter.apps.chatbot.api.v1.views.default.DefaultChatbotApiView
        - http://example.3141-5926-5359.api.localhost:8000/config		        -> smarter.apps.prompt.views.ChatConfigView

        2.) authenticated sandbox end points. Authenticated chats
            self.is_chatbot_sandbox_url==True
        --------
        - http://localhost:8000/workbench/<str:name>/				            -> smarter.apps.prompt.views.ChatAppWorkbenchView
        - http://localhost:8000/workbench/<str:name>/config/			            -> smarter.apps.prompt.views.ChatConfigView

        3.) smarter.sh/v1 end points. Public or authenticated chats
            self.is_chatbot_smarter_api_url==True
        --------
        - http://localhost:8000/api/v1/workbench/<int:chatbot_id>/chat/		    -> smarter.apps.chatbot.api.v1.views.default.DefaultChatbotApiView
        - http://localhost:8000/api/v1/workbench/<int:chatbot_id>/chat/config/	-> smarter.apps.prompt.views.ChatConfigView

        4.) command-line interface api end points. Authenticated chats
            self.is_chatbot_cli_api_url==True
        --------
        - http://localhost:8000/api/v1/cli/chat/<str:name>/			            -> smarter.apps.chatbot.api.v1.cli.views.nonbrokered.chat.ApiV1CliChatApiView -> * non-brokered view based on url returned by ChatConfigView
        - http://localhost:8000/api/v1/cli/chat/config/<str:name>/", 		    -> smarter.apps.chatbot.api.v1.cli..views.nonbrokered.chat_config.ApiV1CliChatConfigApiView	-> ChatConfigView

        5.) wtf are these???????
        - http://localhost:8000/api/v1/chat/        ** these seem to be dead ends
        - http://localhost:8000/api/v1/chat/

    example urls:
    - http://testserver
    - http://localhost:8000/
    - http://localhost:8000/docs/
    - http://localhost:8000/dashboard/
    - https://alpha.platform.smarter.sh/api/v1/workbench/1/chatbot/
    - http://example.com/contact/
    - http://localhost:8000/workbench/example/config/?session_key=1aeee4c1f183354247f43f80261573da921b0167c7c843b28afd3cb5ebba0d9a
    - https://hr.3141-5926-5359.alpha.api.smarter.sh/
    - https://hr.3141-5926-5359.alpha.api.smarter.sh/config/?session_key=38486326c21ef4bcb7e7bc305bdb062f16ee97ed8d2462dedb4565c860cd8ecc
    - http://example.3141-5926-5359.api.localhost:8000/
    - http://example.3141-5926-5359.api.localhost:8000/?session_key=9913baee675fb6618519c478bd4805c4ff9eeaab710e4f127ba67bb1eb442126
    - http://example.3141-5926-5359.api.localhost:8000/config/
    - http://example.3141-5926-5359.api.localhost:8000/config/?session_key=9913baee675fb6618519c478bd4805c4ff9eeaab710e4f127ba67bb1eb442126
    - http://localhost:8000/api/v1/workbench/1/chat/
    - http://localhost:8000/api/v1/cli/chat/smarter/?new_session=false&uid=mcdaniel
    - https://hr.smarter.sh/

    session_key is a unique identifier for a chat session.
    It originates from generate_session_key() in this class.
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
            self.init(request, *args, **kwargs)
        else:
            logger.debug(
                "%s.__init__() - request is None. SmarterRequestMixin will be partially initialized. This might affect request processing.",
                self.formatted_class_name,
            )
            super().__init__(request, *args, api_token=self.api_token, **kwargs)

    def init(self, request: HttpRequest, *args, **kwargs):
        """
        Handles initializations that require a valid request. This is called
        from __init__() iif the request object is passed. It is also called
        from the smarter_request setter.
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
        Invalidate cached properties to force re-evaluation.
        This is useful for testing or when the request object changes.
        """
        for cls in self.__class__.__mro__:
            for name, value in inspect.getmembers(cls):
                if isinstance(value, cached_property):
                    self.__dict__.pop(name, None)

    @property
    def smarter_request(self) -> Optional[HttpRequest]:
        """renaming this to avoid potential name collisions in child classes"""
        return self._smarter_request

    @smarter_request.setter
    def smarter_request(self, request: HttpRequest):
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
        """Get the Authorization header from the request."""
        return (
            self._smarter_request.META.get("HTTP_AUTHORIZATION")
            if self._smarter_request and hasattr(self._smarter_request, "META")
            else None
        )

    @cached_property
    def api_token(self) -> Optional[bytes]:
        """Get the API token from the request."""
        if isinstance(self.auth_header, str) and self.auth_header.startswith("Token "):
            return self.auth_header.split("Token ")[1].encode()
        return None

    @cached_property
    def qualified_request(self) -> bool:
        """
        A cursory screening of the wsgi request object to look for
        any disqualifying conditions that confirm that this is not a
        request that we are interested in.
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
        The str representation of the ParseResult object stored in _parse_result.
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
        expose our private url
        """
        if not isinstance(self._parse_result, ParseResult):
            raise SmarterValueError("The URL has not been initialized as a ParseResult.")
        return self._parse_result

    @property
    def url_path_parts(self) -> list:
        """
        Extract the path parts from the URL.
        """
        return self.parsed_url.path.strip("/").split("/")

    @property
    def params(self) -> Optional[QueryDict]:
        """
        The query string parameters from the Django request object. This extracts
        the query string parameters from the request object and converts them to a
        dictionary. This is used in child views to pass optional command-line
        parameters to the broker.
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
        Unique identifier for the client. This is assumed to be a
        combination of the machine mac address and the hostname.
        """
        return self.params.get("uid") if isinstance(self.params, QueryDict) else None

    @cached_property
    def cache_key(self) -> Optional[str]:
        """
        Returns a cache key for the request.
        This is used to cache the chat request thread.

        The key is a combination of the class name, authenticated username,
        the chat name, and the client UID. Currently used by the
        ApiV1CliChatConfigApiView and ApiV1CliChatApiView as a means of sharing the session_key.

        :param name: a generic object or resource name
        :param uid: UID of the client, assumed to have been created from the
         machine mac address and the hostname of the client
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
    def session_key(self):
        """
        Getter for the session_key property. The session_key is a unique identifier
        for a chat session. It is used to identify the chat session across multiple requests.
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
        example: http://localhost:8000/api/v1/workbench/<int:chatbot_id>/chat/config/
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
        http://example.3141-5926-5359.api.localhost:8000/config
        SmarterValidator.VALID_ACCOUNT_NUMBER_PATTERN
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
        http://example.3141-5926-5359.api.localhost:8000/config
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
        create a consistent timestamp
        based on the time that this object was instantiated.
        """
        return self._timestamp

    @property
    def data(self) -> Optional[Union[dict, list, str]]:
        """
        Get the request body data as a dictionary, list or str.
        used for setting the session_key.
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
        Generate a unique string based on:
         - account number
         - url
         - user agent
         - ip address
         - timestamp
        Used for generating session_key and client_key.
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
        for smarter.sh/v1 api endpoints, the client_key is used to identify the client.
        Generate a unique client key based on the client's IP address, user agent, and the current datetime.
        """
        warnings.warn(
            "The 'client_key' property is deprecated and will be removed in a future version.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.session_key

    @cached_property
    def ip_address(self) -> Optional[str]:
        if (
            self.smarter_request is not None
            and hasattr(self.smarter_request, "META")
            and isinstance(self.smarter_request.META, dict)
        ):
            return self.smarter_request.META.get("REMOTE_ADDR", "") or "ip_address"
        return None

    @cached_property
    def user_agent(self) -> Optional[str]:
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
        Returns True if the url resolves to a config endpoint.

        examples:
        - http://testserver/api/v1/cli/chat/config/testc7098865f39202d5/
        - http://localhost:8000/workbench/example/config/?session_key=1aeee4c1f183354247f43f80261573da921b0167c7c843b28afd3cb5ebba0d9a
        - http://localhost:8000/api/v1/workbench/<int:chatbot_id>/chat/config/
        - http://example.api.localhost:8000/config

        """
        return "config" in self.url_path_parts

    @cached_property
    def is_dashboard(self) -> bool:
        """
        Returns True if the url resolves to a dashboard endpoint.
        """
        if not self.smarter_request:
            return False
        return self.url_path_parts[-1] == "dashboard"

    @cached_property
    def is_workbench(self) -> bool:
        """
        Returns True if the url resolves to a workbench endpoint.
        """
        if not self.smarter_request:
            return False
        return self.url_path_parts[-1] == "workbench"

    @cached_property
    def is_environment_root_domain(self) -> bool:
        if not self.smarter_request:
            return False
        if not self.parsed_url:
            return False
        return self.parsed_url.netloc == smarter_settings.environment_platform_domain and self.parsed_url.path == "/"

    @cached_property
    def is_chatbot(self) -> bool:
        """
        Returns True if the url resolves to a chatbot. Conditions are called in a lazy
        sequence intended to avoid unnecessary processing.
        examples:
        - http://localhost:8000/api/v1/prompt/1/chat/
        - http://localhost:8000/api/v1/cli/chat/example/
        - http://example.3141-5926-5359.api.localhost:8000/
        - http://localhost:8000/workbench/<str:name>/chat/
        - http://localhost:8000/api/v1/chatbots/1556/chat/
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
        Returns True if the url is of the form http://localhost:8000/api/v1/
        examples:
        - path_parts: ['api', 'v1', 'chatbots', '1', 'chat']
        - http://api.localhost:8000/
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
        Returns True if the url is of the form
        - http://localhost:8000/api/v1/workbench/1/chat/
          path_parts: ['api', 'v1', 'workbench', '<int:pk>', 'chat']

        - http://localhost:8000/api/v1/chatbots/1556/chat/
          path_parts: ['api', 'v1', 'chatbots', '<int:pk>', 'chat']


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
        Returns True if the url is of the form http://localhost:8000/api/v1/cli/chat/example/
        path_parts: ['api', 'v1', 'cli', 'chat', 'example']
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
        Returns True if the url is of the form
        - https://example.3141-5926-5359.api.smarter.sh/
        - http://example.3141-5926-5359.api.localhost:8000/
        - http://example.3141-5926-5359.api.localhost:8000/config/
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
        example urls:
        - https://alpha.platform.smarter.sh/workbench/example/
          https://<environment_domain>/workbench/<name>
          path_parts: ['workbench', 'example']

        - http://localhost:8000/workbench/<str:name>/chat/
        - https://alpha.platform.smarter.sh/workbench/example/config/
          https://<environment_domain>/workbench/<name>/config/
          path_parts: ['workbench', 'example', 'config']

        - http://localhost:8000/api/v1/prompt/1/chat/
          http://<environment_domain>/api/v1/prompt/<int:chatbot_id>/chat/

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
        example: api.alpha.platform.smarter.sh
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
        :return: The path or None if not found.

        examples:
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

        examples:
        - https://hr.3141-5926-5359.alpha.api.smarter.sh/chatbot/
            returns 'smarter.sh'

        - http://localhost:8000/
            returns 'localhost'
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

        examples:
        - https://hr.3141-5926-5359.alpha.api.smarter.sh/chatbot/
          returns 'hr.3141-5926-5359.alpha'
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

        example: https://hr.3141-5926-5359.alpha.api.smarter.sh/chatbot/
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

        examples:
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
        """
        parent_class = super().formatted_class_name
        return f"{parent_class}.SmarterRequestMixin()"

    @cached_property
    def is_requestmixin_ready(self) -> bool:
        """
        Returns True if the request mixin is ready for processing.
        This is a convenience property to check if the request is ready.
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
        """
        session_key = hash_factory(length=64)
        self.helper_logger(f"Generated new session key: {session_key}")
        return session_key

    def find_session_key(self) -> Optional[str]:
        """
        returns the unique chat session key value for this request.
        session_key is managed by the /config/ endpoint for the chatbot

        The React app calls this endpoint at app initialization to get a
        json dict that includes, among other pertinent info, this session_key
        which uniquely identifies the device and the individual chatbot session
        for the device.

        for subsequent chat prompt requests the session_key is intended to be
        sent in the body of the request as a key-value pair,
        e.g. {"session_key": "1234567890"}.

        But, this method will also check the request headers for the session_key.
        Get the session key from one of the following:
         - url parameter http://localhost:8000/workbench/example/config/?session_key=1aeee4c1f183354247f43f80261573da921b0167c7c843b28afd3cb5ebba0d9a
         - request json body {'session_key': '1aeee4c1f183354247f43f80261573da921b0167c7c843b28afd3cb5ebba0d9a'}
         - request header {'session_key': '1aeee4c1f183354247f43f80261573da921b0167c7c843b28afd3cb5ebba0d9a'}
         - a session_key generator

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
