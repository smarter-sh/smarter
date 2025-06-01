# pylint: disable=wrong-import-position
# pylint: disable=R0801
"""Test lambda_openai_v2 function."""

from django.test import RequestFactory

from smarter.apps.account.tests.mixins import TestAccountMixin

from ..context_processors import base


class TestContextProcessor(TestAccountMixin):
    """Test Dashboard context processor."""

    # pylint: disable=broad-exception-caught
    def test_base(self):
        """Test base."""
        rf = RequestFactory()
        request = rf.get("/login/")
        request.user = self.non_admin_user
        test_context = base(request=request)

        self.assertIn("dashboard", test_context)
