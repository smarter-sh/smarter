# pylint: disable=wrong-import-position
"""Test API end points."""

from django.test import RequestFactory
from django.urls import get_urlconf, set_urlconf

# our stuff
from smarter.apps.account.tests.mixins import TestAccountMixin

from ..context_processors import base


class TestContext(TestAccountMixin):
    """Test Account context processor."""

    def test_context(self):
        """Test that we can instantiate the context."""
        rf = RequestFactory()
        request = rf.get("/login/")
        request.user = self.non_admin_user
        test_context = base(request=request)

        self.assertIn("account", test_context)
        self.assertIn("account_authentication", test_context)

    def test_context_on_a_deployed_llmclient_host(self):
        """The console urls resolve while a deployed LLMClient's urlconf is active."""
        rf = RequestFactory()
        request = rf.get("/")
        request.user = self.non_admin_user
        previous = get_urlconf()
        self.addCleanup(set_urlconf, previous)
        set_urlconf("smarter.urls.llmclients")

        test_context = base(request=request)

        self.assertEqual(test_context["account_authentication"]["forgot_password_url"], "/password-reset-request/")
