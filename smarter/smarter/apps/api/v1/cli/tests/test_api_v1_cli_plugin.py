# pylint: disable=wrong-import-position
"""Test api/v1/cli endpoints on the Plugin model."""

import hashlib
import json
import os
import random
import unittest
from http import HTTPStatus

from django.test import Client
from django.urls import reverse

from smarter.apps.account.models import Account, SmarterAuthToken, UserProfile
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.plugin.models import PluginMeta
from smarter.common.const import PYTHON_ROOT
from smarter.lib.django.user import User
from smarter.lib.manifest.enum import SAMApiVersions


class TestApiV1CliPlugin(unittest.TestCase):
    """Test api/v1/cli endpoints on the Plugin model."""

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

    def get_response(self, path, manifest: str = None) -> tuple[dict, int]:
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

        path = reverse("api_v1_cli_apply_view", kwargs={})
        response, status = self.get_response(path, manifest=self.good_manifest_text)

        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)
        self.assertEqual(response["message"], "Plugin CliTestPlugin applied successfully")

        path = reverse("api_v1_cli_deploy_view", kwargs={"kind": "plugin", "name": self.name})
        response, status = self.get_response(path)
        self.assertEqual(status, HTTPStatus.NOT_IMPLEMENTED)
        self.assertEqual(response["message"], "operation not implemented for Plugin resources")

        path = reverse("api_v1_cli_describe_view", kwargs={"kind": "plugin", "name": self.name})
        response, status = self.get_response(path)
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)
        self.assertEqual(response["apiVersion"], SAMApiVersions.V1.value)
        self.assertEqual(response["kind"], SAMKinds.PLUGIN.value)
        self.assertIsInstance(response.get("metadata", None), dict)
        self.assertEqual(response.get("metadata", {}).get("name", None), self.name)

        path = reverse("api_v1_cli_logs_kind_name_view", kwargs={"kind": "plugin", "name": self.name})
        response, status = self.get_response(path)
        self.assertEqual(status, HTTPStatus.NOT_IMPLEMENTED)
        self.assertEqual(response["message"], "operation not implemented for Plugin resources")

        path = reverse("api_v1_cli_get_view", kwargs={"kind": "plugins"})
        response, status = self.get_response(path)
        self.assertIsInstance(response["items"], list)
        self.assertEqual(response["kind"], SAMKinds.PLUGIN.value)
        self.assertEqual(response["apiVersion"], SAMApiVersions.V1.value)

        path = reverse("api_v1_cli_manifest_view", kwargs={"kind": "plugin"})
        response, status = self.get_response(path)
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)
        self.assertEqual(response["filepath"], "https://cdn.localhost:8000/cli/example-manifests/plugin.yaml")

        path = reverse("api_v1_cli_delete_view", kwargs={"kind": "plugin", "name": self.name})
        response, status = self.get_response(path)
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)
        self.assertEqual(response["message"], "Plugin CliTestPlugin deleted successfully")
        with self.assertRaises(PluginMeta.DoesNotExist):
            PluginMeta.objects.get(name=self.name, account=self.account)
