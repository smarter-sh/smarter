"""Test each gate of :attr:`LLMClientHelper.is_helper_ready` for a helper whose LLMClient isn't resolved by lookup."""

from unittest.mock import MagicMock, PropertyMock, patch

from django.test import RequestFactory

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.llmclient.models import (
    LLMClient,
    LLMClientAPIKey,
    LLMClientCustomDomain,
    LLMClientRequests,
)
from smarter.apps.llmclient.models.llmclient_helper import LLMClientHelper
from smarter.common.exceptions import SmarterValueError

from .test_llmclient_helper import PLATFORM_HOST


class LLMClientHelperTestBase(TestAccountMixin):
    """A helper for a workbench url, whose ``llmclient`` lookup is patched to return None."""

    def setUp(self):
        super().setUp()
        self.llmclient = LLMClient.objects.create(
            name=f"test_llmclient_helper_readiness_{self.hash_suffix}", user_profile=self.user_profile
        )
        self.addCleanup(self.llmclient.delete)
        request = RequestFactory().get(
            f"/workbench/llm-clients/{self.llmclient.hashed_id}/prompt/", HTTP_HOST=PLATFORM_HOST
        )
        request.user = self.admin_user
        self.helper = LLMClientHelper(
            request, user=self.admin_user, user_profile=self.user_profile, account=self.account
        )
        # is_helper_ready is a cached_property, already evaluated by __init__().
        self.helper._is_llmclienthelper_ready = False
        self.helper.__dict__.pop("is_helper_ready", None)
        self.helper._llmclient = self.llmclient
        self.patch_property("llmclient", None)
        self.patch_property("llmclient_custom_domain", MagicMock())
        self.patch_property("is_llmclient", True)
        self.patch_property("user", MagicMock(is_authenticated=True, username="readiness"))
        self.patch_property("account", self.account)
        self.patch_property("name", self.llmclient.name)

    def patch_property(self, name: str, value) -> PropertyMock:
        patcher = patch.object(LLMClientHelper, name, new_callable=PropertyMock, return_value=value)
        mock = patcher.start()
        self.addCleanup(patcher.stop)
        return mock


class TestLLMClientHelperReadiness(LLMClientHelperTestBase):
    """
    Test is_helper_ready's fallback checks.

    The ``llmclient`` lookup is patched to return None, so that readiness is decided
    by the url, user, account, name and cached LLMClient checks in turn.
    """

    def assertNotReady(self):
        self.assertFalse(self.helper.is_helper_ready)
        self.assertIn("Not Ready", self.helper.llmclienthelper_ready_state)

    def test_ready_with_a_cached_llmclient(self):
        """Every check passes, so the helper is ready, and stays ready."""
        self.assertTrue(self.helper.is_helper_ready)
        self.assertTrue(self.helper.is_helper_ready)

    def test_not_an_llmclient_url(self):
        """A url that isn't an LLMClient's isn't ready."""
        self.patch_property("is_llmclient", False)
        self.assertNotReady()

    def test_unauthenticated(self):
        """An anonymous request isn't ready."""
        self.patch_property("user", MagicMock(is_authenticated=False))
        self.assertNotReady()
        self.patch_property("user", None)
        self.assertNotReady()

    def test_no_account(self):
        """A request without an account isn't ready."""
        self.patch_property("account", None)
        self.assertNotReady()

    def test_no_name(self):
        """A helper without an LLMClient name isn't ready."""
        self.patch_property("name", None)
        self.assertNotReady()

    def test_no_cached_llmclient(self):
        """A helper without an LLMClient isn't ready."""
        self.helper._llmclient = None
        self.assertNotReady()


class TestLLMClientHelperLookups(TestAccountMixin):
    """Test LLMClientHelper's initialization options and its llmclient_id lookup by name."""

    def setUp(self):
        super().setUp()
        self.llmclient = LLMClient.objects.create(
            name=f"test_llmclient_helper_lookups_{self.hash_suffix}", user_profile=self.user_profile
        )
        self.addCleanup(self.llmclient.delete)
        self.request = RequestFactory().get("/", HTTP_HOST=PLATFORM_HOST)
        self.request.user = self.admin_user

    def test_init_with_custom_domain_and_requests(self):
        """A custom domain and LLMClientRequests passed in are kept."""
        custom_domain = MagicMock(spec=LLMClientCustomDomain)
        llmclient_requests = MagicMock(spec=LLMClientRequests)
        helper = LLMClientHelper(
            self.request,
            user=self.admin_user,
            user_profile=self.user_profile,
            account=self.account,
            llmclient_custom_domain=custom_domain,
            llmclient_requests=llmclient_requests,
        )
        self.assertIs(helper._llmclient_custom_domain, custom_domain)
        self.assertIs(helper._llmclient_requests, llmclient_requests)

    def test_llmclient_id_from_the_name(self):
        """Without an id, an LLMClient or an id in the url, the id is found by the LLMClient's name."""
        helper = LLMClientHelper(
            self.request, user=self.admin_user, user_profile=self.user_profile, account=self.account
        )
        helper._llmclient_id = None
        helper._llmclient = None
        with patch.object(
            LLMClientHelper, "smarter_request_llmclient_id", new_callable=PropertyMock, return_value=None
        ):
            with patch.object(
                LLMClientHelper, "llmclient_name", new_callable=PropertyMock, return_value=self.llmclient.name
            ):
                self.assertEqual(helper.llmclient_id, self.llmclient.id)


class TestLLMClientHelperWithoutAnLLMClient(LLMClientHelperTestBase):
    """Test the LLMClientHelper properties that fall back when there's no LLMClient or request."""

    def setUp(self):
        super().setUp()
        self.helper._llmclient = None

    def test_without_an_llmclient(self):
        self.assertIsNone(self.helper.rfc1034_compliant_name)
        self.assertIsNone(self.helper.provider)
        self.assertEqual(self.helper.llmclient_plugins_list, [])
        self.patch_property("is_llmclient_sandbox_url", False)
        self.helper.__dict__.pop("is_authentication_required", None)
        self.assertFalse(self.helper.is_authentication_required)

    def test_authentication_required_by_an_active_api_key(self):
        self.patch_property("is_llmclient_sandbox_url", False)
        self.patch_property("llmclient", self.llmclient)
        self.helper.__dict__.pop("is_authentication_required", None)
        with patch.object(LLMClientAPIKey, "get_cached_objects") as api_keys:
            api_keys.return_value.filter.return_value.exists.return_value = True
            self.assertTrue(self.helper.is_authentication_required)

    def test_api_host_needs_a_qualified_request(self):
        for name, value in (("smarter_request", None), ("qualified_request", False)):
            with self.subTest(name=name):
                self.helper.__dict__.pop("api_host", None)
                with patch.object(LLMClientHelper, name, new_callable=PropertyMock, return_value=value):
                    self.assertIsNone(self.helper.api_host)

    def test_llmclient_id_from_the_url(self):
        self.helper._llmclient_id = None
        base_class = next(c for c in LLMClientHelper.__mro__[1:] if "smarter_request_llmclient_id" in vars(c))
        with patch.object(base_class, "smarter_request_llmclient_id", new_callable=PropertyMock, return_value=42):
            self.assertEqual(self.helper.llmclient_id, 42)

    def test_llmclient_id_of_another_account_is_refused(self):
        other = MagicMock()
        other.user_profile.cached_account = MagicMock()
        with patch.object(LLMClient, "get_cached_object", return_value=other):
            with self.assertRaises(SmarterValueError):
                self.helper.llmclient_id = 42
