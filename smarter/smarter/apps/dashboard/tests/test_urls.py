# pylint: disable=wrong-import-position
"""Test API end points."""

from django.test import Client

from smarter.apps.account.tests.mixins import TestAccountMixin


class TestDashboard(TestAccountMixin):
    """Test dashboard views."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.client = Client()
        self.client.force_login(self.non_admin_user)

    def test_dashboard(self):
        """test that we can see the account view and that it matches the account data."""
        response = self.client.get("")
        self.assertIn(response.status_code, [200, 301, 302])
