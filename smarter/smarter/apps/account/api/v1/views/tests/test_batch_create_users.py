# pylint: disable=wrong-import-position
"""Test Batch user creation for API end point."""

import logging
import os
from http import HTTPStatus

from django.test import Client
from django.urls import reverse

from smarter.apps.account.api.v1.urls import Namespace
from smarter.apps.account.api.v1.views.batch_create_users import (
    BatchCreateUsersResponseModel,
    BatchModel,
)
from smarter.apps.account.const import namespace as account_namespace

# our stuff
from smarter.apps.account.models import Account, User, UserProfile
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.api.const import namespace as api_namespace
from smarter.apps.api.v1.const import namespace as account_api_v1_namespace
from smarter.common.helpers.console_helpers import formatted_json
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

namespace = ":".join([api_namespace, account_api_v1_namespace, account_namespace])
HERE = os.path.abspath(os.path.dirname(__file__))


# pylint: disable=W0613
def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.ACCOUNT_LOGGING) or waffle.switch_is_active(
        SmarterWaffleSwitches.PLUGIN_LOGGING
    )


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class TestUrls(TestAccountMixin):
    """Test Batch user creation API end point."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.client = Client()
        self.client.force_login(self.admin_user)
        self.batch_data = self.get_readonly_json_file(os.path.join(HERE, "data/batch_users.json"))
        self.batch_model = BatchModel(**self.batch_data)  # type: ignore
        self.batch_account = Account.objects.create(account_number=self.batch_model.account_number)
        logger.debug(f"Created test batch account with account number: {self.batch_account.account_number}")

    def tearDown(self):
        """Tear down test fixtures."""
        for user_profile in UserProfile.objects.filter(account=self.batch_account):
            user = user_profile.user
            user_profile.delete()
            user.delete()
        self.batch_account.delete()
        logger.debug("Deleted test batch account and associated users and user_profile records")
        super().tearDown()

    def test_batch_create_users(self):
        """Test batch user creation."""
        url = reverse(namespace + ":" + Namespace.batch_create_users)
        response = self.client.post(url, data=self.batch_data, content_type="application/json")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertIsInstance(response.json(), dict)

        logger.debug(f"response: {formatted_json(response.json())}")

        batch_response_model = BatchCreateUsersResponseModel(**response.json())

        # test that all users were created.
        for user in self.batch_model.users:
            try:
                user_orm = User.objects.get(username=user.username)
                user_profile = UserProfile.objects.get(user=user_orm)
                self.assertEqual(user_profile.account.account_number, self.batch_model.account_number)
            except (User.DoesNotExist, UserProfile.DoesNotExist):
                self.fail(f"User {user.username} should exist in the database for testing batch user creation.")

        # test that the http response is correct.
        self.assertEqual(len(batch_response_model.created_users), len(self.batch_model.users))
        for created_user in batch_response_model.created_users:
            self.assertEqual(created_user.status, "success")
            self.assertEqual(created_user.account_number, self.batch_model.account_number)
            self.assertIsNone(created_user.error)
