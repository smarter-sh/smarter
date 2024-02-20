# -*- coding: utf-8 -*-
# pylint: disable=wrong-import-position
"""Test User."""

# python stuff
import os
import unittest

from django.contrib.auth.models import User

# our stuff
from smarter.apps.account.models import Account, UserProfile
from smarter.apps.account.tests.test_setup import PROJECT_ROOT
from smarter.apps.plugin.plugin import Plugins
from smarter.apps.plugin.utils import add_example_plugins


PLUGINS_PATH = os.path.join(PROJECT_ROOT, "smarter", "apps", "plugin", "data", "sample-plugins")


class TestUser(unittest.TestCase):
    """Test OpenAI Function Calling hook for refers_to."""

    user: User

    def setUp(self):
        """Set up test fixtures."""
        self.user, _ = User.objects.get_or_create(username="testuser", password="12345")

    def tearDown(self):
        """Clean up test fixtures."""
        self.user.delete()

    def test_create(self):
        """Test that we can create an account."""

        def count_plugins() -> int:
            num_plugins = 0
            for file in os.listdir(PLUGINS_PATH):
                if file.endswith(".yaml"):
                    num_plugins += 1
            return num_plugins

        num_plugins = count_plugins()

        account = Account.objects.create(
            company_name="Test Company",
            phone_number="1234567890",
            address="123 Test St",
        )

        profile = UserProfile.objects.create(
            user=self.user,
            account=account,
        )

        self.assertEqual(profile.account, account)
        self.assertEqual(profile.user, self.user)

        add_example_plugins(user_profile=profile)

        plugins = Plugins(user=self.user)
        self.assertEqual(len(plugins.plugins), num_plugins)

        for plugin in plugins.plugins:
            plugin.delete()

        profile.delete()
        account.delete()

    def test_update(self):
        """Test that we can update an account."""

        account = Account.objects.create(
            company_name="Test Company",
            phone_number="1234567890",
            address="123 Test St",
        )

        account_to_update = Account.objects.get(id=account.id)
        account_to_update.company_name = "New Company"
        account_to_update.save()

        self.assertEqual(account_to_update.company_name, "New Company")
        self.assertEqual(account_to_update.phone_number, "1234567890")
        self.assertEqual(account_to_update.address, "123 Test St")
        self.assertEqual(account_to_update.account_number, account.account_number)

        account.delete()

    def test_account_with_profile(self):
        """Test that we can create an account and associate a user_profile."""
