"""Test Api v1 CLI base class for brokered commands."""

from http import HTTPStatus
from typing import Any
from urllib.parse import urlencode

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import OperationalError
from pydantic import BaseModel, Field
from pydantic import ValidationError as PydanticValidationError
from rest_framework.test import APIClient

from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.apps.api.v1.cli.views.base import (
    APIV1CLIViewBadRequestError,
    APIV1CLIViewError,
    client_error_in,
    describe_exception,
    format_validation_error,
    http_status_for_exception,
)
from smarter.apps.api.v1.cli.views.swagger import BUG_REPORT
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.lib import json, logging
from smarter.lib.django.shortcuts import reverse
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.journal.enum import SmarterJournalApiResponseKeys
from smarter.lib.manifest.broker import (
    SAMBrokerError,
    SAMBrokerErrorNotFound,
    SAMBrokerInternalError,
)
from smarter.lib.manifest.enum import SAMKeys
from smarter.lib.manifest.loader import SAMLoaderError
from smarter.lib.unittest.base_classes import SmarterTestBase

from .base_class import ApiV1CliTestBase

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.API_LOGGING])


class TestApiCliV1BaseClass(ApiV1CliTestBase):
    """
    Test Api v1 CLI coverage gaps in base class for brokered commands.

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
        """Prepare and get a response from an api/v1/ endpoint."""
        logger.info(
            "TestApiCliV1BaseClass.authentication_scenarios() testing API endpoint: %s, wrong_key: %s, missing_key: %s, session_authentication: %s",
            path,
            wrong_key,
            missing_key,
            session_authentication,
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
        logger.info("Response from %s: Status Code: %s,\n%s", path, response.status_code, response_json)
        return response_json, response.status_code

    def test_baseauthentication_with_apikey(self):
        """Control test to ensure that the actual expected cases really works."""
        response, status = self.get_response(path=self.public_path)
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIn(SmarterJournalApiResponseKeys.DATA, response.keys())

    def test_bad_authentication_public_url(self):
        """Verify that wrong key authentication is insufficient to access the endpoint."""
        _, status = self.authentication_scenarios(path=self.public_path, wrong_key=True)
        self.assertEqual(status, HTTPStatus.OK)

    def test_authentication_with_no_apikey_public(self):
        """Verify that missing key authentication is insufficient to access the endpoint."""
        response, status = self.authentication_scenarios(path=self.public_path, missing_key=True)
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIn(SmarterJournalApiResponseKeys.DATA, response.keys())

    def test_authentication_with_no_apikey_private(self):
        """Verify that missing key authentication is insufficient to access the endpoint."""
        response, status = self.authentication_scenarios(path=self.private_path, missing_key=True)
        self.assertEqual(status, HTTPStatus.FORBIDDEN)
        self.assertIn(SmarterJournalApiResponseKeys.ERROR, response.keys())

    def test_authentication_with_session(self):
        """Verify that session authentication also works api requests."""
        _, status = self.authentication_scenarios(path=self.public_path, session_authentication=True)
        self.assertEqual(status, HTTPStatus.OK)


class Temperature(BaseModel):
    """A model whose validation error the tests below format."""

    defaultTemperature: float = Field(..., ge=0.0, le=1.0)


def pydantic_validation_error(**data) -> PydanticValidationError:
    try:
        Temperature(**data)
    except PydanticValidationError as e:
        return e
    raise AssertionError("expected a validation error")


class SAMTestBrokerError(SAMBrokerError):
    """A broker's own error class, like SAMLLMClientBrokerError."""


def raised_from(error: BaseException, cause: BaseException) -> BaseException:
    try:
        raise error from cause
    except BaseException as e:  # pylint: disable=broad-except
        return e


class TestCliExceptionClassification(SmarterTestBase):
    """Test the HTTP status and the description of the error response for each kind of exception."""

    def test_status(self):
        cases = [
            (pydantic_validation_error(defaultTemperature=2), HTTPStatus.BAD_REQUEST),
            (DjangoValidationError({"provider": ["not a valid provider"]}), HTTPStatus.BAD_REQUEST),
            (SAMLoaderError("Missing required key: spec"), HTTPStatus.BAD_REQUEST),
            (APIV1CLIViewBadRequestError("unknown kind"), HTTPStatus.BAD_REQUEST),
            # a broker's own error class, which is a subclass of SAMBrokerError
            (SAMTestBrokerError("invalid"), HTTPStatus.BAD_REQUEST),
            (raised_from(SAMTestBrokerError("failed"), DjangoValidationError("bad")), HTTPStatus.BAD_REQUEST),
            # a broker error that a database error caused is not the client's error
            (raised_from(SAMTestBrokerError("failed"), OperationalError("gone")), HTTPStatus.INTERNAL_SERVER_ERROR),
            (SAMBrokerErrorNotFound("missing"), HTTPStatus.NOT_FOUND),
            (SAMBrokerInternalError("bug"), HTTPStatus.INTERNAL_SERVER_ERROR),
            (APIV1CLIViewError("bug"), HTTPStatus.INTERNAL_SERVER_ERROR),
            (RuntimeError("bug"), HTTPStatus.INTERNAL_SERVER_ERROR),
        ]
        for e, status in cases:
            with self.subTest(e=repr(e)):
                self.assertEqual(http_status_for_exception(e), status)

    def test_client_error_in(self):
        cause = DjangoValidationError("bad")
        self.assertIs(client_error_in(raised_from(SAMTestBrokerError("failed"), cause)), cause)
        self.assertIsNone(client_error_in(raised_from(SAMTestBrokerError("failed"), OperationalError("gone"))))

    def test_format_validation_error(self):
        description = format_validation_error(pydantic_validation_error(defaultTemperature=2.5))
        self.assertIn("Temperature is not valid", description)
        self.assertIn("defaultTemperature: Input should be less than or equal to 1 (got 2.5)", description)
        long_input = format_validation_error(pydantic_validation_error(defaultTemperature="x" * 500))
        self.assertLess(len(long_input), 300)
        self.assertEqual(
            format_validation_error(DjangoValidationError({"app_info_url": ["Enter a valid URL."]})),
            "app_info_url: Enter a valid URL.",
        )

    def test_describe_exception(self):
        """Test that a client error says what is wrong, and that only a 500 asks for a bug report."""
        e = pydantic_validation_error(defaultTemperature=-1)
        description = describe_exception(e, http_status_for_exception(e))
        self.assertIn("defaultTemperature", description)
        self.assertNotIn(BUG_REPORT, description)

        e = raised_from(SAMTestBrokerError("Failed to apply"), DjangoValidationError({"app_name": ["too long"]}))
        description = describe_exception(e, http_status_for_exception(e))
        self.assertIn("Failed to apply", description)
        self.assertIn("app_name: too long", description)
        self.assertNotIn(BUG_REPORT, description)

        e = RuntimeError("unexpected")
        description = describe_exception(e, http_status_for_exception(e))
        self.assertIn(BUG_REPORT, description)
        self.assertIn("unexpected", description)

        # other errors, e.g. not found, keep their own message
        self.assertIsNone(describe_exception(SAMBrokerErrorNotFound("missing"), HTTPStatus.NOT_FOUND))
