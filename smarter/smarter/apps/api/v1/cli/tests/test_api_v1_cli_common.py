# pylint: disable=wrong-import-position
"""Test api/v1/cli common endpoints."""

import os
from http import HTTPStatus

from django.urls import reverse

from smarter.apps.api.v1.tests.base_class import ApiV1TestBase
from smarter.common.const import PYTHON_ROOT


class TestApiV1CliCommon(ApiV1TestBase):
    """Test api/v1/cli common endpoints."""

    def setUp(self):
        super().setUp()
        self.path = os.path.join(PYTHON_ROOT, "smarter", "apps", "api", "v1", "cli", "tests", "data")
        self.good_manifest_path = os.path.join(self.path, "good-plugin-manifest.yaml")
        with open(self.good_manifest_path, encoding="utf-8") as file:
            self.good_manifest_text = file.read()

    def test_valid_manifest(self):
        """Test that we get OK response when passing a valid manifest"""

        path = reverse("api_v1_cli_status_view")
        response, status = self.get_response(path)
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)
        self.assertIsInstance(response["compute"], dict)
        self.assertIsInstance(response["infrastructures"], dict)
        self.assertIsInstance(response["infrastructures"]["kubernetes"], dict)
        self.assertIsInstance(response["infrastructures"]["mysql"], dict)
        self.assertIsInstance(response["infrastructures"]["redis"], dict)

        path = reverse("api_v1_cli_whoami_view")
        response, status = self.get_response(path)
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)
        self.assertIsInstance(response["user"], dict)
        self.assertEqual(response["user"]["username"], self.user.username)
        self.assertIsInstance(response["account"], dict)
        self.assertEqual(response["account"]["company_name"], self.account.company_name)
