# pylint: disable=wrong-import-position
"""Test API end points."""

from django.test import RequestFactory

# our stuff
from smarter.apps.account.tests.mixins import TestAccountMixin

from ..context_processors import base


class TestContext(TestAccountMixin):
    """Test Account context processor."""

    def test_context(self):
        """test that we can instantiate the context."""
        rf = RequestFactory()
        request = rf.get("/login/")
        request.user = self.non_admin_user
        test_context = base(request=request)

        self.assertIn("account", test_context)
        self.assertIn("account_authentication", test_context)
