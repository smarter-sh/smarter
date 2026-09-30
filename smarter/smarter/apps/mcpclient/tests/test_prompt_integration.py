"""
Test that an LLMClient's MCPClients' tools and instructions are injected into its prompts.

This tests :meth:`OpenAISmarterClient.handle_mcp_clients` and the MCP branch of
:meth:`OpenAISmarterClient.process_tool_call`, without calling an LLM.

.. note::

    **Experimental.** The MCPClient was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import secrets
from unittest import mock

from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCall,
    Function,
)
from pydantic import SecretStr

from smarter.apps.llmclient.models import LLMClient, LLMClientMCPClients
from smarter.apps.mcpclient.connection import MCPServerConnection
from smarter.apps.mcpclient.exceptions import SmarterMCPClientConnectionError
from smarter.apps.prompt.models import Prompt
from smarter.apps.provider.models import Provider
from smarter.apps.provider.services.text_completion.const import OpenAIMessageKeys
from smarter.apps.provider.services.text_completion.lib.internal_keys import (
    _InternalKeys,
)
from smarter.apps.provider.services.text_completion.lib.openai_compatible_chat_provider import (
    OpenAISmarterClient,
)
from smarter.lib import json

from .base_classes import TEST_SERVER_INSTRUCTIONS, MCPClientTestBase, mock_mcp_server

SYSTEM_ROLE = "You are a helpful assistant."


class TestMCPClientPromptIntegration(MCPClientTestBase):
    """Test the injection of MCP tools into prompts."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.llmclient = LLMClient.objects.create(
            name="test_mcpclient_prompt_llmclient",
            user_profile=cls.user_profile,
            description="Test LLMClient",
            version="1.0.0",
            deployed=False,
            app_name="Smarter",
        )
        cls.prompt = Prompt.objects.create(
            session_key=secrets.token_hex(32),
            user_profile=cls.user_profile,
            llmclient=cls.llmclient,
            ip_address="192.1.1.1",
            user_agent="unit test",
            url="https://www.test.com",
        )

    @classmethod
    def tearDownClass(cls):
        cls.prompt.delete()
        cls.llmclient.delete()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.link = LLMClientMCPClients.objects.create(llmclient=self.llmclient, mcpclient=self.mcpclient)
        self.addCleanup(LLMClientMCPClients.objects.filter(llmclient=self.llmclient).delete)

    def provider(self) -> OpenAISmarterClient:
        """Return a chat provider for the test prompt, with a system and a user message."""
        provider_orm = Provider.objects.filter(name="openai").first()
        if provider_orm is None:
            self.skipTest("the platform's openai Provider does not exist.")
        provider = OpenAISmarterClient(
            provider=provider_orm,
            provider_name="openai",
            base_url="https://api.example.com/v1/",
            api_key=SecretStr("sk-test"),
            default_model="gpt-4o-mini",
        )
        provider.prompt = self.prompt
        provider.messages = [
            {
                OpenAIMessageKeys.MESSAGE_ROLE_KEY: OpenAIMessageKeys.SYSTEM_MESSAGE_KEY,
                OpenAIMessageKeys.MESSAGE_CONTENT_KEY: SYSTEM_ROLE,
            },
            {
                OpenAIMessageKeys.MESSAGE_ROLE_KEY: OpenAIMessageKeys.USER_MESSAGE_KEY,
                OpenAIMessageKeys.MESSAGE_CONTENT_KEY: "Add 2 and 3.",
            },
        ]
        return provider

    def test_mcpclients_for(self):
        """Test that LLMClientMCPClients.mcpclients_for() returns the active MCPClients, in order of priority."""
        second = self.new_mcpclient("test_mcpclient_second", priority=1)
        inactive = self.new_mcpclient("test_mcpclient_inactive", is_active=False)
        LLMClientMCPClients.objects.create(llmclient=self.llmclient, mcpclient=second)
        LLMClientMCPClients.objects.create(llmclient=self.llmclient, mcpclient=inactive)
        self.assertEqual(LLMClientMCPClients.mcpclients_for(self.llmclient), [second, self.mcpclient])

    def test_tools_are_added(self):
        """Test that the MCPClient's tools are added to the request, and its instructions to the system prompt."""
        provider = self.provider()
        with mock_mcp_server():
            provider.handle_mcp_clients()
        function_names = [tool["function"]["name"] for tool in provider.tools]
        self.assertIn(f"mcp{self.mcpclient.id}_echo", function_names)
        self.assertIn(f"mcp{self.mcpclient.id}_add_numbers", function_names)
        self.assertNotIn(f"mcp{self.mcpclient.id}_secret_admin_tool", function_names)
        self.assertIn(f"mcp{self.mcpclient.id}_echo", provider.available_functions)
        system = provider.messages[0][OpenAIMessageKeys.MESSAGE_CONTENT_KEY]
        self.assertTrue(system.startswith(SYSTEM_ROLE))
        self.assertIn(TEST_SERVER_INSTRUCTIONS, system)
        smarter_messages = [
            message[OpenAIMessageKeys.MESSAGE_CONTENT_KEY]
            for message in provider.messages
            if message[OpenAIMessageKeys.MESSAGE_ROLE_KEY] == OpenAIMessageKeys.SMARTER_MESSAGE_KEY
        ]
        self.assertTrue(any(self.mcpclient.name in message for message in smarter_messages))

    def test_no_mcpclients(self):
        """Test that an LLMClient without MCPClients is unchanged."""
        LLMClientMCPClients.objects.filter(llmclient=self.llmclient).delete()
        provider = self.provider()
        provider.handle_mcp_clients()
        self.assertIsNone(provider.mcp_toolkit)
        self.assertIsNone(provider.tools)
        self.assertEqual(provider.messages[0][OpenAIMessageKeys.MESSAGE_CONTENT_KEY], SYSTEM_ROLE)

    def test_unreachable_server(self):
        """Test that an unreachable MCP server is skipped, and reported in a Smarter error message."""
        provider = self.provider()
        with mock.patch.object(
            MCPServerConnection, "discover", side_effect=SmarterMCPClientConnectionError("server is down")
        ):
            provider.handle_mcp_clients()
        self.assertFalse(provider.tools)
        errors = [
            message[OpenAIMessageKeys.MESSAGE_CONTENT_KEY]
            for message in provider.messages
            if message[OpenAIMessageKeys.MESSAGE_ROLE_KEY] == OpenAIMessageKeys.SMARTER_ERROR_KEY
        ]
        self.assertTrue(any("server is down" in error for error in errors))

    def test_process_tool_call(self):
        """Test that the LLM's call of an MCP tool runs on the MCP server, and its result is appended as a tool message."""
        provider = self.provider()
        with mock_mcp_server():
            provider.handle_mcp_clients()
            provider.serialized_tool_calls = []
            tool_call = ChatCompletionMessageToolCall(
                id="call_1",
                type="function",
                function=Function(name=f"mcp{self.mcpclient.id}_add_numbers", arguments=json.dumps({"a": 2, "b": 3})),
            )
            with mock.patch.object(OpenAISmarterClient, "handle_tool_called") as handle_tool_called:
                provider.process_tool_call(tool_call)
        tool_message = provider.messages[-1]
        self.assertEqual(tool_message[OpenAIMessageKeys.MESSAGE_ROLE_KEY], OpenAIMessageKeys.TOOL_MESSAGE_KEY)
        self.assertEqual(tool_message[OpenAIMessageKeys.MESSAGE_CONTENT_KEY], "5")
        self.assertEqual(tool_message[OpenAIMessageKeys.TOOL_CALL_ID], "call_1")
        serialized = provider.serialized_tool_calls[0]
        self.assertEqual(serialized[_InternalKeys.SMARTER_MCPCLIENT_KEY]["name"], self.mcpclient.name)
        self.assertEqual(serialized[_InternalKeys.SMARTER_MCPCLIENT_KEY]["tool"], "add_numbers")
        # the charge includes the MCPClient
        self.assertEqual(
            handle_tool_called.call_args.kwargs["extra_resource_locators"], [self.mcpclient.record_locator]
        )
