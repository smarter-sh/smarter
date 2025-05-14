# pylint: disable=wrong-import-position
"""Test Account payment methods."""

from django.contrib.auth import authenticate
from django.test import Client
from django.urls import reverse

# our stuff
from ..models import PaymentMethod
from .mixins import TestAccountMixin


# pylint: disable=too-many-instance-attributes
class TestPaymentMethods(TestAccountMixin):
    """Test Account Payment Methods."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.base_url = reverse("account_billing_payment_methods")

        self.username = self.non_admin_user.username
        self.password = "12345"
        self.authenticated_user = authenticate(username=self.username, password=self.password)
        self.assertIsNotNone(self.authenticated_user)
        self.payment_method = self.create_payment_method()

    def create_payment_method(self):
        """Create a payment method."""
        return PaymentMethod.objects.create(
            account=self.account,
            name=self.name,
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
            name=self.name,
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
            name=self.name,
            stripe_id="1234567890",
            card_type="visa",
            card_last_4="1234",
            card_exp_month="12",
            card_exp_year="2024",
            is_default=True,
        )
        payment_method.name = self.name + "_updated"
        payment_method.save()

        self.assertEqual(payment_method.name, "Updated Payment Method")
        payment_method.delete()

    def test_payment_methods_view(self):
        """Test that we can get the payment methods view."""
        client = Client()
        client.force_login(self.admin_user)

        response = client.get(self.base_url)
        self.assertEqual(response.status_code, 200)
