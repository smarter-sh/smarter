"""
Test :class:`smarter.lib.django.request.SmarterRequestMixin` with a table of url shapes.

SmarterRequestMixin classifies a request by its url: the dashboard, the api,
the workbench, and the LLMClient's named, sandbox, cli and config urls. Every
property is read for every url, so that each classification's early returns are
exercised, and the classifications that matter are asserted.
"""

import inspect
from functools import cached_property
from urllib.parse import urlsplit

from django.test import RequestFactory

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.common.const import SMARTER_CHAT_SESSION_KEY_NAME
from smarter.lib import json
from smarter.lib.django.request import SmarterRequestMixin

SESSION_KEY = "9913baee675fb6618519c478bd4805c4ff9eeaab710e4f127ba67bb1eb442126"

URLS = [
    "http://testserver/",
    "http://localhost:9357/",
    "http://localhost:9357/docs/",
    "http://localhost:9357/dashboard/",
    "http://localhost:9357/dashboard/llm-clients/",
    "http://localhost:9357/workbench/example/",
    "http://localhost:9357/workbench/example/config/",
    "http://localhost:9357/workbench/example/prompt/",
    f"http://localhost:9357/workbench/example/config/?{SMARTER_CHAT_SESSION_KEY_NAME}={SESSION_KEY}",
    "http://localhost:9357/workbench/llm-clients/example/config/",
    "http://localhost:9357/workbench/llm-clients/example/manifest/",
    "http://localhost:9357/api/v1/workbench/1/prompt/",
    "http://localhost:9357/api/v1/workbench/1/config/",
    "http://localhost:9357/api/v1/workbench/1/other/",
    "http://localhost:9357/api/v1/workbench/not-a-number/prompt/",
    "http://localhost:9357/api/v1/llmclient/1/prompt/",
    "http://localhost:9357/api/v1/cli/prompt/example/",
    "http://localhost:9357/api/v1/cli/whoami/",
    "http://localhost:9357/api/v1/cli/apply/",
    "http://example.3141-5926-5359.api.localhost:9357/",
    "http://example.3141-5926-5359.api.localhost:9357/config/",
    f"http://example.3141-5926-5359.api.localhost:9357/config/?{SMARTER_CHAT_SESSION_KEY_NAME}={SESSION_KEY}",
    "https://hr.3141-5926-5359.alpha.api.smarter.sh/",
    "https://hr.3141-5926-5359.alpha.api.smarter.sh/config/",
    "https://alpha.platform.smarter.sh/api/v1/cli/prompt/example/",
    "https://alpha.platform.smarter.sh/api/v1/workbench/1/llm-client/",
    "https://alpha.platform.smarter.sh/dashboard/",
    "https://hr.smarter.sh/",
    "http://example.com/contact/",
    "http://localhost:9357/a/b/c/d/e/f/g/",
    "http://localhost:9357/llm-clients/example/workbench/",
    "http://localhost:9357/dashboard/workbench/",
]


def property_names() -> list[str]:
    """Return the names of SmarterRequestMixin's properties and cached properties."""
    names = []
    for cls in SmarterRequestMixin.__mro__:
        for name, member in vars(cls).items():
            if isinstance(member, (property, cached_property)) and name not in names:
                names.append(name)
    return names


