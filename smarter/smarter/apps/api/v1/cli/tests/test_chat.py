"""Test Api v1 CLI non-brokered chat command"""

import hashlib
import os
from http import HTTPStatus
from urllib.parse import urlencode

from django.urls import reverse

from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.apps.api.v1.tests.base_class import ApiV1TestBase
from smarter.apps.chatbot.models import ChatBot
from smarter.common.api import SmarterApiVersions
from smarter.lib.journal.enum import (
    SCLIResponseMetadata,
    SmarterJournalApiResponseKeys,
    SmarterJournalCliCommands,
    SmarterJournalThings,
)


class TestApiCliV1Chat(ApiV1TestBase):
    """
    Test Api v1 CLI non-brokered chat command

    This class is a subclass of ApiV1TestBase, which gives us access to the
    setUpClass and tearDownClass methods, which are used to uniformly
    create and delete a user, account, user_profile and token record for
    testing purposes. ApiV1CliTestBase gives us access to the abstract methods
    that we need to implement in order to test the Api v1 CLI commands for
    Account.
    """

    def setUp(self):
        super().setUp()
        self.name = "TestChatBot"
        self.kwargs = {"name": self.name}

        random_bytes = os.urandom(32)
        uid = hashlib.sha256(random_bytes).hexdigest()
        self.query_params = urlencode({"uid": uid})

        self.chatbot = self.chatbot_factory()

    def tearDown(self):
        super().tearDown()
        if self.chatbot:
            self.chatbot.delete()

    def chatbot_factory(self):
        chatbot = ChatBot.objects.create(
            name=self.name,
            account=self.account,
            description="Test ChatBot",
            version="1.0.0",
            subdomain=None,
            custom_domain=None,
            deployed=False,
            app_name="Smarter",
            app_assistant="Smarty Pants",
            app_welcome_message="Welcome to Smarter!",
        )
        return chatbot

    def validate_response(self, response: dict) -> None:
        self.assertIsInstance(response, dict)
        self.assertEqual(response[SmarterJournalApiResponseKeys.API], SmarterApiVersions.V1)
        self.assertEqual(response[SmarterJournalApiResponseKeys.THING], SmarterJournalThings.CHAT.value)
        self.assertIsInstance(response[SmarterJournalApiResponseKeys.DATA], dict)
        self.assertIsInstance(response[SmarterJournalApiResponseKeys.METADATA], dict)

    def validate_data(self, data: dict) -> None:
        config_fields = [
            "request",
            "response",
        ]
        for field in config_fields:
            assert field in data.keys(), f"{field} not found in data keys: {data.keys()}"

    def test_chat(self) -> None:
        """Test chat command"""

        data = {"prompt": "Hello, World!"}
        path = reverse(ApiV1CliReverseViews.chat, kwargs=self.kwargs)
        url_with_query_params = f"{path}?{self.query_params}"
        response, status = self.get_response(path=url_with_query_params, data=data)
        self.assertEqual(status, HTTPStatus.OK)
        self.validate_response(response)
        data = response[SmarterJournalApiResponseKeys.DATA]
        self.validate_data(data=data)
        metadata = response[SmarterJournalApiResponseKeys.METADATA]
        metadata[SCLIResponseMetadata.COMMAND] = SmarterJournalCliCommands.CHAT.value
