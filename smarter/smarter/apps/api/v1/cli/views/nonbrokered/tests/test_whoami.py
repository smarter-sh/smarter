"""Test Api v1 CLI non-brokered whoami command."""

from http import HTTPStatus
from unittest import mock

from smarter.apps.api.v1.cli.tests.base_class import ApiV1CliTestBase
from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.apps.api.v1.cli.views.base import (
    APIV1CLIViewNotFoundError,
    http_status_for_exception,
)
from smarter.apps.api.v1.cli.views.nonbrokered.whoami import ApiV1CliWhoamiApiView
from smarter.common.api import SmarterApiVersions
from smarter.lib import logging
from smarter.lib.django.shortcuts import reverse
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.journal.enum import (
    SCLIResponseMetadata,
    SmarterJournalApiResponseKeys,
    SmarterJournalCliCommands,
)
from smarter.lib.typing import SmarterDictType

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.API_LOGGING, SmarterWaffleSwitches.PLUGIN_LOGGING]
)


class TestApiCliV1Whoami(ApiV1CliTestBase):
    """
    Test Api v1 CLI non-brokered whoami command.

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
        self.assertEqual(response[SmarterJournalApiResponseKeys.METADATA][SmarterJournalApiResponseKeys.THING], "None")
        self.assertIsInstance(response[SmarterJournalApiResponseKeys.DATA], dict)
        self.assertIsInstance(response[SmarterJournalApiResponseKeys.METADATA], dict)

    def test_whoami(self) -> None:
        """Test whoami command."""

        path = reverse(self.namespace + ApiV1CliReverseViews.whoami, kwargs=None)
        logger.info("TestApiCliV1Whoami().test_whoami() Testing whoami command at path: %s", path)
        response, status = self.get_response(path=path)
        self.assertEqual(status, HTTPStatus.OK)
        self.validate_response(response)
        data = response[SmarterJournalApiResponseKeys.DATA]
        self.assertIn("user", data.keys())
        self.assertIn("account", data.keys())

        metadata = response[SmarterJournalApiResponseKeys.METADATA]
        metadata[SCLIResponseMetadata.COMMAND] = SmarterJournalCliCommands.WHOAMI.value

    def assert_journaled_error(self, response: SmarterDictType, status: int, error_class: str, command: str) -> None:
        """Assert that an error response is the journal's error envelope, not a bare {"error": "..."}."""
        self.assertEqual(response[SmarterJournalApiResponseKeys.API], SmarterApiVersions.V1)
        self.assertEqual(response[SmarterJournalApiResponseKeys.METADATA]["command"], command)
        error = response["error"]
        self.assertIsInstance(error, dict)
        self.assertEqual(error["errorClass"], error_class)
        self.assertEqual(error["status"], status)

    def test_whoami_without_user_profile(self) -> None:
        """A user without a user profile is a journaled 404."""
        view = ApiV1CliWhoamiApiView()
        with mock.patch.object(
            ApiV1CliWhoamiApiView, "user_profile", new_callable=mock.PropertyMock, return_value=None
        ):
            with self.assertRaises(APIV1CLIViewNotFoundError):
                view.whoami()
        self.assertEqual(http_status_for_exception(APIV1CLIViewNotFoundError("x")), HTTPStatus.NOT_FOUND)
