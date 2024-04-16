# pylint: disable=wrong-import-position
"""Test API end points."""

# python stuff
import os
import unittest

from django.test import Client

# our stuff
from smarter.apps.account.models import Account, UserProfile
from smarter.lib.django.user import User

from ..plugin import Plugins
from ..utils import add_example_plugins


class TestPluginUrls(unittest.TestCase):
    """Test Account API end points."""

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
        )
        self.user_profile = UserProfile.objects.create(
            user=self.user,
            account=self.account,
            is_test=True,
        )
        add_example_plugins(user_profile=self.user_profile)
        self.client = Client()
        self.client.force_login(self.user)

    def tearDown(self):
        """Clean up test fixtures."""
        self.user.delete()
        self.account.delete()
        self.user_profile.delete()

    def test_account_users_add_plugins_view(self):
        """test that we can add example plugins using the api end point."""
        response = self.client.post("/api/v0/plugins/add-example-plugins/" + str(self.user.id) + "/")

        # we should have been redirected to a list of the plugins for the user
        self.assertEqual(response.status_code, 302)
        if "application/json" in response["Content-Type"]:
            json_data = response.json()
            self.assertIsInstance(json_data, dict)
            self.assertGreaterEqual(len(json_data), 1)

        plugins = Plugins(user=self.user).plugins
        self.assertGreaterEqual(len(plugins), 1)

        for plugin in plugins:
            plugin.delete()
