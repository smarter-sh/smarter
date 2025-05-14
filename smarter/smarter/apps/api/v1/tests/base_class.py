"""
Test api/v1/ base class.

We have somewhere in the neighborhood of 75 api endpoints to test, so we want
ensure that:
- our setUp and tearDown methods are as efficient as possible.
- we are authenticating our http requests properly and consistently.
"""

import json

from django.test import Client

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.lib.drf.models import SmarterAuthToken


class ApiV1TestBase(TestAccountMixin):
    """Test api/v1/ base class."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        instance = cls()

        cls.token_record, cls.token_key = SmarterAuthToken.objects.create(
            name=instance.admin_user.username,
            user=instance.admin_user,
            description=instance.admin_user.username,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()
        instance = cls()
        try:
            instance.token_record.delete()
        except SmarterAuthToken.DoesNotExist:
            pass

    def get_response(self, path, manifest: str = None, data: dict = None) -> tuple[dict[str, any], int]:
        """
        Prepare and get a response from an api/v1/ endpoint.
        """
        client = Client()
        headers = {"HTTP_AUTHORIZATION": f"Token {self.token_key}"}

        if manifest:
            response = client.post(path=path, data=manifest, content_type="application/json", **headers)
        elif data:
            response = client.post(path=path, data=data, content_type="application/json", **headers)
        else:
            response = client.post(path=path, content_type="application/json", data=None, **headers)
        response_content = response.content.decode("utf-8")
        response_json = json.loads(response_content)
        return response_json, response.status_code
