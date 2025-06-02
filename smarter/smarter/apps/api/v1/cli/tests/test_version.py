"""Test Api v1 CLI non-brokered version command"""

from http import HTTPStatus

from django.urls import reverse

from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.common.api import SmarterApiVersions
from smarter.lib.journal.enum import (
    SCLIResponseMetadata,
    SmarterJournalApiResponseKeys,
    SmarterJournalCliCommands,
)

from .base_class import ApiV1CliTestBase


class TestApiCliV1Version(ApiV1CliTestBase):
    """
    Test Api v1 CLI non-brokered version command

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
        self.assertEqual(response[SmarterJournalApiResponseKeys.THING], "None")
        self.assertIsInstance(response[SmarterJournalApiResponseKeys.DATA], dict)
        self.assertIsInstance(response[SmarterJournalApiResponseKeys.METADATA], dict)

    def test_version(self) -> None:
        """Test version command"""

        path = reverse(self.namespace + ApiV1CliReverseViews.version, kwargs=None)
        response, status = self.get_response(path=path)
        self.assertEqual(status, HTTPStatus.OK)
        self.validate_response(response)
        data = response[SmarterJournalApiResponseKeys.DATA]
        self.assertIn("api", data.keys())
        self.assertIn("cli", data.keys())

        metadata = response[SmarterJournalApiResponseKeys.METADATA]
        metadata[SCLIResponseMetadata.COMMAND] = SmarterJournalCliCommands.VERSION.value
