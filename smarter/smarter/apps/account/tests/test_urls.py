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
        self.client.login(username="testuser", password="12345")

    def tearDown(self):
        """Clean up test fixtures."""
        self.user.delete()

    def test_account_view(self):
        response = self.client.get("/account/")

        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertEqual(json_data.get("company_name"), self.account.company_name)
        self.assertEqual(json_data.get("account_number"), self.account.account_number)
