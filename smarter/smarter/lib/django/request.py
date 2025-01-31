"""Django request helper class."""

import hashlib
import json
import logging
from datetime import datetime
from urllib.parse import ParseResult, urlparse

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
    - http://example.3141-5926-5359.api.localhost:8000/
    - http://example.3141-5926-5359.api.localhost:8000/?session_key=9913baee675fb6618519c478bd4805c4ff9eeaab710e4f127ba67bb1eb442126
    - http://example.3141-5926-5359.api.localhost:8000/config/
    - http://example.3141-5926-5359.api.localhost:8000/config/?session_key=9913baee675fb6618519c478bd4805c4ff9eeaab710e4f127ba67bb1eb442126

    session_key is a unique identifier for a chat session.
    It originates from generate_key() in this class.
    """

    __slots__ = ["_request", "_timestamp", "_session_key", "_data"]

    def __init__(self, request):
        self.request = request
        self._timestamp = datetime.now()
        self._session_key: str = None
        self._data: dict = None
        if hasattr(request, "user"):
            self.user: UserType = request.user if request.user.is_authenticated else None
        else:
            self.helper_logger("SmarterRequestMixin - 'WSGIRequest' object has no attribute 'user'")
        if self.is_named_url:
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
        if not self.is_chatbot:
            # session_key is only relevant for chatbots
            # the request object IN THEORY should only send
            # a session_key for a chatbot url.
            return None
        self._session_key = (
            session_key_from_url(self.url)
            or self.data.get(SMARTER_CHAT_SESSION_KEY_NAME)
            or self.request.GET.get(SMARTER_CHAT_SESSION_KEY_NAME)
        )
        self._session_key = self._session_key or self.generate_key()
        SmarterValidator.validate_session_key(self._session_key)
        return self._session_key

    @property
    def client_key(self):
        """
        for smarter.sh/v1 api endpoints, the client_key is used to identify the client.
        Generate a unique client key based on the client's IP address, user agent, and the current datetime.
        """
        return self.generate_key()

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

    @property
    def url(self):
        """
        The URL to parse.
        :return: The URL to parse.

        examples:
        - http://testserver
        - http://localhost:8000/
        - http://localhost:8000/docs/
        - http://localhost:8000/dashboard/
        - https://alpha.platform.smarter.sh/api/v1/chatbots/1/chatbot/
        - http://example.com/contact/
        - https://hr.3141-5926-5359.alpha.api.smarter.sh/chatbot/
        - https://hr.smarter.querium.com/chatbot/
        """
        if self.request:
            self._url = self.request.build_absolute_uri()
        return self._url

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
        return self.is_named_url or self.is_sandbox_domain

    @property
    def is_named_url(self) -> bool:
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
    def is_sandbox_domain(self) -> bool:
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
            return False
        if not self.user:
            return False
        if not self.user.is_authenticated:
            return False

        path_parts = self.parsed_url.path.split("/")
        # valid path_parts:
        #   ['', 'chatbots', '<slug>']
        #   ['', 'chatbots', '<slug>', '']
        #   ['', 'chatbots', '<slug>', 'config']
        #   ['', 'chatbots', '<slug>', 'config', '']
        if not path_parts:
            self.helper_logger(f"is_sandbox_domain() - not path_parts: {path_parts} for url: {self.url}")
            return False
        if self.parsed_url.netloc != smarter_settings.environment_domain:
            self.helper_logger(
                f"is_sandbox_domain() - netloc != smarter_settings.environment_domain: {self.parsed_url.netloc} for url: {self.url}"
            )
            return False
        if len(path_parts) < 3:
            self.helper_logger(f"is_sandbox_domain() - len(path_parts) < 3: {path_parts} for url: {self.url}")
            return False
        if path_parts[1] != "chatbots":
            # expecting this form: ['', 'chatbots', '<slug>', 'config', '']
            self.helper_logger(f"is_sandbox_domain() - path_parts[1] != 'chatbots': {path_parts} for url: {self.url}")
            return False
        if not path_parts[2].isalpha():
            # expecting <slug> to be alpha: ['', 'chatbots', '<slug>', 'config', '']
            self.helper_logger(f"is_sandbox_domain() - not path_parts[2].isalpha(): {path_parts} for url: {self.url}")
            return False
        if len(path_parts) > 5:
            self.helper_logger(f"is_sandbox_domain() - len(path_parts) > 5: {path_parts} for url: {self.url}")
            return False

        if len(path_parts) == 3 and not path_parts[2].isalpha():
            # expecting: ['', 'chatbots', '<slug>']
            self.helper_logger(f"is_sandbox_domain() - not path_parts[2].isalpha(): {path_parts} for url: {self.url}")
            return False

        if len(path_parts) == 4 and not path_parts[3] in ["config", ""]:
            # expecting either of:
            # ['', 'chatbots', '<slug>', 'config']
            # ['', 'chatbots', '<slug>', '']
            self.helper_logger(f"is_sandbox_domain() - not 'config' in path_parts[3]: {path_parts} for url: {self.url}")
            return False
        if len(path_parts) == 5 and path_parts[3] != "config":
            # expecting: ['', 'chatbots', '<slug>', 'config', '']
            self.helper_logger(f"is_sandbox_domain() - not 'config' in path_parts[4]: {path_parts} for url: {self.url}")
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
        validate and parse the url in a ParseResult.
        """
        if self.url:
            SmarterValidator.validate_url(self.url)
            return urlparse(self._url)
        return None

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

    def to_json(self) -> dict:
        """
        serializes the object.
        """
        return {
            "url": self.url,
            "session_key": self.session_key,
            "data": self.data,
            "is_chatbot": self.is_chatbot,
            "is_named_url": self.is_named_url,
            "is_sandbox_domain": self.is_sandbox_domain,
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
            "parsed_url": str(self.parsed_url),
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
