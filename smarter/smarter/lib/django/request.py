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
import json
import logging
import re
import warnings
from datetime import datetime
from functools import cached_property
from urllib.parse import ParseResult, urlparse, urlunsplit

import tldextract
import yaml
from django.core.handlers.wsgi import WSGIRequest
from django.http import QueryDict

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
from smarter.common.utils import hash_factory
from smarter.lib.django import waffle
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.django.waffle import SmarterWaffleSwitches


# Match netloc: chatbot_name.account_number.api.environment_api_domain
netloc_pattern_named_url = re.compile(
    rf"^(?P<chatbot_name>[a-zA-Z0-9\-]+)\.(?P<account_number>\d{{4}}-\d{{4}}-\d{{4}})\.api\.{re.escape(smarter_settings.environment_domain)}(:\d+)?$"
)
logger = logging.getLogger(__name__)


class SmarterRequestMixin(AccountMixin):
    """
    Helper class for the Django request object that enforces authentication and
    provides lazy loading of the user, account, user profile and session_key.

    Works with any Django request object and any valid url, but is designed
    as a helper class for Smarter ChatBot urls.

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
    - https://hr.smarter.querium.com/

    session_key is a unique identifier for a chat session.
    It originates from generate_session_key() in this class.
    """

    __slots__ = (
        "_smarter_request",
        "_timestamp",
        "_session_key",
        "_data",
        "_url",
        "_url_urlunparse_without_params",
        "_params",
        "_cache_key",
    )

    # pylint: disable=W0613
    def __init__(self, request: WSGIRequest, *args, **kwargs):

        session_key: str = kwargs.pop("session_key", None)
        if waffle.switch_is_active(SmarterWaffleSwitches.REQUEST_MIXIN_LOGGING):
            logger.info(
                "SmarterRequestMixin().__init__() - initializing with request=%s, session_key=%s", request, session_key
            )

        self._smarter_request: WSGIRequest = request
        self._timestamp = datetime.now()
        self._session_key: str = None
        self._data: dict = None
        self._url: ParseResult = None
        self._url_urlunparse_without_params = None
        self._params = None
        self._cache_key: str = None
        self.invalidate_cached_properties()

        url = self.smarter_build_absolute_uri(self.smarter_request)
        if url:
            self._url = urlparse(url)
            if not self._url.scheme or not self._url.netloc:
                raise SmarterValueError(f"{self.formatted_class_name} - request url is not a valid URL. url={url}")
            # rebuild the url minus any query parameters
            # example:
            # a request url like https://hr.3141-5926-5359.alpha.api.smarter.sh/config/?session_key=38486326c21ef4bcb7e7bc305bdb062f16ee97ed8d2462dedb4565c860cd8ecc
            # will return https://hr.3141-5926-5359.alpha.api.smarter.sh/config/
            self._url_urlunparse_without_params = urlunsplit(
                (self._url.scheme, self._url.netloc, self._url.path, "", "")
            )
            self._url_urlunparse_without_params = SmarterValidator.urlify(self._url_urlunparse_without_params)
        else:
            logger.warning("%s - request url is None.", self.formatted_class_name)

        super().__init__(request, **kwargs)

        if session_key is not None:
            self.session_key = session_key

        if self._url and self.is_chatbot_named_url:
            account_number = account_number_from_url(self.url)
            if account_number:
                if self.account and self.account.account_number != account_number:
                    raise SmarterValueError(
                        f"account number from url ({account_number}) does not match existing account ({self.account.account_number})."
                    )

            if self.account and not self._user:
                if waffle.switch_is_active(SmarterWaffleSwitches.REQUEST_MIXIN_LOGGING):
                    logger.warning(
                        "%s.__init__() - account (%s) is set but user is not.",
                        self.formatted_class_name,
                        self.account,
                    )

        self.eval_chatbot_url()

        if self.ready:
            self.helper_logger(
                f"__init__() initialized successfully url={self.url}, session_key={self.session_key}, user={self.user_profile}"
            )
        if waffle.switch_is_active(SmarterWaffleSwitches.REQUEST_MIXIN_LOGGING):
            logger.info("SmarterRequestMixin().__init__() - finished %s", self.dump())

    def invalidate_cached_properties(self):
        """
        Invalidate cached properties to force re-evaluation.
        This is useful for testing or when the request object changes.
        """
        cached_properties = [
            "qualified_request",
            "url",
            "url_path_parts",
            "smarter_request_chatbot_id",
            "smarter_request_chatbot_name",
            "unique_client_string",
            "client_key",
            "ip_address",
            "user_agent",
            "is_config",
            "is_dashboard",
            "is_environment_root_domain",
            "is_smarter_api",
            "is_chatbot_smarter_api_url",
            "is_chatbot_cli_api_url",
            "is_chatbot_named_url",
            "is_chatbot_sandbox_url",
            "is_default_domain",
            "path",
            "root_domain",
            "subdomain",
            "api_subdomain",
            "domain",
        ]
        for prop in cached_properties:
            self.__dict__.pop(prop, None)

    @property
    def smarter_request(self) -> WSGIRequest:
        """renaming this to avoid potential name collisions in child classes"""
        return self._smarter_request

    @cached_property
    def qualified_request(self) -> bool:
        """
        A cursory screening of the wsgi request object to look for
        any disqualifying conditions that confirm that this is not a
        request that we are interested in.
        """
        if not self._smarter_request:
            return False
        path = self._url.path if self._url else None
        if not path:
            return False

        if path in ["/favicon.ico", "/robots.txt", "/sitemap.xml"]:
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

    @cached_property
    def url(self) -> str:
        """
        The URL to parse.
        :return: The URL to parse.
        """
        if self._url_urlunparse_without_params:
            return self._url_urlunparse_without_params

        logger.error(
            "%s.url() property was accessed before it was initialized. request: %s",
            self.formatted_class_name,
            self.smarter_request,
        )
        raise SmarterValueError("The URL has not been initialized. Please check the request object.")

    @property
    def parsed_url(self) -> ParseResult:
        """
        expose our private _url
        """
        return self._url

    @cached_property
    def url_path_parts(self) -> list:
        """
        Extract the path parts from the URL.
        """
        if self.parsed_url:
            return self.parsed_url.path.strip("/").split("/")
        return [None, None, None, None]

    @property
    def params(self) -> dict[str, any]:
        """
        The query string parameters from the Django request object. This extracts
        the query string parameters from the request object and converts them to a
        dictionary. This is used in child views to pass optional command-line
        parameters to the broker.
        """
        if not self._params:
            try:
                self._params = QueryDict(self.smarter_request.META.get("QUERY_STRING", "")) or {}
            except AttributeError as e:
                logger.error(
                    "%s.params() internal error. Could not parse query string parameters: %s",
                    self.formatted_class_name,
                    e,
                )
                return {}
        return self._params

    @property
    def uid(self) -> str:
        """
        Unique identifier for the client. This is assumed to be a
        combination of the machine mac address and the hostname.
        """
        return self.params.get("uid", None)

    @property
    def cache_key(self) -> str:
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
        if not self.user or not self.account:
            logger.warning(
                "%s.cache_key() - request is not authenticated. Cannot generate cache key.",
                self.formatted_class_name,
            )
            return None

        uid = self.uid or "unknown_uid"
        username = (
            self.smarter_request.user.username
            if self.smarter_request and hasattr(self._smarter_request, "user")
            else "unknown_user"
        )
        raw_string = self.__class__.__name__ + "_" + username + "_" + "cache_key()_" + uid
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
        return self._session_key

    @session_key.setter
    def session_key(self, value: str):
        """
        Setter for the session_key property.
        This is used to set the session_key from the request object.
        """
        if not value:
            raise SmarterValueError("Session key cannot be None or empty.")
        SmarterValidator.validate_session_key(value)
        if not self.smarter_request:
            raise SmarterValueError("Session key cannot be set without a valid request object.")
        if waffle.switch_is_active(SmarterWaffleSwitches.REQUEST_MIXIN_LOGGING):
            logger.info("%s.session_key() - setting session_key to %s", self.formatted_class_name, value)
        self._session_key = value

    @cached_property
    def smarter_request_chatbot_id(self) -> int:
        """
        Extract the chatbot id from the URL.
        example: http://localhost:8000/api/v1/workbench/<int:chatbot_id>/chat/config/
        """
        if self.is_chatbot_smarter_api_url:
            path_parts = self.url_path_parts
            return int(path_parts[3])

        if self.is_chatbot_named_url:
            # can't get from ChatBot bc of circular import
            return None

    @cached_property
    def smarter_request_chatbot_account_number(self) -> str:
        """
        http://example.3141-5926-5359.api.localhost:8000/config
        SmarterValidator.VALID_ACCOUNT_NUMBER_PATTERN
        """
        return account_number_from_url(self.url)

    @cached_property
    def smarter_request_chatbot_name(self) -> str:
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
            return retval

        # 2.) example: http://localhost:8000/workbench/<str:name>/config/
        if self.is_chatbot_sandbox_url:
            try:
                retval = self.url_path_parts[1]
                return retval
            # pylint: disable=broad-except
            except Exception:
                logger.warning(
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
                return retval
            # pylint: disable=broad-except
            except Exception:
                logger.warning(
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
    def data(self) -> dict:
        """
        Get the request body data as a dictionary.
        used for setting the session_key.
        """
        if self._data:
            return self._data
        if not self.smarter_request:
            logger.warning("%s.data() - request is None or not set.", self.formatted_class_name)
            return {}
        try:
            body = self.smarter_request.body if hasattr(self.smarter_request, "body") else None
            if body is not None:
                body_str = body.decode("utf-8").strip()
                self._data = json.loads(body_str) if body_str else None
                if self._data and waffle.switch_is_active(SmarterWaffleSwitches.REQUEST_MIXIN_LOGGING):
                    logger.info(
                        "%s.data() - initialized from parsed request body as json: %s",
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
                    if waffle.switch_is_active(SmarterWaffleSwitches.REQUEST_MIXIN_LOGGING):
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
        if waffle.switch_is_active(SmarterWaffleSwitches.CHATBOT_LOGGING):
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
            return None
        account_number = self.account.account_number if self.account else "####-####-####"
        url = self.url if self.url else "http://localhost:8000/"
        timestamp = self.timestamp.isoformat()
        return f"{account_number}.{url}.{self.user_agent}.{self.ip_address}.{timestamp}"

    @cached_property
    def client_key(self) -> str:
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
    def ip_address(self) -> str:
        if self.smarter_request:
            return self.smarter_request.META.get("REMOTE_ADDR", "") or "ip_address"
        return None

    @cached_property
    def user_agent(self) -> str:
        if self.smarter_request:
            return self.smarter_request.META.get("HTTP_USER_AGENT", "") or "user_agent"
        return None

    @cached_property
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
        return self.parsed_url.netloc == smarter_settings.environment_domain and self.parsed_url.path == "/"

    @property
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

        return (
            self.qualified_request
            and not self.is_config
            and (
                self.is_chatbot_named_url
                or self.is_chatbot_sandbox_url
                or self.is_chatbot_smarter_api_url
                or self.is_chatbot_cli_api_url
            )
        )

    @cached_property
    def is_smarter_api(self) -> bool:
        """
        Returns True if the url is of the form http://localhost:8000/api/v1/
        examples:
        - path_parts: ['api', 'v1', 'chatbots', '1', 'chat']
        - http://api.localhost:8000/
        """
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
        if path_parts[2] != "cli":
            return False
        if path_parts[3] != "chat":
            return False

        return True

    @cached_property
    def is_chatbot_named_url(self) -> bool:
        """
        Returns True if the url is of the form
        - https://example.3141-5926-5359.api.smarter.sh/
        - http://example.3141-5926-5359.api.localhost:8000/
        """
        if not self.url:
            return False
        if not self.smarter_request:
            return False
        if not smarter_settings.environment_api_domain in self.url:
            return False
        if account_number_from_url(self.url):
            return True

        # Accept root path or root with trailing slash
        if self._url.path not in ("", "/"):
            return False

        if netloc_pattern_named_url.match(self._url.netloc):
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
            return False
        if not self.qualified_request:
            return False
        if not self._url:
            return False
        if not self.parsed_url:
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
        if self.parsed_url.netloc != smarter_settings.environment_domain:
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

        return False

    @cached_property
    def is_default_domain(self) -> bool:
        """
        Returns True if the URL is the default domain for the environment.
        example: api.alpha.platform.smarter.sh
        """
        if not self.url:
            return False
        return smarter_settings.environment_api_domain in self.url

    @cached_property
    def path(self) -> str:
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
    def root_domain(self) -> str:
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
        url = SmarterValidator.urlify(self.url, environment=smarter_settings.environment)
        if url:
            extracted = tldextract.extract(url)
            if extracted.domain and extracted.suffix:
                return f"{extracted.domain}.{extracted.suffix}"
            if extracted.domain:
                return extracted.domain
        return None

    @cached_property
    def subdomain(self) -> str:
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
    def api_subdomain(self) -> str:
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
    def domain(self) -> str:
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

    @property
    def formatted_class_name(self) -> str:
        """
        Returns the class name in a formatted string
        along with the name of this mixin.
        """
        parent_class = super().formatted_class_name
        return f"{parent_class}.SmarterRequestMixin()"

    @property
    def ready(self) -> bool:
        """
        returns True if the request is ready for processing.
        """
        # cheap and easy way to fail.
        if not self.smarter_request:
            return False
        if not self._url:
            return False
        retval = bool(super().ready) and bool(self._smarter_request)
        if not retval and waffle.switch_is_active(SmarterWaffleSwitches.REQUEST_MIXIN_LOGGING):
            logger.warning(
                "%s: SmarterRequestMixin is not ready. super(): %s, request: %s, user: %s, account: %s",
                self.formatted_class_name,
                super().ready,
                self.smarter_request,
                self.user_profile,
                self.account,
            )
        return retval

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
        key_string = self.unique_client_string
        if key_string:
            session_key = hash_factory(length=64)
            self.helper_logger(f"Generated new session key: {session_key}")
            return session_key

    def find_session_key(self) -> str:
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

        session_key: str = None

        # this is our expected case. we look for the session key in the parsed url.
        session_key = session_key_from_url(self.url)
        if session_key:
            SmarterValidator.validate_session_key(session_key)
            self.helper_logger(
                f"session_key() - initialized from url: {session_key}",
            )
            return session_key

        # next, we look for it in the request body data.
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
        session_key = self.smarter_request.GET.get(SMARTER_CHAT_SESSION_KEY_NAME)
        session_key = session_key.strip() if isinstance(session_key, str) else None
        if session_key:
            SmarterValidator.validate_session_key(session_key)
            self.helper_logger(
                f"session_key() - initialized from the get() parameters of the request object: {session_key}",
            )
            return session_key

    def to_json(self) -> dict:
        """
        serializes the object.
        """
        return {
            "ready": self.ready,
            "url": self.url,
            "session_key": self.session_key,
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
                    self.account = get_cached_account(account_number=account_number)
            if self.account and not self.user:
                self.user = get_cached_admin_user_for_account(account=self.account)
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
        if waffle.switch_is_active(SmarterWaffleSwitches.REQUEST_MIXIN_LOGGING):
            logger.info("%s %s", self.formatted_class_name, message)

    def dump(self):
        """
        Dump the object to the console.
        """
        return json.dumps(self.to_json(), indent=4)
