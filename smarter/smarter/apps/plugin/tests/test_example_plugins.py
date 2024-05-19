# pylint: disable=wrong-import-position
"""Test API end points."""

# python stuff
import unittest

from django.test import Client

# our stuff
from smarter.apps.account.tests.factories import admin_user_factory, admin_user_teardown
from smarter.lib.django.user import UserType

from ..models import PluginMeta
from ..utils import add_example_plugins


class TestPluginUrls(unittest.TestCase):
    """Test Account API end points."""

    user: UserType

    def setUp(self):
        """Set up test fixtures."""
        self.user, self.account, self.user_profile = admin_user_factory()
        add_example_plugins(user_profile=self.user_profile)
        self.client = Client()
        self.client.force_login(self.user)

    def tearDown(self):
        """Clean up test fixtures."""
        admin_user_teardown(self.user, self.account, self.user_profile)

    def test_account_users_add_plugins_view(self):
        """test that we can add example plugins using the api end point."""
        response = self.client.post("/api/v1/plugins/add-example-plugins/" + str(self.user.id) + "/")

        # we should have been redirected to a list of the plugins for the user
        self.assertEqual(response.status_code, 302)
        if "application/json" in response["Content-Type"]:
            json_data = response.json()
            self.assertIsInstance(json_data, dict)
            self.assertGreaterEqual(len(json_data), 1)

        plugins = PluginMeta.objects.filter(account=self.account)
        self.assertGreaterEqual(len(plugins), 1)

        for plugin in plugins:
            plugin.delete()