class TestSmarterRequestUrlProbes(TestAccountMixin):
    """Read every property of SmarterRequestMixin for every url in URLS."""

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()

    def srm(self, url: str, method: str = "get", data=None, user=None) -> SmarterRequestMixin:
        parts = urlsplit(url)
        path = parts.path + (f"?{parts.query}" if parts.query else "")
        kwargs = {"HTTP_HOST": parts.netloc, "wsgi.url_scheme": parts.scheme}
        if method == "post":
            request = self.factory.post(path, data=json.dumps(data or {}), content_type="application/json", **kwargs)
        else:
            request = self.factory.get(path, **kwargs)
        request.user = user or self.admin_user
        return SmarterRequestMixin(request)

    def test_every_property_for_every_url(self):
        """Test that no property raises, for any url, and that the instance serializes."""
        names = property_names()
        self.assertGreater(len(names), 40)
        for url in URLS:
            srm = self.srm(url)
            for name in names:
                with self.subTest(url=url, property=name):
                    getattr(srm, name)
            with self.subTest(url=url, method="to_json"):
                self.assertIsInstance(srm.to_json(), dict)

    def test_classification(self):
        """Test the classifications of a few urls."""
        self.assertTrue(self.srm("http://localhost:9357/dashboard/").is_dashboard)
        self.assertFalse(self.srm("http://localhost:9357/dashboard/").is_smarter_api)
        self.assertTrue(self.srm("http://localhost:9357/api/v1/cli/whoami/").is_smarter_api)
        self.assertTrue(self.srm("http://localhost:9357/llm-clients/example/workbench/").is_workbench)
        self.assertFalse(self.srm("http://localhost:9357/workbench/example/").is_workbench)
        self.assertTrue(self.srm("http://example.3141-5926-5359.api.localhost:9357/").is_llmclient_named_url)
        self.assertTrue(self.srm("http://localhost:9357/api/v1/cli/prompt/example/").is_llmclient_cli_api_url)
        self.assertFalse(self.srm("http://example.com/contact/").is_llmclient)

    def test_llmclient_smarter_api_url(self):
        """/api/v1/workbench/<int:pk>/prompt/ and .../config/ are LLMClient smarter api urls, which carry the LLMClient's id."""
        for url in (
            "http://localhost:9357/api/v1/workbench/1/prompt/",
            "http://localhost:9357/api/v1/workbench/1/config/",
            "http://localhost:9357/api/v1/llm-clients/42/prompt/",
        ):
            with self.subTest(url=url):
                srm = self.srm(url)
                self.assertTrue(srm.is_llmclient_smarter_api_url)
                self.assertTrue(srm.is_llmclient)
                self.assertIsNone(srm.smarter_request_llmclient_name)
        self.assertEqual(
            self.srm("http://localhost:9357/api/v1/llm-clients/42/prompt/").smarter_request_llmclient_id, 42
        )
        for url in (
            "http://localhost:9357/api/v1/workbench/not-a-number/prompt/",
            "http://localhost:9357/api/v1/workbench/1/other/",
            "http://localhost:9357/api/v2/workbench/1/prompt/",
            "http://localhost:9357/apis/v1/workbench/1/prompt/",
            "http://localhost:9357/api/v1/llmclient/1/prompt/",
        ):
            with self.subTest(url=url):
                self.assertFalse(self.srm(url).is_llmclient_smarter_api_url)

    def test_session_key(self):
        """Test that the session key is read from the url, the request body, or a cookie."""
        url = f"http://localhost:9357/workbench/example/config/?{SMARTER_CHAT_SESSION_KEY_NAME}={SESSION_KEY}"
        self.assertEqual(self.srm(url).session_key, SESSION_KEY)
        srm = self.srm(
            "http://localhost:9357/api/v1/workbench/1/prompt/",
            method="post",
            data={SMARTER_CHAT_SESSION_KEY_NAME: SESSION_KEY},
        )
        self.assertEqual(srm.session_key, SESSION_KEY)

    def test_post_data(self):
        srm = self.srm("http://localhost:9357/api/v1/cli/apply/", method="post", data={"kind": "Guardrail"})
        self.assertEqual(srm.data, {"kind": "Guardrail"})

    def test_init_with_user_profile_and_account(self):
        """Test that the user, user profile and account can be passed to the constructor."""
        request = self.factory.get("/", HTTP_HOST="localhost:9357")
        srm = SmarterRequestMixin(request, user=self.admin_user, user_profile=self.user_profile, account=self.account)
        self.assertEqual(srm.user_profile, self.user_profile)
        self.assertEqual(srm.account, self.account)
        srm = SmarterRequestMixin(request, self.admin_user, self.user_profile, self.account)
        self.assertEqual(srm.account, self.account)

    def test_equality_and_hash(self):
        a = self.srm("http://localhost:9357/dashboard/")
        b = self.srm("http://localhost:9357/dashboard/")
        self.assertEqual(a, b)
        self.assertNotEqual(a, self.srm("http://localhost:9357/docs/"))
        self.assertNotEqual(a, "not a request")
        self.assertIsInstance(hash(a), int)
        self.assertTrue(bool(a))
