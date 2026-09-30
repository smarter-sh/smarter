"""Test Api v1 CLI non-brokered status command."""

from http import HTTPStatus

from smarter.apps.api.v1.cli.tests.base_class import ApiV1CliTestBase
from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.common.api import SmarterApiVersions
from smarter.lib.django.shortcuts import reverse
from smarter.lib.journal.enum import (
    SCLIResponseMetadata,
    SmarterJournalApiResponseKeys,
    SmarterJournalCliCommands,
)


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

    def validate_response(self, response: dict) -> None:
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
        self.assertIn("compute", data.keys())

        metadata = response[SmarterJournalApiResponseKeys.METADATA]
        self.assertEqual(metadata[SCLIResponseMetadata.COMMAND], SmarterJournalCliCommands.STATUS.value)
