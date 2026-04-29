# pylint: disable=wrong-import-position
"""Test Batch user creation for API end point."""

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
from smarter.apps.account.models import Account, User, UserProfile
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.api.const import namespace as api_namespace
from smarter.apps.api.v1.const import namespace as account_api_v1_namespace
from smarter.common.helpers.console_helpers import formatted_json
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

namespace = ":".join([api_namespace, account_api_v1_namespace, account_namespace])
HERE = os.path.abspath(os.path.dirname(__file__))

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING, SmarterWaffleSwitches.PLUGIN_LOGGING]
)


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
        self.url = reverse(namespace + ":" + Namespace.batch_create_users)
        logger.debug("Created test batch account with account number: %s", self.batch_account.account_number)

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
        logger.debug("Testing batch user creation with url: %s and data: %s", self.url, formatted_json(self.batch_data))
        response = self.client.post(self.url, data=self.batch_data, content_type="application/json")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertIsInstance(response.json(), dict)

        logger.debug("response: %s", formatted_json(response.json()))

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

    def test_get_not_allowed(self):
        """Test GET method is not allowed."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertIn("GET method is not allowed", response.content.decode())

    def test_patch_not_allowed(self):
        """Test PATCH method is not allowed."""
        response = self.client.patch(self.url, data={"foo": "bar"}, content_type="application/json")
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertIn("PATCH method is not allowed", response.content.decode())

    def test_delete_not_allowed(self):
        """Test DELETE method is not allowed."""
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertIn("DELETE method is not allowed", response.content.decode())

    def test_post_missing_body(self):
        """Test POST with missing body returns 400."""
        response = self.client.post(self.url, data=None, content_type="application/json")
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertIn("Request body is required", response.content.decode())

    def test_post_invalid_body(self):
        """Test POST with invalid body returns 400."""
        # Missing required fields
        invalid_data = {"foo": "bar"}
        response = self.client.post(self.url, data=invalid_data, content_type="application/json")
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertIn("Invalid request data", response.content.decode())

    def test_post_admin_user(self):
        """Test POST with is_admin True creates admin user."""
        admin_user = self.batch_model.users[0].model_copy()
        admin_user.is_admin = True
        batch_data = {"account_number": self.batch_model.account_number, "users": [admin_user.model_dump()]}
        response = self.client.post(self.url, data=batch_data, content_type="application/json")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        resp_json = response.json()
        self.assertEqual(len(resp_json["created_users"]), 1)
        created = resp_json["created_users"][0]
        self.assertEqual(created["status"], "success")
        # Optionally, check is_staff or is_superuser if your model supports it
        user_obj = User.objects.get(username=admin_user.username)
        self.assertTrue(user_obj.is_staff or user_obj.is_superuser)
