# pylint: disable=wrong-import-position
"""Test Account payment methods."""

import os

# python stuff
import unittest

from django.contrib.auth import authenticate
from django.test import Client
from django.urls import reverse

# our stuff
from smarter.lib.django.user import User

from ..models import Account, PaymentMethod, UserProfile


# pylint: disable=too-many-instance-attributes
class TestPaymentMethods(unittest.TestCase):
    """Test Account Payment Methods."""

    def setUp(self):
        """Set up test fixtures."""
        self.base_url = reverse("account_billing_payment_methods")

        self.username = "testuser_" + os.urandom(4).hex()
        self.password = "12345"
        self.user = User.objects.create_user(username=self.username, is_staff=True, is_active=True, is_superuser=True)
        self.user.set_password(self.password)
        self.user.save()
        self.authenticated_user = authenticate(username=self.username, password=self.password)
        self.assertIsNotNone(self.authenticated_user)

        self.account = Account.objects.create(
            company_name="Test Company",
            phone_number="1234567890",
            address1="123 Test St",
            address2="Apt 1",
            city="Test City",
            state="TX",
            postal_code="12345",
        )
        self.user_profile = UserProfile.objects.create(user=self.user, account=self.account)
        self.payment_method = self.create_payment_method()

    def tearDown(self):
        """Clean up test fixtures."""
        self.account.delete()

    def create_payment_method(self):
        """Create a payment method."""
        return PaymentMethod.objects.create(
            account=self.account,
            name="Test Payment Method" + os.urandom(4).hex(),
            stripe_id="1234567890",
            card_type="visa",
            card_last_4="1234",
            card_exp_month="12",
            card_exp_year="2024",
            is_default=True,
        )

    def test_create(self):
        """Test that we can create an account."""
        payment_method = PaymentMethod.objects.create(
            account=self.account,
            name="Test Payment Method",
            stripe_id="1234567890",
            card_type="visa",
            card_last_4="1234",
            card_exp_month="12",
            card_exp_year="2024",
            is_default=True,
        )

        payment_method.delete()

    def test_update(self):
        """Test that we can update an account."""
        payment_method = PaymentMethod.objects.create(
            account=self.account,
            name="Test Payment Method",
            stripe_id="1234567890",
            card_type="visa",
            card_last_4="1234",
            card_exp_month="12",
            card_exp_year="2024",
            is_default=True,
        )
        payment_method.name = "Updated Payment Method"
        payment_method.save()

        self.assertEqual(payment_method.name, "Updated Payment Method")
        payment_method.delete()

    def test_payment_methods_view(self):
        """Test that we can get the payment methods view."""
        client = Client()
        client.force_login(self.user)

        response = client.get(self.base_url)
        self.assertEqual(response.status_code, 200)
