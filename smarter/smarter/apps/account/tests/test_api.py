# pylint: disable=wrong-import-position
"""Test API end points."""

import logging
from http import HTTPStatus

from django.test import Client
from django.urls import reverse

from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

# our stuff
from .mixins import TestAccountMixin


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.ACCOUNT_LOGGING) or waffle.switch_is_active(
        SmarterWaffleSwitches.PLUGIN_LOGGING
    )


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class TestUrls(TestAccountMixin):
    """Test Account API end points."""

    namespace = "account:api:v1:"

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.client = Client()
        self.client.force_login(self.admin_user)

    def tearDown(self):

        if self.client:
            self.client.logout()

        self.client = None

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
