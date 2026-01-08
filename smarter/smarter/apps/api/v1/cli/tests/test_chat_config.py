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
    return waffle.switch_is_active(SmarterWaffleSwitches.API_LOGGING) and waffle.switch_is_active(
        SmarterWaffleSwitches.PLUGIN_LOGGING
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
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)

        logger.debug("chat_config() raw response: %s", response)

        # pylint: disable=W0612
        expected_output = {
            "data": {
                "session_key": "a506bd92f58682c8280d756066f18ce2d2a3381b7fb7bb13fbe54dd5d114d24f",
                "sandbox_mode": False,
                "debug_mode": True,
                "chatbot": {
                    "id": 372,
                    "url_chatbot": "http://localhost:8000/api/v1/chatbots/372/chat/",
                    "account": {"accountNumber": "7154-0706-7820"},
                    "default_system_role": "The current date/time is Wednesday, 2026-01-07T23:25:02+0000\nYou are a helpful chatbot. When given the opportunity to utilize function calling, you should always do so. This will allow you to provide the best possible responses to the user. If you are unable to provide a response, you should prompt the user for more information. If you are still unable to provide a response, you should inform the user that you are unable to help them at this time.",
                    "created_at": "2026-01-07T23:25:02.548999Z",
                    "updated_at": "2026-01-07T23:25:02.549006Z",
                    "name": "smarter_test_base_364beb79380074c9",
                    "description": "Test ChatBot",
                    "version": "1.0.0",
                    "annotations": [],
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
                        "name": "",
                        "description": "",
                        "version": "",
                        "annotations": None,
                        "session_key": "",
                        "ip_address": "",
                        "user_agent": "",
                        "url": "",
                        "account": None,
                        "chatbot": None,
                    },
                    "chat_history": [],
                    "chat_tool_call_history": [],
                    "chat_plugin_usage_history": [],
                    "chatbot_request_history": [],
                    "plugin_selector_history": [],
                },
                "meta_data": {
                    "account": {"accountNumber": "7154-0706-7820"},
                    "api_host": "api.localhost:8000",
                    "api_subdomain": "testserver",
                    "api_token": "****c10e",
                    "auth_header": "Token 5d65****",
                    "cache_key": "887e673f7be35b7190caf0934bcdc09c2286f9f941799310444fcd70d5e3971a",
                    "chatbot": {
                        "id": 372,
                        "created_at": "2026-01-07T23:25:02.548999Z",
                        "updated_at": "2026-01-07T23:25:02.549006Z",
                        "name": "smarter_test_base_364beb79380074c9",
                        "description": "Test ChatBot",
                        "version": "1.0.0",
                        "annotations": [],
                        "account": {"accountNumber": "7154-0706-7820"},
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
                        "tags": [],
                        "tagged_items": [],
                        "url_chatbot": "http://localhost:8000/api/v1/chatbots/372/chat/",
                    },
                    "chatbot_custom_domain": None,
                    "chatbot_id": None,
                    "chatbot_name": "smarter_test_base_364beb79380074c9",
                    "class_name": "ChatBotHelper",
                    "data": {},
                    "domain": "testserver",
                    "environment_api_domain": "api.localhost:8000",
                    "ip_address": "127.0.0.1",
                    "is_authentication_required": False,
                    "is_chatbot": True,
                    "is_chatbot_cli_api_url": True,
                    "is_chatbot_named_url": False,
                    "is_chatbot_sandbox_url": False,
                    "is_chatbot_smarter_api_url": False,
                    "is_chatbothelper_ready": True,
                    "is_config": True,
                    "is_custom_domain": False,
                    "is_dashboard": False,
                    "is_default_domain": False,
                    "is_deployed": False,
                    "is_environment_root_domain": False,
                    "is_smarter_api": True,
                    "is_workbench": False,
                    "name": "smarter_test_base_364beb79380074c9",
                    "params": {"uid": "198f94309784a5a8465ae2f99f29d350319218aa7da93f2bc97028ade398afd3"},
                    "parsed_url": "ParseResult(scheme='http', netloc='testserver', path='/api/v1/cli/chat/config/smarter_test_base_364beb79380074c9/', params='', query='', fragment='')",
                    "path": "/api/v1/cli/chat/config/smarter_test_base_364beb79380074c9/",
                    "qualified_request": True,
                    "ready": True,
                    "request": True,
                    "rfc1034_compliant_name": "smarter-test-base-364beb79380074c9",
                    "root_domain": "testserver",
                    "session_key": "a506bd92f58682c8280d756066f18ce2d2a3381b7fb7bb13fbe54dd5d114d24f",
                    "subdomain": None,
                    "timestamp": "2026-01-07T23:25:02.909556",
                    "uid": "198f94309784a5a8465ae2f99f29d350319218aa7da93f2bc97028ade398afd3",
                    "unique_client_string": "7154-0706-7820.http://testserver/api/v1/cli/chat/config/smarter_test_base_364beb79380074c9/.user_agent.127.0.0.1.2026-01-07T23:25:02.909556",
                    "url": "http://testserver/api/v1/cli/chat/config/smarter_test_base_364beb79380074c9/",
                    "url_original": "http://testserver/api/v1/cli/chat/config/smarter_test_base_364beb79380074c9/",
                    "url_path_parts": ["api", "v1", "cli", "chat", "config", "smarter_test_base_364beb79380074c9"],
                    "user": {
                        "username": "test_admin_user_8a37f9ec927e391e",
                        "email": "test-admin-8a37f9ec927e391e@mail.com",
                    },
                    "user_agent": "user_agent",
                    "user_profile": {
                        "user": {
                            "username": "test_admin_user_8a37f9ec927e391e",
                            "email": "test-admin-8a37f9ec927e391e@mail.com",
                        },
                        "account": {"accountNumber": "7154-0706-7820"},
                    },
                },
                "plugins": {"meta_data": {"total_plugins": 0, "plugins_returned": 0}, "plugins": []},
            },
            "api": "smarter.sh/v1",
            "thing": "ChatConfig",
            "metadata": {"key": "8dc3217f96ff966ba44adb4493f58d523d9680be2527a0854b5f424534046354"},
        }

        self.validate_response(response)
        data = response[SmarterJournalApiResponseKeys.DATA]
        self.validate_data(data=data)
        session_key = data[SMARTER_CHAT_SESSION_KEY_NAME]

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

        metadata = response[SmarterJournalApiResponseKeys.METADATA]
        metadata[SCLIResponseMetadata.COMMAND] = SmarterJournalCliCommands.CHAT_CONFIG.value

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
