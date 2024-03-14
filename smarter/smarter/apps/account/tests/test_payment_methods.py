# -*- coding: utf-8 -*-
# pylint: disable=wrong-import-position
"""Test Account payment methods."""

# python stuff
import unittest

# our stuff
from smarter.apps.account.models import Account, PaymentMethod


class TestPaymentMethods(unittest.TestCase):
    """Test Account Payment Methods."""

    def setUp(self):
        """Set up test fixtures."""
        self.account = Account.objects.create(
            company_name="Test Company",
            phone_number="1234567890",
            address1="123 Test St",
            address2="Apt 1",
            city="Test City",
            state="TX",
            postal_code="12345",
        )

    def tearDown(self):
        """Clean up test fixtures."""
        self.account.delete()

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
