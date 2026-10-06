"""
Test the defensive and fallback branches of :class:`smarter.lib.django.request.SmarterRequestMixin`.

test_request_url_probes.py reads every property for a table of well-formed urls.
These tests cover what a well-formed url never reaches: a url that names a
different account than the caller's, Bearer tokens, session keys in the query
string, unreadable request bodies, and properties whose inputs (parsed_url,
url, url_path_parts) are missing or malformed.
"""

from unittest.mock import MagicMock, PropertyMock, patch
from urllib.parse import urlparse, urlsplit

from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest, RawPostDataException
from django.test import RequestFactory

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.common.conf import smarter_settings
from smarter.common.const import SMARTER_CHAT_SESSION_KEY_NAME
from smarter.common.exceptions import SmarterValueError
from smarter.lib.django.request import SmarterRequestMixin

SESSION_KEY = "9913baee675fb6618519c478bd4805c4ff9eeaab710e4f127ba67bb1eb442126"
MODULE = "smarter.lib.django.request"


class TestSmarterRequestBranches(TestAccountMixin):
    """Exercise SmarterRequestMixin's error and fallback branches."""

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()

    def request(self, url: str, user=None, **extra):
        parts = urlsplit(url)
        path = parts.path + (f"?{parts.query}" if parts.query else "")
        request = self.factory.get(path, HTTP_HOST=parts.netloc, **extra)
        request.user = user or self.admin_user
        return request

    def srm(self, url: str, **kwargs) -> SmarterRequestMixin:
        return SmarterRequestMixin(self.request(url, **kwargs))

    def named_url(self, account_number: str) -> str:
        return f"http://example.{account_number}.{smarter_settings.environment_api_domain}/config/"

    # -------------------------------------------------------------------------
    # account numbers in named urls
    # -------------------------------------------------------------------------
    def test_named_url_for_another_account_is_rejected(self):
        """A named url for a different account than the caller's raises."""
        with patch.object(
            SmarterRequestMixin, "url_account_number", new_callable=PropertyMock, return_value="9999-8888-7777"
        ):
            with self.assertRaises(SmarterValueError):
                SmarterRequestMixin(self.request(self.named_url("9999-8888-7777")), account=self.account)

    def test_named_url_lazy_loads_account_and_user(self):
        """A named url's account, and its admin, are loaded from the url's account number."""
        with patch.object(
            SmarterRequestMixin,
            "url_account_number",
            new_callable=PropertyMock,
            return_value=self.account.account_number,
        ):
            srm = self.srm(self.named_url(self.account.account_number), user=AnonymousUser())
            srm.account = None
            self.assertTrue(SmarterRequestMixin.is_llmclient_named_url.func(srm))
            self.assertEqual(srm.account, self.account)
            srm.account = None
            srm.eval_llmclient_url()
            self.assertEqual(srm.account, self.account)
            self.assertIsNotNone(srm.user)

    def test_cached_url_account_number(self):
        srm = self.srm("http://localhost:9357/dashboard/")
        srm._url_account_number = self.account.account_number
        self.assertEqual(srm.url_account_number, self.account.account_number)

    # -------------------------------------------------------------------------
    # the request setter and the request-less instance
    # -------------------------------------------------------------------------
    def test_unbuildable_url_raises(self):
        with patch(f"{MODULE}.smarter_build_absolute_uri", return_value=None):
            with self.assertRaises(SmarterValueError):
                self.srm("http://localhost:9357/dashboard/")

    def test_user_mismatch_raises(self):
        srm = self.srm("http://localhost:9357/dashboard/")
        with self.assertRaises(SmarterValueError):
            srm.smarter_request = self.request("http://localhost:9357/dashboard/", user=self.non_admin_user)

    def test_no_request(self):
        """Every request-derived property returns its empty value when there's no request."""
        srm = SmarterRequestMixin(None)
        self.assertIsNone(srm.url)
        self.assertEqual(srm.params.dict(), {})
        self.assertIsNone(srm.url_account_number)
        self.assertIsNone(srm.subdomain)
        self.assertIsNone(srm.domain)
        self.assertFalse(srm.srm_ready)
        srm.log_ready_status()

    def test_url_from_a_string(self):
        """A string _url is urlified, and its query string and fragment are dropped."""
        srm = self.srm("http://localhost:9357/dashboard/")
        srm._url = "http://localhost:9357/dashboard/?a=1#top"
        self.assertEqual(srm.url, "http://localhost:9357/dashboard/")

    def test_url_from_an_invalid_string(self):
        srm = self.srm("http://localhost:9357/dashboard/")
        srm._url = "not a url"
        with patch(f"{MODULE}.SmarterValidator.urlify", side_effect=SmarterValueError("invalid")):
            self.assertIsNone(srm.url)

    def test_url_before_initialization(self):
        srm = self.srm("http://localhost:9357/dashboard/")
        srm._url = None
        self.assertIsNone(srm.url)

    def test_params_without_meta(self):
        srm = self.srm("http://localhost:9357/dashboard/")
        srm._smarter_request = object()
        self.assertEqual(srm.params.dict(), {})

    def test_set_is_internal_api_request_rejects_non_requests(self):
        srm = self.srm("http://localhost:9357/dashboard/")
        with self.assertRaises(SmarterValueError):
            srm.set_is_internal_api_request("not a request")
        request = srm.set_is_internal_api_request(HttpRequest())
        self.assertTrue(srm.is_internal_api_request(request))

    # -------------------------------------------------------------------------
    # authorization headers and session keys
    # -------------------------------------------------------------------------
    def test_bearer_token(self):
        srm = self.srm("http://localhost:9357/dashboard/", HTTP_AUTHORIZATION="Bearer abc123")
        self.assertEqual(srm.api_token, b"abc123")

    def test_session_key_from_query_string(self):
        url = f"http://localhost:9357/workbench/example/config/?{SMARTER_CHAT_SESSION_KEY_NAME}={SESSION_KEY}/"
        srm = self.srm(url)
        self.assertEqual(srm.find_session_key(), SESSION_KEY)
        srm._session_key = SESSION_KEY
        self.assertEqual(srm.session_key, SESSION_KEY)

    # -------------------------------------------------------------------------
    # the request body
    # -------------------------------------------------------------------------
    def test_cached_data_is_returned(self):
        srm = self.srm("http://localhost:9357/api/v1/cli/apply/")
        srm._data = {"cached": True}
        self.assertEqual(srm.data, {"cached": True})

    def test_unreadable_body(self):
        """A body that's already been consumed, or isn't text, parses to nothing."""
        srm = self.srm("http://localhost:9357/api/v1/cli/apply/")
        with patch.object(HttpRequest, "body", new_callable=PropertyMock, side_effect=RawPostDataException()):
            self.assertFalse(srm.data)

    def test_undecodable_body(self):
        srm = self.srm("http://localhost:9357/api/v1/cli/apply/")
        with patch.object(HttpRequest, "body", new_callable=PropertyMock, return_value=b"\xff\xfe\xfa"):
            self.assertFalse(srm.data)

    def test_non_text_body(self):
        srm = self.srm("http://localhost:9357/api/v1/cli/apply/")
        with patch.object(HttpRequest, "body", new_callable=PropertyMock, return_value=12345):
            self.assertFalse(srm.data)

    # -------------------------------------------------------------------------
    # classification with missing or malformed url parts
    # -------------------------------------------------------------------------
    def test_path_parts_from_bytes(self):
        srm = self.srm("http://localhost:9357/a/b/")
        with patch.object(
            SmarterRequestMixin,
            "parsed_url",
            new_callable=PropertyMock,
            return_value=urlparse(b"http://localhost:9357/a/b/"),
        ):
            self.assertEqual(srm.url_path_parts, ["a", "b"])

    def test_missing_parsed_url(self):
        """Every classification is False, and every url part is None, without a parsed url."""
        srm = self.srm("http://localhost:9357/dashboard/")
        with patch.object(SmarterRequestMixin, "parsed_url", new_callable=PropertyMock, return_value=None):
            self.assertFalse(SmarterRequestMixin.qualified_request.fget(srm))
            self.assertFalse(srm.is_environment_root_domain)
            self.assertIsNone(srm.domain)
            self.assertIsNone(srm.path)
        with patch.object(SmarterRequestMixin, "qualified_request", new_callable=PropertyMock, return_value=True):
            with patch.object(SmarterRequestMixin, "parsed_url", new_callable=PropertyMock, return_value=None):
                self.assertFalse(SmarterRequestMixin.is_llmclient_smarter_api_url.func(srm))
                self.assertFalse(SmarterRequestMixin.is_llmclient_sandbox_url.func(srm))

    def test_missing_url(self):
        srm = self.srm("http://localhost:9357/dashboard/")
        with patch.object(SmarterRequestMixin, "url", new_callable=PropertyMock, return_value=None):
            self.assertFalse(srm.is_smarter_api)
            self.assertFalse(srm.is_default_domain)
            self.assertIsNone(srm.root_domain)
            self.assertIsNone(srm.subdomain)
            with patch.object(SmarterRequestMixin, "qualified_request", new_callable=PropertyMock, return_value=True):
                self.assertFalse(SmarterRequestMixin.is_llmclient_named_url.func(srm))

    def test_unextractable_root_domain(self):
        srm = self.srm("http://localhost:9357/dashboard/")
        with patch.object(SmarterRequestMixin, "url", new_callable=PropertyMock, return_value="http://123/"):
            with patch(f"{MODULE}.tldextract.extract", return_value=MagicMock(domain="", suffix="")):
                self.assertIsNone(srm.root_domain)

    def test_amnesty_url_is_not_qualified(self):
        srm = self.srm("http://localhost:9357/dashboard/")
        with patch.object(
            SmarterRequestMixin, "amnesty_urls", new_callable=PropertyMock, return_value=["/dashboard/"], create=True
        ):
            self.assertFalse(SmarterRequestMixin.qualified_request.fget(srm))

    def test_empty_path(self):
        srm = self.srm("http://localhost:9357/dashboard/")
        with patch.object(
            SmarterRequestMixin, "parsed_url", new_callable=PropertyMock, return_value=urlparse("http://localhost")
        ):
            self.assertEqual(srm.path, "/")

    def test_malformed_url_path_parts(self):
        """Is_config, is_dashboard and is_workbench are False for missing or empty path parts."""
        srm = self.srm("http://localhost:9357/dashboard/")
        with patch.object(SmarterRequestMixin, "is_llmclient", new_callable=PropertyMock, return_value=True):
            for parts in (None, []):
                with self.subTest(parts=parts):
                    with patch.object(
                        SmarterRequestMixin, "url_path_parts", new_callable=PropertyMock, return_value=parts
                    ):
                        self.assertFalse(SmarterRequestMixin.is_config.func(srm))
                        self.assertFalse(SmarterRequestMixin.is_dashboard.func(srm))
                        self.assertFalse(SmarterRequestMixin.is_workbench.func(srm))

    def test_dashboard_and_workbench_outside_their_paths(self):
        """A url whose last part is 'dashboard' or 'workbench' must also contain that path."""
        srm = self.srm("http://localhost:9357/x/")
        for name in ("dashboard", "workbench"):
            with self.subTest(name=name):
                with patch.object(
                    SmarterRequestMixin, "url_path_parts", new_callable=PropertyMock, return_value=["x", name]
                ):
                    self.assertFalse(getattr(SmarterRequestMixin, f"is_{name}").func(srm))

    def test_sandbox_url_shapes(self):
        """Hashed-id workbench urls that aren't workbench/llm-clients/<id>/<page> aren't sandbox urls."""
        srm = self.srm("http://localhost:9357/x/")
        domain = smarter_settings.environment_platform_domain
        cases = [
            ["other", "llm-clients", "abc", "prompt"],
            ["workbench", "other", "abc", "prompt"],
            ["workbench", "llm-clients", "abc", "other"],
            ["workbench", "llm-clients", "abc", "config"],
        ]
        for parts in cases:
            with self.subTest(parts=parts):
                with (
                    patch.object(
                        SmarterRequestMixin, "qualified_request", new_callable=PropertyMock, return_value=True
                    ),
                    patch.object(SmarterRequestMixin, "url_path_parts", new_callable=PropertyMock, return_value=parts),
                    patch.object(
                        SmarterRequestMixin,
                        "parsed_url",
                        new_callable=PropertyMock,
                        return_value=urlparse(f"http://{domain}/{'/'.join(parts)}/"),
                    ),
                    patch(f"{MODULE}.TimestampedModel.find_hash", return_value="abc"),
                ):
                    expected = parts[-1] == "config"
                    self.assertEqual(SmarterRequestMixin.is_llmclient_sandbox_url.func(srm), expected)

    def test_hyphenated_llmclient_names(self):
        """A hyphenated llmclient name in a named or cli url is truncated at the first hyphen."""
        srm = self.srm(f"http://my-bot.{self.account.account_number}.{smarter_settings.environment_api_domain}/")
        self.assertEqual(srm.smarter_request_llmclient_name, "my")
        srm = self.srm("http://localhost:9357/api/v1/cli/prompt/my-bot/")
        self.assertEqual(srm.smarter_request_llmclient_name, "my")

    def test_srm_ready_with_malformed_url(self):
        srm = self.srm("http://localhost:9357/dashboard/")
        srm._srm_ready = False
        with patch.object(SmarterRequestMixin, "parsed_url", new_callable=PropertyMock, return_value="not parsed"):
            self.assertFalse(srm.srm_ready)
        with patch.object(SmarterRequestMixin, "url", new_callable=PropertyMock, return_value=None):
            self.assertFalse(srm.srm_ready)
