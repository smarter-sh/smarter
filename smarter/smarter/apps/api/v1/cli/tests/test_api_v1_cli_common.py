# pylint: disable=wrong-import-position
"""Test api/v1/cli common endpoints."""

import hashlib
import json
import os
import random
import unittest
from http import HTTPStatus

from django.test import Client
from django.urls import reverse

from smarter.apps.account.models import Account, SmarterAuthToken, UserProfile
from smarter.common.const import PYTHON_ROOT
from smarter.lib.django.user import User


class TestApiV1CliCommon(unittest.TestCase):
    """Test api/v1/cli common endpoints."""

    def setUp(self):
        self.name = "CliTestPlugin"
        hash_suffix = "_" + hashlib.sha256(str(random.getrandbits(256)).encode("utf-8")).hexdigest()

        self.account = Account.objects.create(
            company_name="TestCompany" + hash_suffix,
            phone_number="1234567890",
            address1="123 Test St",
            address2="Apt 1",
            city="Test City",
            state="TX",
            postal_code="12345",
        )

        username = "testuser" + hash_suffix
        self.user = User.objects.create_user(username=username, password="12345", is_staff=True, is_superuser=True)
        self.user_profile = UserProfile.objects.create(user=self.user, account=self.account)

        self.path = os.path.join(PYTHON_ROOT, "smarter", "apps", "api", "v1", "cli", "tests", "data")
        self.good_manifest_path = os.path.join(self.path, "good-plugin-manifest.yaml")

        with open(self.good_manifest_path, encoding="utf-8") as file:
            self.good_manifest_text = file.read()

        self.token_record, self.token_key = SmarterAuthToken.objects.create(
            account=self.account,
            user=self.user,
            description="testToken" + hash_suffix,
        )

    def tearDown(self):
        try:
            self.user_profile.delete()
        except UserProfile.DoesNotExist:
            pass
        try:
            self.user.delete()
        except User.DoesNotExist:
            pass
        try:
            self.account.delete()
        except Account.DoesNotExist:
            pass
        try:
            self.token_record.delete()
        except SmarterAuthToken.DoesNotExist:
            pass

    def get_response(self, path, manifest: str = None):
        """
        Prepare and get a response from an api/v1/cli endpoint.
        """
        client = Client()
        client.force_login(self.user)

        headers = {"Authorization": f"Token {self.token_key}"}
        response = client.post(path=path, data=manifest, content_type="application/json", extra=headers)

        response_content = response.content.decode("utf-8")
        response_json = json.loads(response_content)
        return response_json, response.status_code

    def test_valid_manifest(self):
        """Test that we get OK response when passing a valid manifest"""

        path = reverse("api_v1_cli_status_view")
        response, status = self.get_response(path)
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)
        self.assertIsInstance(response["infrastructure"], dict)
        self.assertIsInstance(response["infrastructure"]["aws"], dict)

        path = reverse("api_v1_cli_whoami_view")
        response, status = self.get_response(path)
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)
        self.assertIsInstance(response["user"], dict)
        self.assertEqual(response["user"]["username"], self.user.username)
        self.assertIsInstance(response["account"], dict)
        self.assertEqual(response["account"]["company_name"], self.account.company_name)
