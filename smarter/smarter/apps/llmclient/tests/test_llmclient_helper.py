"""Test :class:`smarter.apps.llmclient.models.llmclient_helper.LLMClientHelper`."""

from unittest.mock import PropertyMock, patch
from urllib.parse import urlparse

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.llmclient.models import LLMClient
from smarter.apps.llmclient.models.llmclient_helper import LLMClientHelper
from smarter.common.conf import smarter_settings
from smarter.common.exceptions import SmarterValueError
from smarter.lib.django.request import SmarterRequestMixin

PLATFORM_HOST = urlparse(smarter_settings.environment_platform_url).netloc


class TestLLMClientHelper(TestAccountMixin):
    """Test the LLMClientHelper for an LLMClient of the test account."""

    def setUp(self):
        super().setUp()
        self.llmclient = LLMClient.objects.create(
            name=f"test_llmclient_helper_{self.hash_suffix}", user_profile=self.user_profile
        )
        self.addCleanup(self.llmclient.delete)

    def request(self, user=None):
        request = RequestFactory().get(
            f"/workbench/llm-clients/{self.llmclient.hashed_id}/prompt/", HTTP_HOST=PLATFORM_HOST
        )
        request.user = user or self.admin_user
        return request

    def helper(self, **kwargs) -> LLMClientHelper:
        kwargs.setdefault("user", self.admin_user)
        kwargs.setdefault("user_profile", self.user_profile)
        kwargs.setdefault("account", self.account)
        return LLMClientHelper(self.request(kwargs["user"]), **kwargs)

    def test_by_id(self):
        helper = self.helper(llmclient_id=self.llmclient.id)
        self.assertEqual(helper.llmclient, self.llmclient)
        self.assertEqual(helper.llmclient_id, self.llmclient.id)
        self.assertEqual(helper.name, self.llmclient.name)
        self.assertEqual(helper.llmclient_name, self.llmclient.name)
        self.assertEqual(helper.rfc1034_compliant_name, self.llmclient.name.replace("_", "-"))
        self.assertEqual(helper.account, self.account)
        self.assertIsInstance(helper.is_helper_ready, bool)
        self.assertIsInstance(helper.llmclienthelper_ready_state, str)
        self.assertIsInstance(helper.ready, bool)
        self.assertFalse(helper.is_deployed)
        self.assertIsInstance(helper.is_authentication_required, bool)
        self.assertIsNone(helper.provider)
        self.assertEqual(helper.llmclient_plugins_list, [])
        self.assertEqual(helper.llmclient_plugins_list_str, "")
        self.assertFalse(helper.is_custom_domain)
        self.assertIsNone(helper.llmclient_custom_domain)
        self.assertEqual(str(helper), f"{self.llmclient.name} ({self.llmclient.pk})")
        self.assertIsInstance(helper.to_json(), dict)
        helper.api_host  # pylint: disable=pointless-statement

    def test_by_instance_and_name(self):
        self.assertEqual(self.helper(llmclient=self.llmclient).llmclient, self.llmclient)
        self.assertEqual(self.helper(name=self.llmclient.name).llmclient, self.llmclient)
        # the hashed id in the request's url takes precedence over the name.
        self.assertEqual(self.helper(name="no_such_llmclient").llmclient, self.llmclient)

    def test_llmclient_setter(self):
        helper = self.helper()
        helper.llmclient = self.llmclient
        self.assertEqual(helper.llmclient_id, self.llmclient.id)
        helper.llmclient = None
        self.assertIsNone(helper._llmclient_id)  # pylint: disable=protected-access
        with self.assertRaises(SmarterValueError):
            helper.llmclient = "not an llmclient"

    def test_llmclient_id_setter(self):
        helper = self.helper()
        helper.llmclient_id = self.llmclient.id
        self.assertEqual(helper.llmclient, self.llmclient)

    def test_not_ready(self):
        """Test that the helper of an anonymous request, whose url names no LLMClient, is not ready."""
        request = RequestFactory().get("/workbench/", HTTP_HOST=PLATFORM_HOST)
        request.user = AnonymousUser()
        helper = LLMClientHelper(request)
        self.assertFalse(helper.is_helper_ready)
        self.assertFalse(helper.ready)
        self.assertIsNone(helper.llmclient)

    def test_ready_without_a_ready_request(self):
        """The helper is ready, even if its request isn't, as long as the helper itself is ready."""
        helper = self.helper(llmclient_id=self.llmclient.id)
        with patch.object(SmarterRequestMixin, "ready", new_callable=PropertyMock, return_value=False):
            with patch.object(LLMClientHelper, "is_helper_ready", new_callable=PropertyMock, return_value=True):
                self.assertTrue(helper.ready)
            with patch.object(LLMClientHelper, "is_helper_ready", new_callable=PropertyMock, return_value=False):
                self.assertFalse(helper.ready)


