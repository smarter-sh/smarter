# pylint: disable=wrong-import-position
"""Test API end points."""

from http import HTTPStatus
from logging import getLogger

from django.test import Client
from django.urls import reverse

# our stuff
from ..models import PaymentMethod
from .mixins import TestAccountMixin


logger = getLogger(__name__)


class TestUrls(TestAccountMixin):
    """Test Account API end points."""

    namespace = "account:api:v1:"

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

        if self.client:
            self.client.logout()

        self.client = None
        try:
            self.payment_method.delete()

        # pylint: disable=W0718
        except Exception:
            pass

        super().tearDown()

    def test_account_view(self):
        """test that we can see the account view and that it matches the account data."""
        response = self.client.get(reverse(self.namespace + "account_list_view"))

        redirect_url = response.get("Location")
        msg = response.content.decode("utf-8") if redirect_url is None else redirect_url
        self.assertEqual(response.status_code, HTTPStatus.OK, msg=msg)

        json_data = response.json()
        logger.info("test_account_view json_data: %s", json_data)
        if isinstance(json_data, list):
            json_data = json_data[-1]
        self.assertEqual(json_data.get("companyName"), self.account.company_name)
        self.assertEqual(json_data.get("accountNumber"), self.account.account_number)

    def test_accounts_index_view(self):
        """test that we can see an account from inside the list view and that it matches the account data."""
        response = self.client.get(reverse(self.namespace + "account_view", args=[str(self.account.id)]))

        redirect_url = response.get("Location")
        msg = response.content.decode("utf-8") if redirect_url is None else redirect_url
        self.assertEqual(response.status_code, HTTPStatus.OK, msg=msg)

        json_data = response.json()
        logger.info("test_accounts_index_view json_data: %s", json_data)
        output = {
            "id": 5437,
            "createdAt": "2025-05-23T14:56:21.046401Z",
            "updatedAt": "2025-05-23T14:56:21.046424Z",
            "accountNumber": "1137-8137-6260",
            "isDefaultAccount": False,
            "companyName": "TestAccount_AdminUser_08cd0b30b9912bac",
            "phoneNumber": "123-456-789",
            "address1": None,
            "address2": None,
            "city": None,
            "state": None,
            "postalCode": None,
            "country": "USA",
            "language": "EN",
            "timezone": None,
            "currency": "USD",
        }

        self.assertIsInstance(json_data, dict)
        self.assertEqual(json_data.get("companyName"), self.account.company_name)
        self.assertEqual(json_data.get("accountNumber"), self.account.account_number)

    def test_account_users_view(self):
        """test that we can see users associated with an account and that one of these matches the account data."""
        response = self.client.get(reverse(self.namespace + "account_users_list_view"))

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
        response = self.client.get(reverse(self.namespace + "account_user_view", args=[str(self.admin_user.id)]))

        redirect_url = response.get("Location")
        msg = response.content.decode("utf-8") if redirect_url is None else redirect_url
        self.assertEqual(response.status_code, HTTPStatus.OK, msg=msg)

        json_data = response.json()
        logger.info("test_account_users_index_view json_data: %s", json_data)
        output = {
            "id": 8315,
            "username": "testAdminUser_08cd0b30b9912bac",
            "first_name": "TestAdminFirstName_08cd0b30b9912bac",
            "last_name": "TestAdminLastName_08cd0b30b9912bac",
            "email": "test-08cd0b30b9912bac@mail.com",
            "is_staff": True,
            "is_superuser": True,
        }
        self.assertIsInstance(json_data, dict)
        self.assertEqual(json_data.get("email"), self.admin_user.email)
        self.assertEqual(json_data.get("username"), self.admin_user.username)

    def test_account_payment_methods(self):
        """test that we can see the payment methods associated with an account."""
        response = self.client.get(reverse(self.namespace + "account_payment_methods_list_view"))

        redirect_url = response.get("Location")
        msg = response.content.decode("utf-8") if redirect_url is None else redirect_url
        self.assertEqual(response.status_code, HTTPStatus.OK, msg=msg)

        json_data = response.json()
        logger.info("test_account_payment_methods json_data: %s", json_data)
        output = [
            {
                "id": 443,
                "createdAt": "2025-05-23T14:56:21.572330Z",
                "updatedAt": "2025-05-23T14:56:21.572342Z",
                "name": "Test Payment Method",
                "stripeId": "1234567890",
                "cardType": "visa",
                "cardLast4": "1234",
                "cardExpMonth": "12",
                "cardExpYear": "2024",
                "isDefault": True,
                "account": 5437,
            }
        ]

        self.assertIsInstance(json_data, list)
        for payment_method in json_data:
            if payment_method.get("name") == self.payment_method.name:
                self.assertEqual(payment_method.get("cardType"), self.payment_method.card_type)
                break
            self.fail("payment method not found in list")

    def test_account_payment_methods_index(self):
        """test that we can see the payment methods associated with an account."""
        response = self.client.get(
            reverse(self.namespace + "account_payment_method_view", args=[str(self.payment_method.id)])
        )

        redirect_url = response.get("Location")
        msg = response.content.decode("utf-8") if redirect_url is None else redirect_url
        self.assertEqual(response.status_code, HTTPStatus.OK, msg=msg)

        json_data = response.json()
        logger.info("test_account_payment_methods_index json_data: %s", json_data)
        output = {
            "id": 444,
            "createdAt": "2025-05-23T14:56:21.853593Z",
            "updatedAt": "2025-05-23T14:56:21.853610Z",
            "name": "Test Payment Method",
            "stripeId": "1234567890",
            "cardType": "visa",
            "cardLast4": "1234",
            "cardExpMonth": "12",
            "cardExpYear": "2024",
            "isDefault": True,
            "account": 5437,
        }
        self.assertTrue(type(json_data) in (list, dict))

        self.assertEqual(json_data.get("name"), self.payment_method.name)
        self.assertEqual(json_data.get("cardType"), self.payment_method.card_type)
        self.assertEqual(json_data.get("cardLast4"), self.payment_method.card_last_4)
        self.assertEqual(json_data.get("cardExpMonth"), self.payment_method.card_exp_month)
        self.assertEqual(json_data.get("cardExpYear"), self.payment_method.card_exp_year)
        self.assertEqual(json_data.get("isDefault"), self.payment_method.is_default)
