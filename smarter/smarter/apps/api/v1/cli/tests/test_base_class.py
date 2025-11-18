"""Test Api v1 CLI base class for brokered commands"""

import logging
from http import HTTPStatus
from typing import Any
from urllib.parse import urlencode

from django.urls import reverse
from rest_framework.test import APIClient

from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.common.conf import settings as smarter_settings
from smarter.lib import json
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.journal.enum import SmarterJournalApiResponseKeys
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.manifest.enum import SAMKeys

from .base_class import ApiV1CliTestBase


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.API_LOGGING) and level >= smarter_settings.log_level


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class TestApiCliV1BaseClass(ApiV1CliTestBase):
    """
    Test Api v1 CLI coverage gaps in base class for brokered commands
    41, 85-89, 115, 138, 165, 178, 197-198, 211, 249-252, 260-262, 274, 294-295, 301-305, 326-360

    This class is a subclass of ApiV1TestBase, which gives us access to the
    setUpClass and tearDownClass methods, which are used to uniformly
    create and delete a user, account, user_profile and token record for
    testing purposes. ApiV1CliTestBase gives us access to the abstract methods
    that we need to implement in order to test the Api v1 CLI commands for
    User.
    """

    def setUp(self):
        super().setUp()
        self.kwargs = {SAMKeys.KIND.value: SAMKinds.ACCOUNT.value}
        self.query_params = urlencode({"username": self.non_admin_user.username})
        self.public_path = reverse(self.namespace + ApiV1CliReverseViews.example_manifest, kwargs=self.kwargs)
        self.private_path = reverse(self.namespace + ApiV1CliReverseViews.describe, kwargs=self.kwargs)

    def authentication_scenarios(
        self, path, wrong_key: bool = False, missing_key: bool = False, session_authentication: bool = False
    ) -> tuple[dict[str, Any], int]:
        """
        Prepare and get a response from an api/v1/ endpoint.
        """
        logger.info(
            f"TestApiCliV1BaseClass.authentication_scenarios() testing API endpoint: {path}, wrong_key: {wrong_key}, missing_key: {missing_key}, session_authentication: {session_authentication}"
        )
        client = APIClient()
        headers_wrong_key = {"HTTP_AUTHORIZATION": "Token WRONG_KEY"}
        headers_missing_key = {}

        response = None
        if wrong_key:
            response = client.post(path=path, data=None, content_type="application/json", headers=headers_wrong_key)
        elif missing_key:
            response = client.post(path=path, data=None, content_type="application/json", headers=headers_missing_key)
        elif session_authentication:
            client.force_login(user=self.non_admin_user)
            response = client.post(path=path, data=None, content_type="application/json")

        if response is None:
            raise ValueError("No response was generated.")

        response_content = response.content.decode("utf-8")
        response_json = json.loads(response_content)
        logger.info(f"Response from {path}: Status Code: {response.status_code},\n{response_json}")
        return response_json, response.status_code

    def test_baseauthentication_with_apikey(self):
        """control test to ensure that the actual expected cases really works."""
        response, status = self.get_response(path=self.public_path)
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIn(SmarterJournalApiResponseKeys.DATA, response.keys())

    def test_bad_authentication_public_url(self):
        """verify that wrong key authentication is insufficient to access the endpoint"""
        _, status = self.authentication_scenarios(path=self.public_path, wrong_key=True)
        self.assertEqual(status, HTTPStatus.OK)

    def test_authentication_with_no_apikey_public(self):
        """verify that missing key authentication is insufficient to access the endpoint"""
        response, status = self.authentication_scenarios(path=self.public_path, missing_key=True)
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIn(SmarterJournalApiResponseKeys.DATA, response.keys())

    def test_authentication_with_no_apikey_private(self):
        """verify that missing key authentication is insufficient to access the endpoint"""
        response, status = self.authentication_scenarios(path=self.private_path, missing_key=True)
        self.assertEqual(status, HTTPStatus.FORBIDDEN)
        self.assertIn(SmarterJournalApiResponseKeys.ERROR, response.keys())

    def test_authentication_with_session(self):
        """verify that session authentication also works api requests."""
        _, status = self.authentication_scenarios(path=self.public_path, session_authentication=True)
        self.assertEqual(status, HTTPStatus.OK)