class TestLLMClientHelperNamedUrl(TestAccountMixin):
    """Test that a named url resolves the LLMClient whose rfc1034 compliant name is the url's first label."""

    def setUp(self):
        super().setUp()
        self.admin_llmclient = LLMClient.objects.create(
            name=f"named_url_{self.hash_suffix}_sql", user_profile=self.user_profile
        )
        self.addCleanup(LLMClient.objects.filter(pk=self.admin_llmclient.pk).delete)
        self.user_llmclient = LLMClient.objects.create(
            name=f"named_url_{self.hash_suffix}", user_profile=self.non_admin_user_profile
        )
        self.addCleanup(LLMClient.objects.filter(pk=self.user_llmclient.pk).delete)

    def helper(self, label: str, path: str = "/") -> LLMClientHelper:
        host = f"{label}.{self.account.account_number}.{smarter_settings.environment_api_domain}"
        request = RequestFactory().get(path, HTTP_HOST=host)
        request.user = AnonymousUser()
        return LLMClientHelper(request)

    def test_a_hyphenated_label_of_an_admin_llmclient(self):
        """The label of ``<name>_sql`` is ``<name>-sql``, which must not be read as ``<name>`` and a username."""
        helper = self.helper(self.admin_llmclient.rfc1034_compliant_name)
        self.assertEqual(helper.llmclient, self.admin_llmclient)
        self.assertEqual(helper.llmclient_id, self.admin_llmclient.id)

    def test_the_label_of_a_non_admin_llmclient(self):
        """The label of a non-admin user's LLMClient is ``<name>-<username>``."""
        helper = self.helper(self.user_llmclient.rfc1034_compliant_name)
        self.assertEqual(helper.llmclient, self.user_llmclient)

    def test_an_unknown_label_resolves_nothing(self):
        """A label that matches no LLMClient resolves None, and llmclient_id doesn't raise."""
        helper = self.helper(f"no-such-{self.hash_suffix}")
        self.assertIsNone(helper.llmclient)
        self.assertIsNone(helper.llmclient_id)
        self.assertIsNone(helper.llmclient_from_host_label())

    def test_the_config_and_prompt_paths(self):
        """A deployed host's /config/ and /prompt/ resolve its LLMClient, with or without a trailing slash."""
        for path in ("/config/", "/config", "/prompt/", "/prompt"):
            with self.subTest(path=path):
                helper = self.helper(self.admin_llmclient.rfc1034_compliant_name, path=path)
                self.assertEqual(helper.llmclient, self.admin_llmclient)

    def test_the_label_wins_over_the_callers_llmclient_of_a_shorter_name(self):
        """
        ``x-developer`` is ``x_developer`` for everyone, even for the owner of an LLMClient named ``x``.

        The name parsed from the url ends at the label's first hyphen, so a caller who owns ``x`` used to
        resolve ``x``, and its resolution was cached for every caller of the host.
        """
        decoy = LLMClient.objects.create(name=f"dev{self.hash_suffix}", user_profile=self.user_profile)
        self.addCleanup(LLMClient.objects.filter(pk=decoy.pk).delete)
        target = LLMClient.objects.create(name=f"dev{self.hash_suffix}_developer", user_profile=self.user_profile)
        self.addCleanup(LLMClient.objects.filter(pk=target.pk).delete)
        host = (
            f"{target.rfc1034_compliant_name}.{self.account.account_number}.{smarter_settings.environment_api_domain}"
        )
        for user in (AnonymousUser(), self.admin_user):
            with self.subTest(user=user):
                request = RequestFactory().get("/config/", HTTP_HOST=host)
                request.user = user
                self.assertEqual(LLMClientHelper(request).llmclient, target)

    def test_the_account_of_a_named_url(self):
        """A named url's account is the account in the url, the account of the LLMClient it names."""
        helper = self.helper(self.admin_llmclient.rfc1034_compliant_name)
        self.assertEqual(helper.account, self.account)

    def test_other_paths_are_not_named_urls(self):
        """Paths that a deployed host doesn't serve, e.g. the console's /dashboard/, resolve nothing."""
        for path in ("/dashboard/", "/jsi18n/", "/config/extra/"):
            with self.subTest(path=path):
                helper = self.helper(self.admin_llmclient.rfc1034_compliant_name, path=path)
                self.assertFalse(helper.is_llmclient_named_url)
                self.assertIsNone(helper.llmclient)
