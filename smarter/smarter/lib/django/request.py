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
import warnings
from datetime import datetime
from urllib.parse import ParseResult, parse_qs, urlparse, urlunsplit

import tldextract
import waffle

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
from smarter.lib.django.user import UserType
from smarter.lib.django.validators import SmarterValidator, SmarterValueError


logger = logging.getLogger(__name__)


class SmarterRequestMixin(AccountMixin, SmarterHelperMixin):
    """
    Helper class for the Django request object that enforces authentication and
    provides lazy loading of the user, account, user profile and session_key.

    Works with any Django request object and any valid url, but is designed
    as a helper class for Smarter ChatBot urls.

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
    - https://hr.smarter.querium.com/

    session_key is a unique identifier for a chat session.
    It originates from generate_key() in this class.
    """

    __slots__ = ["_request", "_timestamp", "_session_key", "_data", "_url", "_url_urlunparse_without_params"]

    def __init__(self, request):
        # slot definition/initialization
        self._request = None
        self._timestamp = datetime.now()
        self._session_key: str = None
        self._url: ParseResult = None
        self._url_urlunparse_without_params: str = None
        self._data: dict = None

        # instance initialization
        self.request = request

        self.url = self.request.build_absolute_uri()
        self.session_key = self.get_session_key()

        if hasattr(request, "user"):
            self.user: UserType = request.user if request.user.is_authenticated else None
        else:
            self.helper_logger("SmarterRequestMixin - 'WSGIRequest' object has no attribute 'user'")
        if self.is_chatbot_named_url:
            account_number = account_number_from_url(self.url)
            self.account = get_cached_account(account_number=account_number)

            if self.account and not self._user:
                self._user = get_cached_admin_user_for_account(account=self.account)
        super().__init__(user=self._user)
        self.eval_chatbot_url()

    @property
    def request(self):
        return self._request

    @request.setter
    def request(self, request):
        if not request:
            raise SmarterValueError("request object is required")
        self._request = request
        self.helper_logger(f"@request.setter={self._request.build_absolute_uri()}")

    @property
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
            return self._url_urlunparse_without_params

    @url.setter
    def url(self, url: str):
        """
        validate, standardize and parse the request url string into a ParseResult.
        Note that the setter and getter both work with strings
        but we store the private instance variable _url as a ParseResult.
        """
        self._url = url
        if self._url:
            self._url = urlparse(url)
            self.helper_logger(f"@url.setter={self._url}")

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
        try:
            self._data = json.loads(self.request.body)
        except json.JSONDecodeError:
            self._data = {}

        if waffle.switch_is_active(SmarterWaffleSwitches.SMARTER_WAFFLE_SWITCH_CHATBOT_API_VIEW_LOGGING):
            self.helper_logger(f"data={self._data}")

        return self._data

    @property
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

    @property
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

    @property
    def ip_address(self):
        if self.request:
            return self.request.META.get("REMOTE_ADDR", "")
        return None

    @property
    def user_agent(self):
        if self.request:
            return self.request.META.get("HTTP_USER_AGENT", "")
        return None

    def generate_key(self) -> str:
        """
        Generate a session_key based on a unique string and the current datetime.
        """
        key_string = self.unique_client_string
        if key_string:
            session_key = hashlib.sha256(key_string.encode()).hexdigest()
            self.helper_logger(f"Generated new session key: {session_key}")
            return session_key

    @property
    def is_chatbot(self) -> bool:
        """
        Returns True if the url resolves to a chatbot.
        """
        return self.is_chatbot_named_url or self.is_chatbot_sandbox_url or self.is_chatbot_smarter_api_url

    @property
    def is_smarter_api(self) -> bool:
        """
        Returns True if the url is of the form http://localhost:8000/api/v1/
        example path_parts: ['', 'api', 'v1', 'chatbots', '1', 'chat', '']
        """
        path_parts = self.parsed_url.path.split("/")
        if not path_parts:
            return False
        if len(path_parts) < 7:
            return False
        if path_parts[1] != "api":
            return False
        if path_parts[2] != "v1":
            return False
        return True

    @property
    def is_chatbot_smarter_api_url(self) -> bool:
        """
        Returns True if the url is of the form http://localhost:8000/api/v1/chatbots/1/chat/
        path_parts: ['', 'api', 'v1', 'chatbots', '1', 'chat', '']
        """
        if not self.is_smarter_api:
            return False

        path_parts = self.parsed_url.path.split("/")
        if path_parts[3] != "chatbots":
            return False
        if not path_parts[4].isnumeric():
            return False

        return True

    @property
    def is_chatbot_named_url(self) -> bool:
        """
        Returns True if the url is of the form https://example.3141-5926-5359.api.smarter.sh/
        """
        if not self.url:
            return False
        if not smarter_settings.customer_api_domain in self.url:
            return False
        if account_number_from_url(self.url):
            return True
        return False

    @property
    def is_chatbot_sandbox_url(self) -> bool:
        """
        example urls:
        - https://alpha.platform.smarter.sh/chatbots/example/
          https://<environment_domain>/chatbots/<name>
          path_parts: ['', 'chatbots', 'example', '']

        - https://alpha.platform.smarter.sh/chatbots/example/config/
          https://<environment_domain>/chatbots/<name>/config/
          path_parts: ['', 'chatbots', 'example', 'config', '']
        """
        if not self.url:
            self.helper_logger(f"is_chatbot_sandbox_url() - not self.url: {self.url}")
            return False

        path_parts = self.parsed_url.path.split("/")
        # valid path_parts:
        #   ['', 'chatbots', '<slug>']
        #   ['', 'chatbots', '<slug>', '']
        #   ['', 'chatbots', '<slug>', 'config']
        #   ['', 'chatbots', '<slug>', 'config', '']
        if not path_parts:
            self.helper_logger(f"is_chatbot_sandbox_url() - not path_parts: {path_parts} for url: {self.url}")
            return False
        if self.parsed_url.netloc != smarter_settings.environment_domain:
            self.helper_logger(
                f"is_chatbot_sandbox_url() - netloc != smarter_settings.environment_domain: {self.parsed_url.netloc} for url: {self.url}"
            )
            return False
        if len(path_parts) < 3:
            self.helper_logger(f"is_chatbot_sandbox_url() - len(path_parts) < 3: {path_parts} for url: {self.url}")
            return False
        if path_parts[1] != "chatbots":
            # expecting this form: ['', 'chatbots', '<slug>', 'config', '']
            self.helper_logger(
                f"is_chatbot_sandbox_url() - path_parts[1] != 'chatbots': {path_parts} for url: {self.url}"
            )
            return False
        if not path_parts[2].isalpha():
            # expecting <slug> to be alpha: ['', 'chatbots', '<slug>', 'config', '']
            self.helper_logger(
                f"is_chatbot_sandbox_url() - not path_parts[2].isalpha(): {path_parts} for url: {self.url}"
            )
            return False
        if len(path_parts) > 5:
            self.helper_logger(f"is_chatbot_sandbox_url() - len(path_parts) > 5: {path_parts} for url: {self.url}")
            return False

        if len(path_parts) == 3 and not path_parts[2].isalpha():
            # expecting: ['', 'chatbots', '<slug>']
            self.helper_logger(
                f"is_chatbot_sandbox_url() - not path_parts[2].isalpha(): {path_parts} for url: {self.url}"
            )
            return False

        if len(path_parts) == 4 and not path_parts[3] in ["config", ""]:
            # expecting either of:
            # ['', 'chatbots', '<slug>', 'config']
            # ['', 'chatbots', '<slug>', '']
            self.helper_logger(
                f"is_chatbot_sandbox_url() - not 'config' in path_parts[3]: {path_parts} for url: {self.url}"
            )
            return False
        if len(path_parts) == 5 and path_parts[3] != "config":
            # expecting: ['', 'chatbots', '<slug>', 'config', '']
            self.helper_logger(
                f"is_chatbot_sandbox_url() - not 'config' in path_parts[4]: {path_parts} for url: {self.url}"
            )
            return False

        return True

    @property
    def is_default_domain(self) -> bool:
        if not self.url:
            return False
        return smarter_settings.customer_api_domain in self.url

    @property
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

    @property
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

    @property
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

    @property
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

    @property
    def parsed_url(self) -> ParseResult:
        """
        expose our private _url
        """
        return self._url

    @property
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
    def to_json(self) -> dict:
        """
        serializes the object.
        """
        return {
            "url": self.url,
            "session_key": self.session_key,
            "data": self.data,
            "is_smarter_api": self.is_smarter_api,
            "is_chatbot": self.is_chatbot,
            "is_chatbot_smarter_api_url": self.is_chatbot_smarter_api_url,
            "is_chatbot_named_url": self.is_chatbot_named_url,
            "is_chatbot_sandbox_url": self.is_chatbot_sandbox_url,
            "is_default_domain": self.is_default_domain,
            "path": self.path,
            "root_domain": self.root_domain,
            "subdomain": self.subdomain,
            "api_subdomain": self.api_subdomain,
            "domain": self.domain,
            "user": self.user if self.user else None,
            "account": self.account if self.account else None,
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
        if not self.account:
            account_number = account_number_from_url(self.url)
            self.account = get_cached_account(account_number=account_number)
        if not self.user:
            self.user = get_cached_admin_user_for_account(account=self.account)

    def helper_logger(self, message: str):
        """
        Create a log entry
        """
        if waffle.switch_is_active(SmarterWaffleSwitches.SMARTER_WAFFLE_SWITCH_REQUEST_MIXIN_LOGGING):
            logger.info(f"{self.formatted_class_name}: {message}")

    def get_session_key(self) -> str:
        """
        Extract the session key from the URL, the request body, or the request headers.
        """
        session_key: str = None

        if self._url:
            # this is our expected case. we look for the session key in th parsed url.
            query_params = parse_qs(self._url.query)
            session_key = query_params.get("session_key", [None])[0] if query_params else None
            if session_key:
                return session_key

        # alternatively we look for the session key in the request body
        # and also in the request headers.
        session_key = (
            session_key_from_url(self.request.build_absolute_uri())
            or self.data.get(SMARTER_CHAT_SESSION_KEY_NAME)
            or self.request.GET.get(SMARTER_CHAT_SESSION_KEY_NAME)
        )
        if session_key:
            return session_key

        # if we still don't have a session key, we generate a new one.
        self.helper_logger(f"Generating new session key for {self.url}")
        session_key = self.generate_key()
        return session_key
