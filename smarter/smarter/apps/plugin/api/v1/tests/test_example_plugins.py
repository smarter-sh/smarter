# pylint: disable=wrong-import-position
"""Test API end points."""

from rest_framework.test import APIClient

# our stuff
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.plugin.models import PluginMeta
from smarter.apps.plugin.utils import add_example_plugins


class TestPluginUrls(TestAccountMixin):
    """Test Account API end points."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        add_example_plugins(user_profile=self.user_profile)
        self.client = APIClient()
        self.client.force_login(self.admin_user)

    def test_account_users_add_plugins_view(self):
        """test that we can add example plugins using the api end point."""
        response = self.client.post("/api/v1/plugins/add-example-plugins/" + str(self.admin_user.id) + "/")

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
