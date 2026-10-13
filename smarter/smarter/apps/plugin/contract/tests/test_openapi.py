"""Test the plugins' REST reads against the Smarter api's OpenAPI document, and that a plugin of another account is not disclosed."""

import os
from http import HTTPStatus
from unittest.mock import patch

import yaml
from rest_framework.test import APIClient

from smarter.apps.account.tests.factories import mortal_user_factory
from smarter.apps.api.v1.contract.tests.mixins import OpenApiResponseMixin
from smarter.apps.api.v1.tests.base_class import ApiV1TestBase
from smarter.apps.plugin.models import PluginMeta

MANIFEST = os.path.join(os.path.dirname(__file__), "..", "..", "tests", "data", "static-plugin.yaml")
NAME = "test_plugin_app_static_plugin"


class TestPluginOpenApi(OpenApiResponseMixin, ApiV1TestBase):
    """The plugins' list and a plugin's manifest, against the document."""

    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_key}")
        self.addCleanup(PluginMeta.objects.filter(user_profile=self.user_profile, name__startswith=NAME).delete)
        with open(MANIFEST, encoding="utf-8") as f:
            manifest = yaml.safe_load(f)
        response = self.client.post("/api/v1/plugins/", data=manifest, format="json")
        self.assertEqual(response.status_code, HTTPStatus.FOUND, response.content[:500])
        self.plugin = PluginMeta.objects.get(user_profile=self.user_profile, name=NAME)

    def test_list_and_retrieve(self):
        response = self.client.get("/api/v1/plugins/")
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:500])
        self.assertValidResponse("/plugins/", "get", response.json())
        with patch("smarter.lib.django.waffle.switch_is_active", return_value=True):
            response = self.client.get(f"/api/v1/plugins/{self.plugin.pk}/")
            self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:500])
            self.assertValidResponse("/plugins/{plugin_id}/", "get", response.json())
            response = self.client.get("/api/v1/plugins/999999999/")
            self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
            self.assertValidResponse("/plugins/{plugin_id}/", "get", response.json(), HTTPStatus.NOT_FOUND)

    def test_another_accounts_plugin_is_not_found(self):
        """A plugin of another account is a 404 to a user who is not a superuser, not its manifest."""
        # factory_account_teardown() would also delete this class's account: delete only the stranger's.
        stranger, account, profile = mortal_user_factory()
        self.addCleanup(account.delete)
        self.addCleanup(stranger.delete)
        self.addCleanup(profile.delete)
        client = APIClient()
        client.force_authenticate(user=stranger)
        with patch("smarter.lib.django.waffle.switch_is_active", return_value=True):
            response = client.get(f"/api/v1/plugins/{self.plugin.pk}/")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND, response.content[:500])
        self.assertValidResponse("/plugins/{plugin_id}/", "get", response.json(), HTTPStatus.NOT_FOUND)
