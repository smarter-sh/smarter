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
from urllib.parse import ParseResult, parse_qs, urlparse, urlunsplit

import tldextract
from django.core.handlers.wsgi import WSGIRequest

from smarter.apps.account.mixins import AccountMixin
from smarter.apps.account.utils import (
    account_number_from_url,
    get_cached_account,
    get_cached_admin_user_for_account,
)
from smarter.common.classes import SmarterHelperMixin
from smarter.common.conf import settings as smarter_settings
from smarter.common.const import SMARTER_CHAT_SESSION_KEY_NAME, SmarterWaffleSwitches
from smarter.common.helpers.url_helpers import session_key_from_url
from smarter.lib.django import waffle
from smarter.lib.django.validators import SmarterValidator


logger = logging.getLogger(__name__)


class SmarterRequestMixin(AccountMixin, SmarterHelperMixin):
    """
    Helper class for the Django request object that enforces authentication and
    provides lazy loading of the user, account, user profile and session_key.

    Works with any Django request object and any valid url, but is designed
    as a helper class for Smarter ChatBot urls.

    valid end points:
        1.) root end points for named urls. Public or authenticated chats
            self.is_chatbot_named_url==True
        --------
        - http://example.3141-5926-5359.api.localhost:8000/			            -> smarter.apps.chatbot.api.v1.views.default.DefaultChatBotApiView
        - http://example.3141-5926-5359.api.localhost:8000/config		        -> smarter.apps.chatapp.views.ChatConfigView

        2.) authenticated sandbox end points. Authenticated chats
            self.is_chatbot_sandbox_url==True
        --------
        - http://localhost:8000/chatbots/<str:name>/				            -> smarter.apps.chatapp.views.ChatAppWorkbenchView
        - http://localhost:8000/chatbots/<str:name>/config/			            -> smarter.apps.chatapp.views.ChatConfigView

        3.) smarter.sh/v1 end points. Public or authenticated chats
            self.is_chatbot_smarter_api_url==True
        --------
        - http://localhost:8000/api/v1/chatbots/<int:chatbot_id>/chat/		    -> smarter.apps.chatbot.api.v1.views.default.DefaultChatBotApiView
        - http://localhost:8000/api/v1/chatbots/<int:chatbot_id>/chat/config/	-> smarter.apps.chatapp.views.ChatConfigView

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
    - https://alpha.platform.smarter.sh/api/v1/chatbots/1/chatbot/
    - http://example.com/contact/
    - http://localhost:8000/chatbots/example/config/?session_key=1aeee4c1f183354247f43f80261573da921b0167c7c843b28afd3cb5ebba0d9a
    - https://hr.3141-5926-5359.alpha.api.smarter.sh/
    - https://hr.3141-5926-5359.alpha.api.smarter.sh/config/?session_key=38486326c21ef4bcb7e7bc305bdb062f16ee97ed8d2462dedb4565c860cd8ecc
    - http://example.3141-5926-5359.api.localhost:8000/
    - http://example.3141-5926-5359.api.localhost:8000/?session_key=9913baee675fb6618519c478bd4805c4ff9eeaab710e4f127ba67bb1eb442126
    - http://example.3141-5926-5359.api.localhost:8000/config/
    - http://example.3141-5926-5359.api.localhost:8000/config/?session_key=9913baee675fb6618519c478bd4805c4ff9eeaab710e4f127ba67bb1eb442126
    - http://localhost:8000/api/v1/chatbots/1/chat/
    - http://localhost:8000/api/v1/cli/chat/smarter/?new_session=false&uid=mcdaniel
    - https://hr.smarter.querium.com/

    session_key is a unique identifier for a chat session.
    It originates from generate_key() in this class.
    """

    __slots__ = ("_smarter_request", "_timestamp", "_session_key", "_data", "_url", "_url_urlunparse_without_params")

    def init(self, request: WSGIRequest):
        """
        validate, standardize and parse the request url string into a ParseResult.
        Note that the setter and getter both work with strings
        but we store the private instance variable _url as a ParseResult.

        note: this is separated from __init__ because SmarterRequestMixin is a
        parent of Classes that do not necessarily initialize with a request object.
        For example, Django Views do not pass a request object to the __init__ method.
        """
        if self._smarter_request:
            # we've already been initialized. nothing to do.
            return None

        if not request:
            logger.warning("%s - request is None", self.formatted_class_name)
            return None

        if hasattr(request, "user") and request.user and request.user.is_authenticated:
            self.user = request.user

        self._smarter_request: WSGIRequest = request
        url = request.build_absolute_uri() if request else "http://localhost:8000/"
        self._url = urlparse(url)
        self._url_urlunparse_without_params: str = None

        self.helper_logger(f"init() request: {self.url}")
        self.session_key = self.get_session_key()
        self.helper_logger(f"url={self._url}")

        # lazy excuses to not do anything...
        if not self.qualified_request:
            return None

        if self.is_chatbot_named_url:
            account_number = account_number_from_url(self.url)
            self.account = get_cached_account(account_number=account_number)

            if self.account and not self._user:
                self._user = get_cached_admin_user_for_account(account=self.account)

        self.eval_chatbot_url()

        if self.is_chatbot:
            self.helper_logger(
                f"chatbot_name={self.smarter_request_chatbot_name} chatbot_id={self.smarter_request_chatbot_id}"
            )
        if self.is_config:
            self.helper_logger("is_config=True")

        if waffle.switch_is_active(SmarterWaffleSwitches.REQUEST_MIXIN_LOGGING):
            self.dump()

        cached_properties = [
            "qualified_request",
            "url",
            "url_path_parts",
            "smarter_request_chatbot_id",
            "smarter_request_chatbot_name",
            "timestamp",
            "data",
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

    # pylint: disable=W0613
    def __init__(self, *args, **kwargs):
        self._smarter_request: WSGIRequest = None
        self._timestamp = datetime.now()
        self._session_key: str = None
        self._data: dict = None
        self._url = None
        self._url_urlunparse_without_params = None

        # validate, standardize and parse the request url string into a ParseResult.
        # Note that the setter and getter both work with strings
        # but we store the private instance variable _url as a ParseResult.
        request: WSGIRequest = kwargs.get("request", None)
        if not request and args:
            request = args[0]
        if not request:
            AccountMixin.__init__(self)
            logger.warning("request.user is missing or is not authenticated for url: %s", self.url)
            logger.warning("%s - request is None. Ditching.", self.formatted_class_name)
            return None
        if hasattr(request, "user") and request.user and request.user.is_authenticated:
            AccountMixin.__init__(self, user=request.user)
        else:
            AccountMixin.__init__(self)
        self.init(request=request)

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
        if self._smarter_request.path in ["/favicon.ico", "/robots.txt", "/sitemap.xml"]:
            return False
        if self._smarter_request.path.startswith("/admin/"):
            return False
        if self._smarter_request.path.startswith("/docs/"):
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
        if any(self._smarter_request.path.endswith(ext) for ext in static_extensions):
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

        if self._url:
            # rebuild the url minus any query parameters
            # example:
            # a request url like https://hr.3141-5926-5359.alpha.api.smarter.sh/config/?session_key=38486326c21ef4bcb7e7bc305bdb062f16ee97ed8d2462dedb4565c860cd8ecc
            # will return https://hr.3141-5926-5359.alpha.api.smarter.sh/config/
            self._url_urlunparse_without_params = urlunsplit(
                (self._url.scheme, self._url.netloc, self._url.path, "", "")
            )
            self._url_urlunparse_without_params = SmarterValidator.urlify(self._url_urlunparse_without_params)
            return self._url_urlunparse_without_params
        logger.error("%s - url is None", self.formatted_class_name)

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
    def session_key(self):
        """
        Get the session key from one of the following:
         - url parameter http://localhost:8000/chatbots/example/config/?session_key=1aeee4c1f183354247f43f80261573da921b0167c7c843b28afd3cb5ebba0d9a
         - request json body {'session_key': '1aeee4c1f183354247f43f80261573da921b0167c7c843b28afd3cb5ebba0d9a'}
         - request header {'session_key': '1aeee4c1f183354247f43f80261573da921b0167c7c843b28afd3cb5ebba0d9a'}
         - a session_key generator
        """
        if self._session_key:
            return self._session_key

    @session_key.setter
    def session_key(self, session_key: str):
        self._session_key = session_key
        if self._session_key:
            SmarterValidator.validate_session_key(session_key)
        self.helper_logger(f"@session_key.setter={self._session_key}")

    @cached_property
    def smarter_request_chatbot_id(self) -> int:
        """
        Extract the chatbot id from the URL.
        example: http://localhost:8000/api/v1/chatbots/<int:chatbot_id>/chat/config/
        """
        if self.is_chatbot_smarter_api_url:
            path_parts = self.url_path_parts
            return int(path_parts[3])

    @cached_property
    def smarter_request_chatbot_name(self) -> str:
        """
        Extract the chatbot name from the URL.
        """
        if not self.is_chatbot:
            self.helper_logger("smarter_request_chatbot_name() - not a chatbot")
            return None

        # 1.) http://example.api.localhost:8000/config
        if self.is_chatbot_named_url:
            netloc_parts = self.parsed_url.netloc.split(".") if self.parsed_url and self.parsed_url.netloc else None
            retval = netloc_parts[0] if netloc_parts else None
            self.helper_logger(
                f"smarter_request_chatbot_name() - is_chatbot_named_url=True netloc_parts={netloc_parts} chatbot_name={retval}"
            )
            return retval

        # 2.) example: http://localhost:8000/chatbots/<str:name>/config/
        if self.is_chatbot_sandbox_url:
            try:
                retval = self.url_path_parts[1]
                self.helper_logger(
                    f"smarter_request_chatbot_name() - is_chatbot_sandbox_url=True path_parts={self.url_path_parts} chatbot_name={retval}"
                )
                return retval
            # pylint: disable=broad-except
            except Exception:
                logger.warning(
                    "%s.smarter_request_chatbot_name() - failed to extract chatbot name from url: %s",
                    self.formatted_class_name,
                    self.url,
                )
        # 3.) http://localhost:8000/api/v1/chatbots/<int:chatbot_id>
        # no name. nothing to do in this case.
        if self.is_chatbot_smarter_api_url:
            self.helper_logger(
                "smarter_request_chatbot_name() - is_chatbot_smarter_api_url=True this url does not include a name"
            )

        # 4.) http://localhost:8000/api/v1/cli/chat/config/<str:name>/
        # http://localhost:8000/api/v1/cli/chat/<str:name>/
        if self.is_chatbot_cli_api_url:
            try:
                retval = self.url_path_parts[-1]
                self.helper_logger(
                    f"smarter_request_chatbot_name() - is_chatbot_cli_api_url=True path_parts={self.url_path_parts} chatbot_name={retval}"
                )
                return retval
            # pylint: disable=broad-except
            except Exception:
                logger.warning(
                    "%s.smarter_request_chatbot_name() - failed to extract chatbot name from url: %s",
                    self.formatted_class_name,
                    self.url,
                )

        return None

    @cached_property
    def timestamp(self):
        """
        create a consistent timestamp
        based on the time that this object was instantiated.
        """
        return self._timestamp

    @cached_property
    def data(self) -> dict:
        """
        Get the request body data as a dictionary.
        used for setting the session_key.
        """
        if self._data:
            return self._data
        try:
            if self.smarter_request and self.smarter_request.body:
                self.helper_logger(f"request body={self.smarter_request.body}")
                body_str = self.smarter_request.body.decode("utf-8").strip()
                self._data = json.loads(body_str) if body_str else {}
        # pylint: disable=broad-except
        except Exception as e:
            logger.warning("%s - failed to parse request body: %s", self.formatted_class_name, e)

        self._data = self._data or {}
        if waffle.switch_is_active(SmarterWaffleSwitches.CHATBOT_LOGGING):
            self.helper_logger(f"request body json={self._data}")

        return self._data

    @cached_property
    def unique_client_string(self):
        """
        Generate a unique string based on:
         - account number
         - url
         - user agent
         - ip address
         - timestamp
        Used for generating session_key and client_key.
        """
        account_number = self.account.account_number if self.account else "####-####-####"
        url = self.url if self.url else "http://localhost:8000/"
        timestamp = self.timestamp.isoformat()
        return f"{account_number}.{url}.{self.user_agent}.{self.ip_address}.{timestamp}"

    @cached_property
    def client_key(self):
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
    def ip_address(self):
        if self.smarter_request:
            return self.smarter_request.META.get("REMOTE_ADDR", "") or "ip_address"
        return None

    @cached_property
    def user_agent(self):
        if self.smarter_request:
            return self.smarter_request.META.get("HTTP_USER_AGENT", "") or "user_agent"
        return None

    @cached_property
    def is_config(self) -> bool:
        """
        Returns True if the url resolves to a config endpoint.
        """
        return self.url_path_parts[-1] == "config"

    @cached_property
    def is_dashboard(self) -> bool:
        """
        Returns True if the url resolves to a dashboard endpoint.
        """
        return self.url_path_parts[-1] == "dashboard"

    @cached_property
    def is_environment_root_domain(self):
        retval = self.parsed_url.netloc == smarter_settings.environment_domain and self.parsed_url.path == "/"
        self.helper_logger(f"is_environment_root_domain={retval}")
        return retval

    @property
    def is_chatbot(self) -> bool:
        """
        Returns True if the url resolves to a chatbot. Conditions are called in a lazy
        sequence intended to avoid unnecessary processing.
        """

        return (
            self.qualified_request
            and not self.is_environment_root_domain
            and not self.is_config
            and not self.is_dashboard
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
        example path_parts: ['api', 'v1', 'chatbots', '1', 'chat']
        """
        if self.url_path_parts[0] != "api":
            return False
        # expecting 'v1', 'v2', 'v3', etc. in the path
        if not re.match(r"^v\d+", self.url_path_parts[1]):
            return False
        return True

    @cached_property
    def is_chatbot_smarter_api_url(self) -> bool:
        """
        Returns True if the url is of the form http://localhost:8000/api/v1/chatbots/1/chat/
        path_parts: ['api', 'v1', 'chatbots', '1', 'chat']
        """
        if not self.is_smarter_api:
            return False

        path_parts = self.url_path_parts
        if path_parts[2] != "chatbots":
            return False
        if not path_parts[3].isnumeric():
            return False

        return True

    @cached_property
    def is_chatbot_cli_api_url(self) -> bool:
        """
        Returns True if the url is of the form http://localhost:8000/api/v1/cli/chat/example/
        path_parts: ['api', 'v1', 'cli', 'chat', 'example']
        """
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
        Returns True if the url is of the form https://example.3141-5926-5359.api.smarter.sh/
        """
        if not self.url:
            return False
        if not smarter_settings.environment_api_domain in self.url:
            return False
        if account_number_from_url(self.url):
            return True
        return False

    @cached_property
    def is_chatbot_sandbox_url(self) -> bool:
        """
        example urls:
        - https://alpha.platform.smarter.sh/chatbots/example/
          https://<environment_domain>/chatbots/<name>
          path_parts: ['chatbots', 'example']

        - https://alpha.platform.smarter.sh/chatbots/example/config/
          https://<environment_domain>/chatbots/<name>/config/
          path_parts: ['chatbots', 'example', 'config']
        """
        if not self.qualified_request:
            return False
        if not self.url:
            return False

        path_parts = self.url_path_parts
        # valid path_parts:
        #   ['chatbots', '<slug>']
        #   ['chatbots', '<slug>', 'config']
        if self.parsed_url.netloc != smarter_settings.environment_domain:
            self.helper_logger(
                f"is_chatbot_sandbox_url() - netloc != smarter_settings.environment_domain: {self.parsed_url.netloc} for url: {self.url}"
            )
            return False
        if len(path_parts) < 2:
            self.helper_logger(f"is_chatbot_sandbox_url() - len(path_parts) < 2: {path_parts} for url: {self.url}")
            return False
        if path_parts[0] != "chatbots":
            # expecting this form: ['chatbots', '<slug>', 'config']
            self.helper_logger(
                f"is_chatbot_sandbox_url() - path_parts[0] != 'chatbots': {path_parts} for url: {self.url}"
            )
            return False
        if not path_parts[1].isalpha():
            # expecting <slug> to be alpha: ['chatbots', '<slug>', 'config']
            self.helper_logger(
                f"is_chatbot_sandbox_url() - not path_parts[2].isalpha(): {path_parts} for url: {self.url}"
            )
            return False
        if len(path_parts) > 3:
            self.helper_logger(f"is_chatbot_sandbox_url() - len(path_parts) > 3: {path_parts} for url: {self.url}")
            return False

        if len(path_parts) == 2 and not path_parts[1].isalpha():
            # expecting: ['chatbots', '<slug>']
            self.helper_logger(
                f"is_chatbot_sandbox_url() - not path_parts[1].isalpha(): {path_parts} for url: {self.url}"
            )
            return False

        if len(path_parts) == 3 and not self.is_config:
            # expecting either of:
            # ['chatbots', '<slug>', 'config']
            # ['chatbots', '<slug>']
            self.helper_logger(f"is_chatbot_sandbox_url() - is not 'config' for url: {self.url}")
            return False

        return True

    @cached_property
    def is_default_domain(self) -> bool:
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
        if not self.url:
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
        return self.parsed_url.netloc if self.parsed_url else None

    # --------------------------------------------------------------------------
    # instance methods
    # --------------------------------------------------------------------------
    def generate_key(self) -> str:
        """
        Generate a session_key based on a unique string and the current datetime.
        """
        key_string = self.unique_client_string
        if key_string:
            session_key = hashlib.sha256(key_string.encode()).hexdigest()
            self.helper_logger(f"Generated new session key: {session_key}")
            return session_key

    def to_json(self) -> dict:
        """
        serializes the object.
        """
        return {
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
            "user": str(self.user) if self.user else None,
            "account": str(self.account) if self.account else None,
            "timestamp": self.timestamp.isoformat(),
            "unique_client_string": self.unique_client_string,
            "client_key": self.client_key,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "parsed_url": str(self.parsed_url) if self.parsed_url else None,
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
            # https://alpha.platform.smarter.sh/api/v1/chatbots/1/chatbot/
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

    def get_session_key(self) -> str:
        """
        Extract the session key from the URL, the request body, or the request headers.
        """
        if not self.smarter_request:
            self.helper_logger("get_session_key() - request is None")
            return None
        session_key: str = None

        if self._url:
            # this is our expected case. we look for the session key in th parsed url.
            query_params = parse_qs(self._url.query)
            session_key = query_params.get("session_key", [None])[0] if query_params else None
            session_key = session_key.strip() if isinstance(session_key, str) else None
            if session_key:
                self.helper_logger(
                    f"get_session_key() - session_key found in url: {session_key}",
                )
                return session_key

        # alternatively we look for the session key in the request body
        # and also in the request headers.
        session_key = (
            session_key_from_url(self.smarter_request.build_absolute_uri())
            or self.data.get(SMARTER_CHAT_SESSION_KEY_NAME)
            or self.smarter_request.GET.get(SMARTER_CHAT_SESSION_KEY_NAME)
        )

        session_key = session_key.strip() if isinstance(session_key, str) else None
        if session_key:
            self.helper_logger(f"get_session_key() - session_key found in url: {session_key}")
            return session_key

        # if we still don't have a session key, we generate a new one.
        session_key = self.generate_key()
        return session_key

    def dump(self):
        """
        Dump the object to the console.
        """
        return json.dumps(self.to_json(), indent=4)
