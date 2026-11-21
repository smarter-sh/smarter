"""
Test api/v1/ base class.

We have somewhere in the neighborhood of 75 api endpoints to test, so we want
ensure that:
- our setUp and tearDown methods are as efficient as possible.
- we are authenticating our http requests properly and consistently.
"""

from typing import Optional, Union

from rest_framework.test import APIClient

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.lib import json, logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.models import SmarterAuthToken
from smarter.lib.typing import SmarterDictType

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.API_LOGGING])


class ApiV1TestBase(TestAccountMixin):
    """Test api/v1/ base class."""

    namespace = "api:v1:"

    def setUp(self):
        super().setUp()

        self.token_record, self.token_key = SmarterAuthToken.objects.create(  # type: ignore[call-arg]
            user_profile=self.user_profile,
            name=self.admin_user.username,
            user=self.admin_user,
            description=self.admin_user.username,
        )

    def tearDown(self):
        try:
            self.token_record.delete()
        except SmarterAuthToken.DoesNotExist:
            pass

        return super().tearDown()

    def get_response(
        self, path, manifest: Union[str, SmarterDictType, None] = None, data: Optional[SmarterDictType] = None
    ) -> tuple[SmarterDictType, int]:
        """Prepare and get a response from an api/v1/ endpoint."""
        client = APIClient()

        headers = {"Authorization": f"Token {self.token_key}"}

        # never the headers: they hold the api key.
        logger.info("with path: %s manifest: %s, data: %s", path, manifest, data)

        if manifest:
            response = client.post(path=path, data=manifest, content_type="application/json", headers=headers)
        elif data:
            response = client.post(path=path, data=data, content_type="application/json", headers=headers)
        else:
            response = client.post(path=path, content_type="application/json", data=None, headers=headers)
        response_content = response.content.decode("utf-8")

        try:
            response_json = json.loads(response_content)
        except json.JSONDecodeError as e:
            logger.warning(
                "could not decode JSON response for path: %s error: %s",
                path,
                str(e),
            )
            response_json = {"raw_response": response_content}

        logger.info(
            "%s with status code: %d response: %s",
            path,
            response.status_code,
            response_json,
        )
        return response_json, response.status_code
