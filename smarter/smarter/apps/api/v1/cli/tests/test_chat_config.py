"""Test Api v1 CLI non-brokered chat_config command"""

import logging
from http import HTTPStatus
from urllib.parse import urlencode

from django.urls import reverse

from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.apps.chatbot.models import ChatBot
from smarter.common.api import SmarterApiVersions
from smarter.common.conf import settings as smarter_settings
from smarter.common.const import SMARTER_CHAT_SESSION_KEY_NAME
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.journal.enum import (
    SCLIResponseMetadata,
    SmarterJournalApiResponseKeys,
    SmarterJournalCliCommands,
    SmarterJournalThings,
)
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from .base_class import ApiV1CliTestBase


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return (
        waffle.switch_is_active(SmarterWaffleSwitches.API_LOGGING)
        and waffle.switch_is_active(SmarterWaffleSwitches.PLUGIN_LOGGING)
        and level >= smarter_settings.log_level
    )


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class TestApiCliV1ChatConfig(ApiV1CliTestBase):
    """
    Test Api v1 CLI non-brokered chat_config command

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

        self.chatbot = self.chatbot_factory()

    def tearDown(self):
        if self.chatbot:
            self.chatbot.delete()
        super().tearDown()

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
        self.assertEqual(response[SmarterJournalApiResponseKeys.THING], SmarterJournalThings.CHAT_CONFIG.value)
        self.assertIsInstance(response[SmarterJournalApiResponseKeys.DATA], dict)
        self.assertIsInstance(response[SmarterJournalApiResponseKeys.METADATA], dict)

    def validate_data(self, data: dict) -> None:
        config_fields = [
            SMARTER_CHAT_SESSION_KEY_NAME,
            "sandbox_mode",
            "debug_mode",
            "chatbot",
            "meta_data",
            "history",
            "meta_data",
            "plugins",
        ]
        for field in config_fields:
            assert field in data.keys(), f"{field} not found in data keys: {data.keys()}"

    def test_chat_config(self) -> None:
        """Test chat_config command"""

        path = reverse(self.namespace + ApiV1CliReverseViews.chat_config, kwargs=self.kwargs)
        url_with_query_params = f"{path}?{self.query_params}"
        response, status = self.get_response(path=url_with_query_params)

        # pylint: disable=W0612
        expected_output = {
            "data": {
                "session_key": "25046e8d285b6bc3cefaac912397bfd542ea3d1ca6c596a527842403ef138bbd",
                "sandbox_mode": False,
                "debug_mode": True,
                "chatbot": {
                    "id": 1581,
                    "url_chatbot": "http://localhost:8000/api/v1/workbench/1581/chat/",
                    "account": {"accountNumber": "2873-5129-3755"},
                    "default_system_role": "The current date/time is Thursday, 2025-05-22T19:35:04+0000\nYou are a helpful chatbot. When given the opportunity to utilize function calling, you should always do so. This will allow you to provide the best possible responses to the user. If you are unable to provide a response, you should prompt the user for more information. If you are still unable to provide a response, you should inform the user that you are unable to help them at this time.",
                    "created_at": "2025-05-22T19:35:03.935229Z",
                    "updated_at": "2025-05-22T19:35:03.935243Z",
                    "name": "test35dd6e57c0deb505",
                    "description": "Test ChatBot",
                    "version": "1.0.0",
                    "deployed": False,
                    "provider": "openai",
                    "default_model": None,
                    "default_temperature": 0.5,
                    "default_max_tokens": 2048,
                    "app_name": "Smarter",
                    "app_assistant": "Smarty Pants",
                    "app_welcome_message": "Welcome to Smarter!",
                    "app_example_prompts": [],
                    "app_placeholder": "Type something here...",
                    "app_info_url": "https://smarter.sh",
                    "app_background_image_url": None,
                    "app_logo_url": None,
                    "app_file_attachment": False,
                    "dns_verification_status": "Not Verified",
                    "tls_certificate_issuance_status": "No Certificate",
                    "subdomain": None,
                    "custom_domain": None,
                },
                "history": {
                    "chat": {
                        "id": 512,
                        "created_at": "2025-05-22T19:35:04.427757Z",
                        "updated_at": "2025-05-22T19:35:04.427783Z",
                        "session_key": "25046e8d285b6bc3cefaac912397bfd542ea3d1ca6c596a527842403ef138bbd",
                        "ip_address": "127.0.0.1",
                        "user_agent": "user_agent",
                        "url": "http://testserver.local/api/v1/cli/chat/config/test35dd6e57c0deb505/",
                        "account": 5189,
                        "chatbot": 1581,
                    },
                    "chat_history": [],
                    "chat_tool_call_history": [],
                    "chat_plugin_usage_history": [],
                    "chatbot_request_history": [],
                    "plugin_selector_history": [],
                },
                "meta_data": {
                    "url": "http://testserver/api/v1/cli/chat/config/test35dd6e57c0deb505/",
                    "session_key": "856286a90329ae59ccaaa6b8edf15157f4671dfde34c72068fb79556c5ea6d1c",
                    "data": {},
                    "chatbot_id": 1581,
                    "chatbot_name": "test35dd6e57c0deb505",
                    "is_smarter_api": True,
                    "is_chatbot": True,
                    "is_chatbot_smarter_api_url": False,
                    "is_chatbot_named_url": False,
                    "is_chatbot_sandbox_url": False,
                    "is_chatbot_cli_api_url": True,
                    "is_default_domain": False,
                    "path": "/api/v1/cli/chat/config/test35dd6e57c0deb505/",
                    "root_domain": "testserver",
                    "subdomain": "",
                    "api_subdomain": "testserver",
                    "domain": "testserver",
                    "user": "testAdminUser_39083d40df6e1149",
                    "account": "2873-5129-3755",
                    "timestamp": "2025-05-22T19:35:04.392831",
                    "unique_client_string": "2873-5129-3755.http://testserver/api/v1/cli/chat/config/test35dd6e57c0deb505/.user_agent.127.0.0.1.2025-05-22T19:35:04.392831",
                    "client_key": "856286a90329ae59ccaaa6b8edf15157f4671dfde34c72068fb79556c5ea6d1c",
                    "ip_address": "127.0.0.1",
                    "user_agent": "user_agent",
                    "parsed_url": "",
                    "environment": "local",
                    "environment_api_domain": "api.localhost:8000",
                    "is_deployed": False,
                    "is_valid": True,
                    "error": None,
                    "is_authentication_required": False,
                    "name": "test35dd6e57c0deb505",
                    "chatbot": {
                        "id": 1581,
                        "created_at": "2025-05-22T19:35:03.935229Z",
                        "updated_at": "2025-05-22T19:35:03.935243Z",
                        "account": {"accountNumber": "2873-5129-3755"},
                        "name": "test35dd6e57c0deb505",
                        "description": "Test ChatBot",
                        "version": "1.0.0",
                        "subdomain": None,
                        "custom_domain": None,
                        "deployed": False,
                        "provider": "openai",
                        "default_model": None,
                        "default_system_role": "You are a helpful chatbot. When given the opportunity to utilize function calling, you should always do so. This will allow you to provide the best possible responses to the user. If you are unable to provide a response, you should prompt the user for more information. If you are still unable to provide a response, you should inform the user that you are unable to help them at this time.",
                        "default_temperature": 0.5,
                        "default_max_tokens": 2048,
                        "app_name": "Smarter",
                        "app_assistant": "Smarty Pants",
                        "app_welcome_message": "Welcome to Smarter!",
                        "app_example_prompts": [],
                        "app_placeholder": "Type something here...",
                        "app_info_url": "https://smarter.sh",
                        "app_background_image_url": None,
                        "app_logo_url": None,
                        "app_file_attachment": False,
                        "dns_verification_status": "Not Verified",
                        "tls_certificate_issuance_status": "No Certificate",
                        "url_chatbot": "http://localhost:8000/api/v1/workbench/1581/chat/",
                    },
                    "api_host": None,
                    "is_custom_domain": False,
                    "chatbot_custom_domain": None,
                },
                "plugins": {"meta_data": {"total_plugins": 0, "plugins_returned": 0}, "plugins": []},
            },
            "api": "smarter.sh/v1",
            "thing": "ChatConfig",
            "metadata": {"key": "1dbeec326a275722d0456d1cac97c029b34f183e850ac3655c7f57d4278b7975"},
        }

        self.assertEqual(status, HTTPStatus.OK)
        self.validate_response(response)
        data = response[SmarterJournalApiResponseKeys.DATA]
        self.validate_data(data=data)
        metadata = response[SmarterJournalApiResponseKeys.METADATA]
        metadata[SCLIResponseMetadata.COMMAND] = SmarterJournalCliCommands.CHAT_CONFIG.value

        session_key = data[SMARTER_CHAT_SESSION_KEY_NAME]

        # re-request the config to verify that we have a sticky session.
        # the session_key should be the same as the first request.
        response, status = self.get_response(path=url_with_query_params)
        data = response[SmarterJournalApiResponseKeys.DATA]
        next_session_key = data[SMARTER_CHAT_SESSION_KEY_NAME]
        self.assertEqual(session_key, next_session_key)

        # add assertions for existence of the top-level keys
        self.assertIn(SmarterJournalApiResponseKeys.API, response)
        self.assertIn(SmarterJournalApiResponseKeys.THING, response)
        self.assertIn(SmarterJournalApiResponseKeys.DATA, response)
        self.assertIn(SmarterJournalApiResponseKeys.METADATA, response)

        self.assertIsInstance(response[SmarterJournalApiResponseKeys.API], str)
        self.assertIsInstance(response[SmarterJournalApiResponseKeys.THING], str)
        self.assertIsInstance(response[SmarterJournalApiResponseKeys.DATA], dict)
        self.assertIsInstance(response[SmarterJournalApiResponseKeys.METADATA], dict)
        self.assertEqual(response[SmarterJournalApiResponseKeys.API], SmarterApiVersions.V1)
        self.assertEqual(response[SmarterJournalApiResponseKeys.THING], SmarterJournalThings.CHAT_CONFIG.value)
