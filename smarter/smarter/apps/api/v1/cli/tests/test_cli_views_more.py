"""
Test the cli's json-schema, example-manifest and whoami views, and the Brokers lookups.

The json-schema and example-manifest views need no authentication, and are tested for every kind.
"""

from http import HTTPStatus
from unittest.mock import patch

from django.test import Client
from django.urls import reverse

from smarter.apps.api.v1.cli.brokers import Brokers
from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.lib import json
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .base_class import ApiV1CliTestBase


class TestBrokersLookups(ApiV1CliTestBase):
    """Test Brokers.get_broker_kind(), from_url() and all_brokers()."""

    def test_get_broker_kind(self):
        self.assertEqual(Brokers.get_broker_kind("Account"), "Account")
        self.assertEqual(Brokers.get_broker_kind("accounts"), "Account")
        self.assertEqual(Brokers.get_broker_kind("llm_client"), Brokers.get_broker_kind("LLMClient"))
        self.assertIsNone(Brokers.get_broker_kind(""))
        self.assertIsNone(Brokers.get_broker_kind("not_a_kind"))

    def test_from_url(self):
        self.assertEqual(Brokers.from_url("http://localhost:9357/api/v1/cli/example_manifest/account/"), "Account")
        self.assertIsNone(Brokers.from_url("http://localhost:9357/dashboard/account/"))
        self.assertIsNone(Brokers.from_url("http://localhost:9357/api/v1/cli/whoami/"))
        self.assertIn("Account", Brokers.all_brokers())


class TestSchemaAndExampleManifestViews(ApiV1CliTestBase):
    """Get and post the json schema and example manifest of every kind."""

    def url(self, name: str, kind: str) -> str:
        return reverse(ApiV1CliReverseViews.namespace + name, kwargs={"kind": kind})

    def test_every_kind(self):
        """Test that every kind's json schema and example manifest are returned, by POST, and by GET when it is allowed."""
        client = Client()
        with patch(
            "smarter.lib.django.waffle.switch_is_active",
            side_effect=lambda name: name == SmarterWaffleSwitches.ALLOW_API_GET,
        ):
            for kind in Brokers.all_brokers():
                for name in (ApiV1CliReverseViews.json_schema, ApiV1CliReverseViews.example_manifest):
                    for method in ("get", "post"):
                        with self.subTest(kind=kind, view=name, method=method):
                            response = getattr(client, method)(self.url(name, kind))
                            self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:300])
                            self.assertIn("data", json.loads(response.content))

    def test_get_not_allowed(self):
        """Test that the example manifest can't be got while the ALLOW_API_GET switch is off."""
        with patch("smarter.lib.django.waffle.switch_is_active", return_value=False):
            response = Client().get(self.url(ApiV1CliReverseViews.example_manifest, "Account"))
        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)


class TestWhoamiView(ApiV1CliTestBase):
    """Test that whoami returns the api key's user and account."""

    def test_whoami(self):
        response, status = self.get_response(path=reverse(ApiV1CliReverseViews.namespace + ApiV1CliReverseViews.whoami))
        self.assertEqual(status, HTTPStatus.OK, response)
        self.assertEqual(response["data"]["user"]["username"], self.admin_user.username)
