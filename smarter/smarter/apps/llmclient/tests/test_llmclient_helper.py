"""Test :class:`smarter.apps.llmclient.models.llmclient_helper.LLMClientHelper`."""

from urllib.parse import urlparse

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.llmclient.models import LLMClient
from smarter.apps.llmclient.models.llmclient_helper import LLMClientHelper
from smarter.common.conf import smarter_settings
from smarter.common.exceptions import SmarterValueError

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
        self.assertIn(self.llmclient.hashed_id, str(helper))
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
