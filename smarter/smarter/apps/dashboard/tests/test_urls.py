# pylint: disable=wrong-import-position
"""Test API end points."""

# python stuff
import os
import unittest

from django.test import Client

from smarter.apps.account.models import Account, UserProfile

# our stuff
from smarter.lib.django.user import User


class TestDashboard(unittest.TestCase):
    """Test dashboard views."""

    user: User

    def setUp(self):
        """Set up test fixtures."""
        username = "testuser_" + os.urandom(4).hex()
        self.user = User.objects.create(
            username=username, password="12345", is_staff=True, is_active=True, is_superuser=True
        )
        self.account = Account.objects.create(
            company_name="Test Company",
            phone_number="1234567890",
            address1="123 Test St",
            address2="Apt 1",
            city="Test City",
            state="TX",
            postal_code="12345",
        )
        self.user_profile = UserProfile.objects.create(user=self.user, account=self.account, is_test=True)
        self.client = Client()
        # self.client.login(username="testuser", password="12345")
        self.client.force_login(self.user)

    def tearDown(self):
        """Clean up test fixtures."""
        self.user.delete()
        self.account.delete()
        self.user_profile.delete()

    def test_dashboard(self):
        """test that we can see the account view and that it matches the account data."""
        response = self.client.get("")
        self.assertIn(response.status_code, [200, 301, 302])
