"""Django request helper class."""

import hashlib
import json
import logging
from datetime import datetime

import waffle

from smarter.apps.account.mixins import AccountMixin
from smarter.common.classes import SmarterHelperMixin
from smarter.common.const import SMARTER_CHAT_SESSION_KEY_NAME, SmarterWaffleSwitches
from smarter.common.helpers.url_helpers import session_key_from_url
from smarter.lib.django.user import UserType
from smarter.lib.django.validators import SmarterValidator, SmarterValueError


logger = logging.getLogger(__name__)


class SmarterRequestHelper(AccountMixin, SmarterHelperMixin):
    """
    Helper class for the Django request object that enforces authentication and
    provides lazy loading of the user, account, user profile and session_key
    """

    __slots__ = ["_request", "_request_timestamp", "_url", "_session_key", "_data"]

    def __init__(self, request):
        self._request = request
        self._request_timestamp = datetime.now()
        self._url: str = None
        self._session_key: str = None
        self._data: dict = None
        self._user: UserType = request.user if request.user.is_authenticated else None
        super().__init__(user=self._user)

    @property
    def request(self):
        return self._request

    @request.setter
    def request(self, request):
        self._request = request

    @property
    def request_timestamp(self):
        """
        create a consistent timestamp
        based on the time that this object was instantiated.
        """
        return self._request_timestamp

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
            logger.info("%s - data=%s", self.formatted_class_name, self._data)

        return self._data

    @property
    def unique_client_string(self):
        """
        Generate a unique string based on the client's IP address, user agent, and the current datetime.
        """
        return f"{self.account.account_number}{self.url}{self.user_agent}{self.ip_address}"

    @property
    def session_key(self):
        """
        Get the session key from one of the following:
         - url parameter
         - request json body
         - request header
         - a session_key generator
        """
        if not self._session_key:
            self._session_key = (
                session_key_from_url(self.url)
                or self.data.get(SMARTER_CHAT_SESSION_KEY_NAME)
                or self.request.GET.get(SMARTER_CHAT_SESSION_KEY_NAME)
            )
        self._session_key = self._session_key or self.generate_key()

        try:
            SmarterValidator.validate_session_key(self._session_key)
        except SmarterValueError as e:
            raise SmarterValueError(f"Illegal session_key format received: {e}") from e

        return self._session_key

    @property
    def client_key(self):
        """
        Generate a unique client key based on the client's IP address, user agent, and the current datetime.
        FIX NOTE: no longer in use?
        """
        return hashlib.sha256(self.unique_client_string.encode()).hexdigest()

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
        if self.request:
            self._url = self.request.build_absolute_uri()
        return self._url

    def generate_key(self) -> str:
        """
        Generate a session key based on a unique string and the current datetime.
        """
        key_string = self.unique_client_string + str(datetime.now())
        session_key = hashlib.sha256(key_string.encode()).hexdigest()
        logger.info("Generated new session key: %s", session_key)
        return session_key
