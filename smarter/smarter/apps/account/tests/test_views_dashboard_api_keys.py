# -*- coding: utf-8 -*-
# pylint: disable=wrong-import-position
"""Test API Keys."""

import json

# python stuff
import os
import unittest
from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.test import RequestFactory

# our stuff
from smarter.apps.account.models import Account, APIKey, UserProfile
from smarter.apps.account.views.dashboard.api_keys import APIKeyView


User = get_user_model()


class TestAPIKeys(unittest.TestCase):
    """Test API Keys"""

    def setUp(self):
        """Set up test fixtures."""
        self.base_url = "/account/dashboard/api-keys/"
        self.username = "testuser_" + os.urandom(4).hex()
        self.password = "12345"

        self.user = User.objects.create(
            username=self.username, password=self.password, is_staff=True, is_active=True, is_superuser=True
        )
        self.account = Account.objects.create(
            company_name="Test Company",
            phone_number="1234567890",
            address1="123 Test St",
            address2="Apt 1",
            city="Test City",
            state="TX",
            postal_code="12345",
        )

        self.user_profile = UserProfile.objects.create(
            user=self.user,
            account=self.account,
        )

    def tearDown(self):
        """Clean up test fixtures."""
        self.user_profile.delete()
        self.user.delete()
        self.account.delete()

    # pylint: disable=too-many-locals
    def test_api_key(self):
        """Test that we can create, update, delete an api key."""
        url = self.base_url + "new/"
        factory = RequestFactory()

        # test that we can create an api key
        data = {
            "description": "TEST KEY",
            "is_active": True,
        }
        request = factory.post(url, data=data)
        request.user = self.user

        response = APIKeyView.as_view()(request)
        response_json = json.loads(response.content)

        key_id = response_json.get("key_id")
        self.assertEqual(response.status_code, HTTPStatus.CREATED)

        # test that we can activate an api key
        factory = RequestFactory()
        data = {"action": "activate"}
        request_activate = factory.post(url, data=JsonResponse(data).content, content_type="application/json")
        request_activate.user = self.user
        response_activate = APIKeyView.as_view()(request_activate, key_id=key_id)
        self.assertEqual(response_activate.status_code, 200)

        activated_api_key = APIKey.objects.get(key_id=key_id)
        self.assertTrue(activated_api_key.is_active)

        # test that we can deactivate an api key
        factory = RequestFactory()
        data = {"action": "deactivate"}
        request_deactivate = factory.post(url, data=JsonResponse(data).content, content_type="application/json")
        request_deactivate.user = self.user
        response_deactivate = APIKeyView.as_view()(request_deactivate, key_id=key_id)
        self.assertEqual(response_deactivate.status_code, 200)

        deactivated_api_key = APIKey.objects.get(key_id=key_id)
        self.assertFalse(deactivated_api_key.is_active)

        # test that we can delete an api key
        factory = RequestFactory()
        request_delete = factory.delete(url)
        request_delete.user = self.user
        response_delete = APIKeyView.as_view()(request_delete, key_id=key_id)
        self.assertEqual(response_delete.status_code, 200)
