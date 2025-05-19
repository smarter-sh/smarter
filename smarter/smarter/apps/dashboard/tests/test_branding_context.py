# pylint: disable=wrong-import-position
"""Test global context processor."""


from django.test import RequestFactory

# our stuff
from smarter.apps.account.tests.mixins import TestAccountMixin

from ..context_processors import branding


class TestContext(TestAccountMixin):
    """Test global context processor."""

    def test_context(self):
        """test that we can instantiate the context."""
        rf = RequestFactory()
        request = rf.get("/")
        request.user = self.user
        test_context = branding(request=request)

        self.assertIn("branding", test_context)
        branding_context = test_context["branding"]
        self.assertIn("root_url", branding_context)
        self.assertIn("support_phone_number", branding_context)
        self.assertIn("corporate_name", branding_context)
        self.assertIn("support_email", branding_context)
        # asset that support_email is a valid email
        self.assertIn("@", branding_context["support_email"])
