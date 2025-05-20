# pylint: disable=wrong-import-position
"""Test API end points."""

from django.test import Client
from django.urls import reverse

from smarter.apps.account.tests.mixins import TestAccountMixin

from ..const import namespace


class TestDashboard(TestAccountMixin):
    """Test dashboard views."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.client = Client()
        self.client.force_login(self.non_admin_user)

    def test_dashboard(self):
        """Test dashboard root view."""
        response = self.client.get("")
        self.assertIn(response.status_code, [200, 301, 302])

    def test_account_url(self):
        """Test account url includes."""
        response = self.client.get(f"{namespace}/account/")
        self.assertIn(response.status_code, [200, 301, 302, 404])

    def test_plugins_url(self):
        """Test plugins url includes."""
        response = self.client.get(f"{namespace}/plugins/")
        self.assertIn(response.status_code, [200, 301, 302, 404])

    def test_profile_url(self):
        """Test profile url includes."""
        response = self.client.get(f"{namespace}/profile/")
        self.assertIn(response.status_code, [200, 301, 302, 404])

    def test_help_redirect(self):
        """Test help url redirects to /docs/."""
        reverse_url = reverse(f"{namespace}:help")
        response = self.client.get(reverse_url)
        self.assertIn(response.status_code, [301, 302])

    def test_support_redirect(self):
        """Test support url redirects to /docs/."""
        reverse_url = reverse(f"{namespace}:support")
        response = self.client.get(reverse_url)
        self.assertIn(response.status_code, [301, 302])

    def test_changelog(self):
        """Test changelog view."""
        reverse_url = reverse(f"{namespace}:changelog")
        response = self.client.get(reverse_url)
        self.assertIn(response.status_code, [200, 301, 302])

    def test_notifications(self):
        """Test notifications view."""
        reverse_url = reverse(f"{namespace}:notifications")
        response = self.client.get(reverse_url)
        self.assertIn(response.status_code, [200, 301, 302])
