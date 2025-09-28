"""
Test api/v1/ base class.

We have somewhere in the neighborhood of 75 api endpoints to test, so we want
ensure that:
- our setUp and tearDown methods are as efficient as possible.
- we are authenticating our http requests properly and consistently.
"""

import logging
from typing import Any, Optional

from rest_framework.test import APIClient

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.lib import json
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.models import SmarterAuthToken
from smarter.lib.logging import WaffleSwitchedLoggerWrapper


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.API_LOGGING) and level >= logging.INFO


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class ApiV1TestBase(TestAccountMixin):
    """Test api/v1/ base class."""

    namespace = "api:v1:"

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        instance = cls()

        cls.token_record, cls.token_key = SmarterAuthToken.objects.create(  # type: ignore[call-arg]
            name=instance.admin_user.username,
            user=instance.admin_user,
            description=instance.admin_user.username,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        instance = cls()
        try:
            instance.token_record.delete()
        except SmarterAuthToken.DoesNotExist:
            pass
        super().tearDownClass()

    def get_response(
        self, path, manifest: Optional[str] = None, data: Optional[dict] = None
    ) -> tuple[dict[str, Any], int]:
        """
        Prepare and get a response from an api/v1/ endpoint.
        """
        client = APIClient()

        headers = {"Authorization": f"Token {self.token_key}"}

        logger.info(
            "ApiV1TestBase.get_response() with path: %s headers: %s manifest: %s, data: %s",
            path,
            headers,
            manifest,
            data,
        )

        if manifest:
            logger.info(
                "ApiV1TestBase.get_response() with path: %s, headers: %s, manifest: %s", path, headers, manifest
            )
            response = client.post(path=path, data=manifest, content_type="application/json", headers=headers)
        elif data:
            logger.info("ApiV1TestBase.get_response() with data: %s", data)
            response = client.post(path=path, data=data, content_type="application/json", headers=headers)
        else:
            logger.info("ApiV1TestBase.get_response() with no data or manifest. headers: %s", headers)
            response = client.post(path=path, content_type="application/json", data=None, headers=headers)
        response_content = response.content.decode("utf-8")
        response_json = json.loads(response_content)

        logger.info(
            "ApiV1TestBase.get_response() %s with status code: %d response: %s",
            path,
            response.status_code,
            response_json,
        )
        return response_json, response.status_code
