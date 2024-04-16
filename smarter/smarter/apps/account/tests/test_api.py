# pylint: disable=wrong-import-position
"""Test API end points."""

# python stuff
import os
import unittest

from django.test import Client

# our stuff
from smarter.lib.django.user import User, UserType

from ..models import Account, PaymentMethod, UserProfile


class TestUrls(unittest.TestCase):
    """Test Account API end points."""

    user: UserType

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
        self.client = Client()
        self.client.force_login(self.user)

    def tearDown(self):
        """Clean up test fixtures."""
        self.user.delete()
        self.account.delete()
        self.user_profile.delete()

    def test_account_view(self):
        """test that we can see the account view and that it matches the account data."""
        response = self.client.get("/api/v0/accounts/")

        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        if isinstance(json_data, list):
            json_data = json_data[-1]
        self.assertEqual(json_data.get("company_name"), self.account.company_name)
        self.assertEqual(json_data.get("account_number"), self.account.account_number)

    def test_accounts_view(self):
        """test that we can see the accounts view and that it matches the account data."""
        response = self.client.get("/api/v0/accounts/")

        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertIn(type(json_data), (list, dict))

        # there should be at least one account
        self.assertGreaterEqual(len(json_data), 1)

        if isinstance(json_data, dict):
            self.assertEqual(json_data.get("account_number"), self.account.account_number)

        # iterate the list and try to match a dict to the company_name and account_number
        if isinstance(json_data, list):
            for account in json_data:
                if account.get("account_number") == self.account.account_number:
                    self.assertEqual(account.get("company_name"), self.account.company_name)
                    break
            else:
                self.fail("account not found in list")

    def test_accounts_index_view(self):
        """test that we can see an account from inside the list view and that it matches the account data."""
        response = self.client.get("/api/v0/accounts/" + str(self.account.id) + "/")

        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertIsInstance(json_data, dict)
        self.assertEqual(json_data.get("company_name"), self.account.company_name)
        self.assertEqual(json_data.get("account_number"), self.account.account_number)

    def test_account_users_view(self):
        """test that we can see users associated with an account and that one of these matches the account data."""
        response = self.client.get("/api/v0/accounts/users/")

        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertIsInstance(json_data, list)
        for user in json_data:
            if user.get("username") == self.user.username:
                self.assertEqual(user.get("email"), self.user.email)
                break

    def test_account_users_index_view(self):
        """test that we can see an account from inside the list view and that it matches the account data."""
        response = self.client.get("/api/v0/accounts/users/" + str(self.user.id) + "/")

        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertIsInstance(json_data, dict)
        self.assertEqual(json_data.get("email"), self.user.email)
        self.assertEqual(json_data.get("username"), self.user.username)

    def test_account_payment_methods(self):
        """test that we can see the payment methods associated with an account."""
        response = self.client.get("/api/v0/accounts/payment-methods/")

        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertIsInstance(json_data, list)
        for payment_method in json_data:
            if payment_method.get("name") == self.payment_method.name:
                self.assertEqual(payment_method.get("card_type"), self.payment_method.card_type)
                break
            self.fail("payment method not found in list")

    def test_account_payment_methods_index(self):
        """test that we can see the payment methods associated with an account."""
        response = self.client.get("/api/v0/accounts/payment-methods/" + str(self.payment_method.id) + "/")

        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertTrue(type(json_data) in (list, dict))

        self.assertEqual(json_data.get("name"), self.payment_method.name)
        self.assertEqual(json_data.get("card_type"), self.payment_method.card_type)
        self.assertEqual(json_data.get("card_last_4"), self.payment_method.card_last_4)
        self.assertEqual(json_data.get("card_exp_month"), self.payment_method.card_exp_month)
        self.assertEqual(json_data.get("card_exp_year"), self.payment_method.card_exp_year)
        self.assertEqual(json_data.get("is_default"), self.payment_method.is_default)
