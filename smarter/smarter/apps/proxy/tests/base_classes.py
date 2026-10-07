"""
Test harness for the proxy app.

The tests never call a real LLM provider, DNS, or Celery:

- :class:`FakeProvider` answers the Proxies' requests, with an :class:`httpx.MockTransport`
  that :func:`~smarter.apps.proxy.services.configure_transport` installs. Without it, the
  forwarder refuses to call a provider from the unit tests.
- :func:`~smarter.apps.proxy.services.host_addresses` is patched to return a public address.
- :func:`~smarter.apps.proxy.services.record_charges` is patched, so that no Celery task is queued.
"""

import copy
import os
from typing import Any, Callable, Optional, Union
from unittest.mock import MagicMock, patch

import httpx

from smarter.apps.account.models import UserProfile
from smarter.apps.account.tests.factories import mortal_user_factory
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.provider.models import Provider
from smarter.apps.proxy.models import Proxy
from smarter.apps.proxy.services import configure_transport
from smarter.apps.secret.models import Secret
from smarter.apps.secret.tests.factories import secret_factory
from smarter.common.utils import get_readonly_yaml_file
from smarter.lib import json
from smarter.lib.drf.models import SmarterAuthToken

HERE = os.path.abspath(os.path.dirname(__file__))
DATA_PATH = os.path.join(HERE, "data")

PROVIDER_NAME = "test_proxy_provider"
SECRET_NAME = "test_proxy_api_key"
API_KEY = "sk-test-provider-api-key-0123456789"
BASE_URL = "https://api.example-llm.com/v1/"
PUBLIC_ADDRESS = "93.184.215.14"

FakeResponse = Union[httpx.Response, Callable[[httpx.Request], httpx.Response], Exception]


def get_data_path(filename: str) -> str:
    """Return the full path of a file in ./data."""
    return os.path.join(DATA_PATH, filename)


def get_test_data(filename: str) -> Any:
    """Return the parsed contents of a yaml file in ./data."""
    return copy.deepcopy(get_readonly_yaml_file(get_data_path(filename)))


def get_test_text(filename: str) -> bytes:
    """Return the contents of a file in ./data."""
    with open(get_data_path(filename), "rb") as f:
        return f.read()


def json_response(data: Any, status: int = 200, headers: Optional[dict] = None) -> httpx.Response:
    """A provider's JSON response."""
    return httpx.Response(
        status, content=json.dumps(data).encode(), headers={"content-type": "application/json", **(headers or {})}
    )


def sse_response(content: bytes, status: int = 200) -> httpx.Response:
    """A provider's server-sent event stream."""
    return httpx.Response(status, content=content, headers={"content-type": "text/event-stream"})


class FakeProvider:
    """
    A fake LLM provider: it records each request, and answers it with the next queued response.

    A queued response may be an :class:`httpx.Response`, a function of the request that returns
    one, or an exception to raise, e.g. :class:`httpx.ConnectError`. With none queued, it answers
    with an OpenAI-style chat completion.
    """

    def __init__(self):
        self.requests: list[httpx.Request] = []
        self.responses: list[FakeResponse] = []

    def reset(self) -> None:
        self.requests.clear()
        self.responses.clear()

    def queue(self, *responses: FakeResponse) -> None:
        self.responses.extend(responses)

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        response = self.responses.pop(0) if self.responses else None
        if response is None:
            return json_response(get_test_data("responses.yaml")["openai_chat_completion"])
        if isinstance(response, Exception):
            raise response
        if callable(response):
            return response(request)
        return response

    @property
    def last_request(self) -> httpx.Request:
        return self.requests[-1]

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handler)


class ProxyTestBase(TestAccountMixin):
    """
    Base class of the proxy app's tests.

    It creates a Provider, owned by the test account's admin user, with an API key Secret, and a
    :class:`FakeProvider` that answers every Proxy's requests.

    The test account's admin user is a superuser. :attr:`staff_user`, who is not, is the typical
    caller, whose API keys the tests create: Smarter only creates API keys for staff users.
    :attr:`non_admin_user` is neither.
    """

    provider: Provider
    secret: Secret
    fake: FakeProvider
    record_charges: MagicMock
    _patchers: list

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.staff_user, _, cls.staff_user_profile = mortal_user_factory(account=cls.account)
        cls.staff_user.is_staff = True
        cls.staff_user.save()
        cls.secret = secret_factory(
            user_profile=cls.user_profile, name=SECRET_NAME, description="A fake provider's API key.", value=API_KEY
        )
        cls.provider = Provider.objects.create(
            user_profile=cls.user_profile,
            name=PROVIDER_NAME,
            description="A fake OpenAI-compatible provider, for unit testing.",
            base_url=BASE_URL,
            api_key=cls.secret,
        )
        cls.fake = FakeProvider()
        configure_transport(cls.fake.transport)
        cls.record_charges = MagicMock()
        cls._patchers = [
            patch("smarter.apps.proxy.services.host_addresses", return_value=[PUBLIC_ADDRESS]),
            patch("smarter.apps.proxy.services.record_charges", cls.record_charges),
        ]
        for patcher in cls._patchers:
            patcher.start()

    @classmethod
    def tearDownClass(cls):
        for patcher in cls._patchers:
            patcher.stop()
        configure_transport(None)
        Proxy.objects.filter(user_profile__account=cls.account).delete()
        Provider.objects.filter(user_profile__account=cls.account).delete()
        Secret.objects.filter(user_profile__account=cls.account).delete()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.fake.reset()
        self.record_charges.reset_mock()

    @classmethod
    def create_proxy(cls, name: str, user_profile: Optional[UserProfile] = None, **fields) -> Proxy:
        """Create a Proxy of the test Provider.

        The caller deletes it.
        """
        defaults = {
            "provider": cls.provider,
            "api_key_secret": cls.secret,
            "description": f"{name}, for unit testing.",
            "allowed_paths": ["chat/completions", "embeddings", "models", "models/*"],
        }
        return Proxy.objects.create(name=name, user_profile=user_profile or cls.user_profile, **{**defaults, **fields})

    def proxy(self, name: str, user_profile: Optional[UserProfile] = None, **fields) -> Proxy:
        """Create a Proxy for one test, which is deleted after it."""
        proxy = self.create_proxy(name, user_profile=user_profile, **fields)
        self.addCleanup(Proxy.objects.filter(pk=proxy.pk).delete)
        return proxy

    def api_key(self, user_profile: Optional[UserProfile] = None) -> str:
        """A Smarter API key of a staff user, by default :attr:`staff_user`, for one test."""
        user_profile = user_profile or self.staff_user_profile
        record, key = SmarterAuthToken.objects.create(  # type: ignore[misc]
            user_profile=user_profile,
            name=f"test_proxy_{self._testMethodName}"[:50],
            user=user_profile.user,
            description="A Smarter API key, for unit testing.",
            is_active=True,
        )
        self.addCleanup(SmarterAuthToken.objects.filter(pk=record.pk).delete)
        return key
