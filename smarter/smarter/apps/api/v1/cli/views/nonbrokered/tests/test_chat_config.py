"""Test Api v1 CLI non-brokered chat_config command."""

from http import HTTPStatus
from urllib.parse import urlencode

from smarter.apps.api.v1.cli.tests.base_class import ApiV1CliTestBase
from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.apps.llmclient.models import LLMClient
from smarter.common.api import SmarterApiVersions
from smarter.common.const import SMARTER_CHAT_SESSION_KEY_NAME
from smarter.lib import logging
from smarter.lib.django.shortcuts import reverse
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.journal.enum import (
    SCLIResponseMetadata,
    SmarterJournalApiResponseKeys,
    SmarterJournalCliCommands,
    SmarterJournalThings,
)
from smarter.lib.typing import SmarterDictType

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.API_LOGGING, SmarterWaffleSwitches.PLUGIN_LOGGING]
)


class TestApiCliV1ChatConfig(ApiV1CliTestBase):
    """
    Test Api v1 CLI non-brokered chat_config command.

    This class is a subclass of ApiV1TestBase, which gives us access to the
    setUpClass and tearDownClass methods, which are used to uniformly
    create and delete a user, account, user_profile and token record for
    testing purposes. ApiV1CliTestBase gives us access to the abstract methods
    that we need to implement in order to test the Api v1 CLI commands for
    Account.
    """

    def setUp(self):
        super().setUp()
        self.kwargs = {"name": self.name}

        self.query_params = urlencode({"uid": self.uid})

        self.llmclient = self.llmclient_factory()

    def tearDown(self):
        if self.llmclient:
            self.llmclient.delete()
        super().tearDown()

    def llmclient_factory(self):
        llmclient = LLMClient.objects.create(
            name=self.name,
            user_profile=self.user_profile,
            description="Test LLMClient",
            version="1.0.0",
            subdomain=None,
            custom_domain=None,
            deployed=False,
            app_name="Smarter",
            app_assistant="Smarty Pants",
            app_welcome_message="Welcome to Smarter!",
        )
        return llmclient

    def validate_response(self, response: SmarterDictType) -> None:
        self.assertIsInstance(response, dict)
        self.assertEqual(response[SmarterJournalApiResponseKeys.API], SmarterApiVersions.V1)
        self.assertEqual(
            response[SmarterJournalApiResponseKeys.METADATA][SmarterJournalApiResponseKeys.THING],
            SmarterJournalThings.PROMPT_CONFIG.value,
        )
        self.assertIsInstance(response[SmarterJournalApiResponseKeys.DATA], dict)
        self.assertIsInstance(response[SmarterJournalApiResponseKeys.METADATA], dict)

    def validate_data(self, data: SmarterDictType) -> None:
        config_fields = [
            SMARTER_CHAT_SESSION_KEY_NAME,
            "sandbox_mode",
            "debug_mode",
            "llmclient",
            "meta_data",
            "history",
            "meta_data",
            "plugins",
        ]
        for field in config_fields:
            assert field in data.keys(), f"{field} not found in data keys: {data.keys()}"

    def test_chat_config(self) -> None:
        """Test chat_config command."""

        path = reverse(self.namespace + ApiV1CliReverseViews.chat_config, kwargs=self.kwargs)
        url_with_query_params = f"{path}?{self.query_params}"
        response, status = self.get_response(path=url_with_query_params)
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)

        logger.debug("chat_config() raw response: %s", response)

        self.validate_response(response)
        data = response[SmarterJournalApiResponseKeys.DATA]
        self.validate_data(data=data)
        session_key = data[SMARTER_CHAT_SESSION_KEY_NAME]

        # the cli receives every diagnostic part of the configuration.
        self.assertEqual(
            set(data["history"]),
            {
                "chat_history",
                "prompt_tool_call_history",
                "prompt_plugin_usage_history",
                "plugin_selector_history",
                "llmclient_request_history",
            },
        )
        self.assertIn("llmclient", data["meta_data"])

        # add assertions for existence of the top-level keys
        self.assertIn(SmarterJournalApiResponseKeys.API, response)
        self.assertIn(SmarterJournalApiResponseKeys.THING, response[SmarterJournalApiResponseKeys.METADATA])
        self.assertIn(SmarterJournalApiResponseKeys.DATA, response)
        self.assertIn(SmarterJournalApiResponseKeys.METADATA, response)

        self.assertIsInstance(response[SmarterJournalApiResponseKeys.API], str)
        self.assertIsInstance(
            response[SmarterJournalApiResponseKeys.METADATA][SmarterJournalApiResponseKeys.THING], str
        )
        self.assertIsInstance(response[SmarterJournalApiResponseKeys.DATA], dict)
        self.assertIsInstance(response[SmarterJournalApiResponseKeys.METADATA], dict)
        self.assertEqual(response[SmarterJournalApiResponseKeys.API], SmarterApiVersions.V1)
        self.assertEqual(
            response[SmarterJournalApiResponseKeys.METADATA][SmarterJournalApiResponseKeys.THING],
            SmarterJournalThings.PROMPT_CONFIG.value,
        )

        metadata = response[SmarterJournalApiResponseKeys.METADATA]
        metadata[SCLIResponseMetadata.COMMAND] = SmarterJournalCliCommands.PROMPT_CONFIG.value

        # re-request the config to verify that we have a sticky session.
        # the session_key should be the same as the first request.
        query_params = self.query_params + f"&{SMARTER_CHAT_SESSION_KEY_NAME}={session_key}"
        url_with_query_params = f"{path}?{query_params}"
        response, status = self.get_response(path=url_with_query_params)
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)

        data = response[SmarterJournalApiResponseKeys.DATA]
        next_session_key = data[SMARTER_CHAT_SESSION_KEY_NAME]
        self.assertEqual(session_key, next_session_key)
