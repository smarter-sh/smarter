"""
Test that an LLMClient's extensions offer their tools to the LLM, and run the LLM's tool calls.

This tests :meth:`OpenAISmarterClient.handle_extensions` and the extension branch of
:meth:`OpenAISmarterClient.process_tool_call`, with a mocked LLM that calls the echo
fixture extension's tool.
"""

import secrets
import time
from unittest import mock

from openai.types.chat.chat_completion import ChatCompletion, Choice
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCall,
    Function,
)
from openai.types.completion_usage import CompletionUsage
from pydantic import SecretStr

from smarter.apps.llmclient.models import LLMClient, LLMClientExtensions
from smarter.apps.llmtool.extension.tests.mixins import ExtensionTestMixin
from smarter.apps.prompt.models import Prompt
from smarter.apps.provider.models import Provider
from smarter.apps.provider.services.text_completion.const import OpenAIMessageKeys
from smarter.apps.provider.services.text_completion.lib.internal_keys import (
    _InternalKeys,
)
from smarter.apps.provider.services.text_completion.lib.openai_compatible_chat_provider import (
    OpenAISmarterClient,
)

SYSTEM_ROLE = "You are a helpful assistant."
CREATE_PATCH = (
    "smarter.apps.provider.services.text_completion.lib.openai_compatible_chat_provider.openai.chat.completions.create"
)
# Celery tasks that write rows that refer to the prompt, or charge for it. See the guardrail prompt tests.
PROMPT_TASK_PATCHES = (
    "smarter.apps.prompt.receivers.create_prompt_history",
    "smarter.apps.provider.services.text_completion.lib.mixins.create_prompt_tool_call_history",
    "smarter.apps.provider.services.text_completion.lib.mixins.create_prompt_plugin_usage",
    "smarter.apps.provider.services.text_completion.lib.mixins.create_charge",
)


def completion(content: str = "", tool_calls=None) -> ChatCompletion:
    """Return an LLM's chat completion, with a reply or tool calls."""
    return ChatCompletion(
        id="test",
        model="gpt-6-luna",
        choices=[
            Choice(
                message=ChatCompletionMessage(role="assistant", content=content or None, tool_calls=tool_calls),
                finish_reason="tool_calls" if tool_calls else "stop",
                index=0,
            )
        ],
        usage=CompletionUsage(prompt_tokens=10, completion_tokens=10, total_tokens=20),
        created=int(time.time()),
        object="chat.completion",
    )


class TestExtensionPromptIntegration(ExtensionTestMixin):
    """Test an LLMClient's extensions in a prompt."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        for target in PROMPT_TASK_PATCHES:
            patcher = mock.patch(target)
            patcher.start()
            cls.addClassCleanup(patcher.stop)
        cls.llmclient = LLMClient.objects.create(
            name="test_extension_prompt_llmclient", user_profile=cls.user_profile, deployed=False, app_name="Smarter"
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

    def provider(self) -> OpenAISmarterClient:
        """Return a chat provider for the test prompt."""
        provider_orm = Provider.objects.filter(name="openai").first()
        if provider_orm is None:
            self.skipTest("the platform's openai Provider does not exist.")
        return OpenAISmarterClient(
            provider=provider_orm,
            provider_name="openai",
            base_url="https://api.example.com/v1/",
            api_key=SecretStr("sk-test"),
            default_model="gpt-6-luna",
        )

    def data(self, text: str) -> dict:
        """Return the request body of a prompt."""
        return {
            "session_key": self.prompt.session_key,
            "messages": [{"role": "system", "content": SYSTEM_ROLE}, {"role": "user", "content": text}],
        }

    def test_tool_call(self):
        """The LLM is offered the extension's tools, and its call to one is answered with the tool's result."""
        extension = self.enable_echo()
        LLMClientExtensions.objects.create(llmclient=self.llmclient, extension=extension)
        tool_call = ChatCompletionMessageToolCall(
            id="call_1", type="function", function=Function(name="ext_echo_echo", arguments='{"text": "banana"}')
        )
        provider = self.provider()
        with mock.patch(
            CREATE_PATCH, side_effect=[completion(tool_calls=[tool_call]), completion("hello banana")]
        ) as create:
            provider.handler(self.user_profile, self.prompt, self.data("Echo banana."))
        offered = [tool["function"]["name"] for tool in create.call_args_list[0].kwargs["tools"]]
        self.assertIn("ext_echo_echo", offered)
        second_request = create.call_args_list[1].kwargs["messages"]
        tool_messages = [m for m in second_request if m.get(OpenAIMessageKeys.MESSAGE_ROLE_KEY) == "tool"]
        self.assertIn("hello banana", tool_messages[0][OpenAIMessageKeys.MESSAGE_CONTENT_KEY])
        serialized = provider.serialized_tool_calls[0]  # type: ignore[index]
        self.assertEqual(
            serialized[_InternalKeys.SMARTER_EXTENSION_KEY],
            {"id": extension.pk, "slug": "echo", "version": "1.0.0", "tool": "echo"},
        )
        self.assertEqual(provider.tool_display_name("ext_echo_echo"), "echo")
        smarter_messages = [
            m.get(OpenAIMessageKeys.MESSAGE_CONTENT_KEY) for m in provider.messages if m.get("role") == "smarter"
        ]
        self.assertTrue(any("tools of these extensions: echo" in str(m) for m in smarter_messages))

    def test_disabled_extension_is_reported(self):
        """A disabled extension's tools are not offered, and the user is told why."""
        extension = self.install_echo()
        LLMClientExtensions.objects.create(llmclient=self.llmclient, extension=extension)
        provider = self.provider()
        with mock.patch(CREATE_PATCH, return_value=completion("ok")) as create:
            provider.handler(self.user_profile, self.prompt, self.data("Hi."))
        self.assertNotIn("tools", create.call_args.kwargs)
        errors = [
            m.get(OpenAIMessageKeys.MESSAGE_CONTENT_KEY) for m in provider.messages if m.get("role") == "smarter_error"
        ]
        self.assertTrue(any("could not use the echo extension: the extension is disabled" in str(m) for m in errors))

    def test_no_extensions(self):
        """An LLMClient without extensions has no extension toolkit."""
        provider = self.provider()
        provider.prompt = self.prompt
        provider.handle_extensions()
        self.assertIsNone(provider.extension_toolkit)
        provider._chat = None  # pylint: disable=protected-access
        provider.handle_extensions()
        self.assertIsNone(provider.extension_toolkit)
