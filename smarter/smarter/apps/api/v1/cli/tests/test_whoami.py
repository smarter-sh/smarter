"""Test Api v1 CLI non-brokered whoami command"""

import logging
from http import HTTPStatus

from django.urls import reverse

from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.common.api import SmarterApiVersions
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.journal.enum import (
    SCLIResponseMetadata,
    SmarterJournalApiResponseKeys,
    SmarterJournalCliCommands,
)
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from .base_class import ApiV1CliTestBase


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return (
        waffle.switch_is_active(SmarterWaffleSwitches.API_LOGGING)
        and waffle.switch_is_active(SmarterWaffleSwitches.PLUGIN_LOGGING)
        and level >= logging.INFO
    )


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class TestApiCliV1Whoami(ApiV1CliTestBase):
    """
    Test Api v1 CLI non-brokered whoami command

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

    def test_whoami(self) -> None:
        """Test whoami command"""

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
