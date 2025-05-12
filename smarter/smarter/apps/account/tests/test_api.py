# pylint: disable=wrong-import-position
"""Test API end points."""

from http import HTTPStatus

from django.test import Client
from django.urls import reverse

# our stuff
from ..models import PaymentMethod
from .mixins import TestAccountMixin


class TestUrls(TestAccountMixin):
    """Test Account API end points."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
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
        self.client.force_login(self.admin_user)

    def tearDown(self):
        super().tearDown()

        if self.client:
            self.client.logout()

        self.client = None
        try:
            self.payment_method.delete()

        # pylint: disable=W0718
        except Exception:
            pass

    def test_account_view(self):
        """test that we can see the account view and that it matches the account data."""
        response = self.client.get(reverse("account_list_view"))

        redirect_url = response.get("Location")
        msg = response.content.decode("utf-8") if redirect_url is None else redirect_url
        self.assertEqual(response.status_code, HTTPStatus.OK, msg=msg)

        json_data = response.json()
        if isinstance(json_data, list):
            json_data = json_data[-1]
        self.assertEqual(json_data.get("company_name"), self.account.company_name)
        self.assertEqual(json_data.get("account_number"), self.account.account_number)

    def test_accounts_index_view(self):
        """test that we can see an account from inside the list view and that it matches the account data."""
        response = self.client.get(reverse("account_view", args=[str(self.account.id)]))

        redirect_url = response.get("Location")
        msg = response.content.decode("utf-8") if redirect_url is None else redirect_url
        self.assertEqual(response.status_code, HTTPStatus.OK, msg=msg)

        json_data = response.json()
        self.assertIsInstance(json_data, dict)
        self.assertEqual(json_data.get("company_name"), self.account.company_name)
        self.assertEqual(json_data.get("account_number"), self.account.account_number)

    def test_account_users_view(self):
        """test that we can see users associated with an account and that one of these matches the account data."""
        response = self.client.get(reverse("account_users_list_view"))

        redirect_url = response.get("Location")
        msg = response.content.decode("utf-8") if redirect_url is None else redirect_url
        self.assertEqual(response.status_code, HTTPStatus.OK, msg=msg)

        json_data = response.json()
        self.assertIsInstance(json_data, list)
        for user in json_data:
            if user.get("username") == self.admin_user.username:
                self.assertEqual(user.get("email"), self.admin_user.email)
                break

    def test_account_users_index_view(self):
        """test that we can see an account from inside the list view and that it matches the account data."""
        response = self.client.get(reverse("account_user_view", args=[str(self.admin_user.id)]))

        redirect_url = response.get("Location")
        msg = response.content.decode("utf-8") if redirect_url is None else redirect_url
        self.assertEqual(response.status_code, HTTPStatus.OK, msg=msg)

        json_data = response.json()
        self.assertIsInstance(json_data, dict)
        self.assertEqual(json_data.get("email"), self.admin_user.email)
        self.assertEqual(json_data.get("username"), self.admin_user.username)

    def test_account_payment_methods(self):
        """test that we can see the payment methods associated with an account."""
        response = self.client.get(reverse("account_payment_methods_list_view"))

        redirect_url = response.get("Location")
        msg = response.content.decode("utf-8") if redirect_url is None else redirect_url
        self.assertEqual(response.status_code, HTTPStatus.OK, msg=msg)

        json_data = response.json()
        self.assertIsInstance(json_data, list)
        for payment_method in json_data:
            if payment_method.get("name") == self.payment_method.name:
                self.assertEqual(payment_method.get("card_type"), self.payment_method.card_type)
                break
            self.fail("payment method not found in list")

    def test_account_payment_methods_index(self):
        """test that we can see the payment methods associated with an account."""
        response = self.client.get(reverse("account_payment_method_view", args=[str(self.payment_method.id)]))

        redirect_url = response.get("Location")
        msg = response.content.decode("utf-8") if redirect_url is None else redirect_url
        self.assertEqual(response.status_code, HTTPStatus.OK, msg=msg)

        json_data = response.json()
        self.assertTrue(type(json_data) in (list, dict))

        self.assertEqual(json_data.get("name"), self.payment_method.name)
        self.assertEqual(json_data.get("card_type"), self.payment_method.card_type)
        self.assertEqual(json_data.get("card_last_4"), self.payment_method.card_last_4)
        self.assertEqual(json_data.get("card_exp_month"), self.payment_method.card_exp_month)
        self.assertEqual(json_data.get("card_exp_year"), self.payment_method.card_exp_year)
        self.assertEqual(json_data.get("is_default"), self.payment_method.is_default)
