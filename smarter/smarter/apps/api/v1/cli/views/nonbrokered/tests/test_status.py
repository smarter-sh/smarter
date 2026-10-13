"""Test Api v1 CLI non-brokered status command."""

from http import HTTPStatus
from unittest import mock

from smarter.apps.api.v1.cli.tests.base_class import ApiV1CliTestBase
from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.common.api import SmarterApiVersions
from smarter.lib.django.shortcuts import reverse
from smarter.lib.journal.enum import (
    SCLIResponseMetadata,
    SmarterJournalApiResponseKeys,
    SmarterJournalCliCommands,
)
from smarter.lib.typing import SmarterDictType


class TestApiCliV1Status(ApiV1CliTestBase):
    """
    Test Api v1 CLI non-brokered status command.

    This class is a subclass of ApiV1TestBase, which gives us access to the
    setUpClass and tearDownClass methods, which are used to uniformly
    create and delete a user, account, user_profile and token record for
    testing purposes. ApiV1CliTestBase gives us access to the abstract methods
    that we need to implement in order to test the Api v1 CLI commands for
    Account.
    """

    def validate_response(self, response: SmarterDictType) -> None:
        self.assertIsInstance(response, dict)
        self.assertEqual(response[SmarterJournalApiResponseKeys.API], SmarterApiVersions.V1)
        self.assertIsInstance(response[SmarterJournalApiResponseKeys.DATA], dict)

        metadata = response[SmarterJournalApiResponseKeys.METADATA]
        self.assertIsInstance(metadata, dict)
        self.assertEqual(metadata[SmarterJournalApiResponseKeys.THING], "None")

    def test_status(self) -> None:
        """Test status command."""

        path = reverse(self.namespace + ApiV1CliReverseViews.status, kwargs=None)
        response, status = self.get_response(path=path)
        self.assertEqual(status, HTTPStatus.OK)
        self.validate_response(response)
        data = response[SmarterJournalApiResponseKeys.DATA]
        self.assertIn("infrastructures", data.keys())
        # without AWS credentials, kubernetes is {"error": ...} instead of a failed request.
        self.assertIn("kubernetes", data["infrastructures"].keys())
        self.assertIn("redis", data["infrastructures"].keys())
        self.assertIn("compute", data.keys())

        metadata = response[SmarterJournalApiResponseKeys.METADATA]
        self.assertEqual(metadata[SCLIResponseMetadata.COMMAND], SmarterJournalCliCommands.STATUS.value)

    def assert_journaled_error(self, response: SmarterDictType, status: int, error_class: str, command: str) -> None:
        """Assert that an error response is the journal's error envelope, not a bare {"error": "..."}."""
        self.assertEqual(response[SmarterJournalApiResponseKeys.API], SmarterApiVersions.V1)
        self.assertEqual(response[SmarterJournalApiResponseKeys.METADATA]["command"], command)
        error = response["error"]
        self.assertIsInstance(error, dict)
        self.assertEqual(error["errorClass"], error_class)
        self.assertEqual(error["status"], status)

    def test_status_error_is_journaled(self) -> None:
        """An error is returned as a journaled error response, with its status."""
        path = reverse(self.namespace + ApiV1CliReverseViews.status, kwargs=None)
        with mock.patch(
            "smarter.apps.api.v1.cli.views.nonbrokered.status.ApiV1CliStatusApiView.get_redis_info",
            side_effect=RuntimeError("redis is down"),
        ):
            response, status = self.get_response(path=path)
        self.assertEqual(status, HTTPStatus.INTERNAL_SERVER_ERROR)
        self.assert_journaled_error(response, HTTPStatus.INTERNAL_SERVER_ERROR, "RuntimeError", "status")
