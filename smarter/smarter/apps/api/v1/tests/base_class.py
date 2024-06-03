"""
Test api/v1/ base class.

We have somewhere in the neighborhood of 75 api endpoints to test, so we want
ensure that our setUp and tearDown methods are as efficient as possible.
"""

import json
import unittest

from django.test import Client

from smarter.apps.account.mixins import AccountMixin
from smarter.apps.account.models import Account, UserProfile
from smarter.apps.account.tests.factories import admin_user_factory
from smarter.lib.django.user import User
from smarter.lib.drf.models import SmarterAuthToken


class ApiV1TestBase(unittest.TestCase, AccountMixin):
    """Test api/v1/ base class."""

    name: str = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.name = "CliTestPlugin"
        cls._user, cls._account, cls._user_profile = admin_user_factory()
        cls.token_record, cls.token_key = SmarterAuthToken.objects.create(
            name=cls.user.get_username(),
            user=cls.user,
            description=cls.user.get_username(),
        )

    @classmethod
    def tearDownClass(cls) -> None:
        try:
            cls.user_profile.delete()
        except UserProfile.DoesNotExist:
            pass
        try:
            cls.user.delete()
        except User.DoesNotExist:
            pass
        try:
            cls.account.delete()
        except Account.DoesNotExist:
            pass
        try:
            cls.token_record.delete()
        except SmarterAuthToken.DoesNotExist:
            pass

    def get_response(self, path, manifest: str = None) -> tuple[dict[str, any], int]:
        """
        Prepare and get a response from an api/v1/ endpoint.
        """
        client = Client()
        headers = {"HTTP_AUTHORIZATION": f"Token {self.token_key}"}
        response = client.post(path=path, data=manifest, content_type="application/json", **headers)

        response_content = response.content.decode("utf-8")
        response_json = json.loads(response_content)
        return response_json, response.status_code
