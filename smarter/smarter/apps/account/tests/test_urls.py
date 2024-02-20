# -*- coding: utf-8 -*-
# pylint: disable=wrong-import-position
"""Test API end points."""

# python stuff
import os
import unittest

from django.contrib.auth.models import User
from django.test import Client

# our stuff
from smarter.apps.account.models import Account, PaymentMethod, UserProfile
from smarter.apps.account.tests.test_setup import PROJECT_ROOT
from smarter.apps.plugin.utils import add_example_plugins


PLUGINS_PATH = os.path.join(PROJECT_ROOT, "smarter", "app", "plugins", "data", "sample-plugins")


class TestUrls(unittest.TestCase):
    """Test OpenAI Function Calling hook for refers_to."""

    user: User

    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create(
            username="testuser", password="12345", is_staff=True, is_active=True, is_superuser=True
        )
        self.account = Account.objects.create(
            company_name="Test Company",
            phone_number="1234567890",
            address="123 Test St",
        )
        self.user_profile = UserProfile.objects.create(
            user=self.user,
            account=self.account,
        )
        self.payment_method = PaymentMethod.objects.create(
            account=self.account,
            name="Test Payment Method",
            stripe_id="1234567890",
            card_type="visa",
            card_last_4="1234",
            card_exp_month="12",
            card_exp_year="2024",
            is_default=True,
        )
        add_example_plugins(user_profile=self.user_profile)
        self.client = Client()
        # self.client.login(username="testuser", password="12345")
        self.client.force_login(self.user)

    def tearDown(self):
        """Clean up test fixtures."""
        self.user.delete()
        self.account.delete()
        self.user_profile.delete()

    def test_account_view(self):
        """test that we can see the account view and that it matches the account data."""
        response = self.client.get("/v0/account/")

        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertEqual(json_data.get("company_name"), self.account.company_name)
        self.assertEqual(json_data.get("account_number"), self.account.account_number)

    def test_accounts_view(self):
        """test that we can see the accounts view and that it matches the account data."""
        response = self.client.get("/v0/accounts/")

        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertIsInstance(json_data, list)

        # there should be at least one account
        self.assertGreaterEqual(len(json_data), 1)

        # iterate the list and try to match a dict to the company_name and account_number
        for account in json_data:
            if account.get("company_name") == self.account.company_name:
                self.assertEqual(account.get("account_number"), self.account.account_number)
                break
        else:
            self.fail("account not found in list")

    def test_accounts_index_view(self):
        """test that we can see an account from inside the list view and that it matches the account data."""
        response = self.client.get("/v0/accounts/" + str(self.account.id) + "/")

        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertIsInstance(json_data, dict)
        self.assertEqual(json_data.get("company_name"), self.account.company_name)
        self.assertEqual(json_data.get("account_number"), self.account.account_number)

    def test_account_users_view(self):
        """test that we can see an account from inside the list view and that it matches the account data."""
        response = self.client.get("/v0/account/users/")

        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertIsInstance(json_data, list)
        for user in json_data:
            if user.get("username") == self.user.username:
                self.assertEqual(user.get("email"), self.user.email)
                break

    def test_account_users_index_view(self):
        """test that we can see an account from inside the list view and that it matches the account data."""
        response = self.client.get("/v0/account/users/" + str(self.user.id) + "/")

        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertIsInstance(json_data, dict)
        self.assertEqual(json_data.get("email"), self.user.email)
        self.assertEqual(json_data.get("username"), self.user.username)
