"""
Test that an LLMClient's guardrails protect its prompts.

This tests :meth:`OpenAISmarterClient.handle_input_guardrails`,
:meth:`OpenAISmarterClient.handle_output_guardrails`, and, with a mocked LLM, the handler's
response to a blocked message.

.. note::

    **Experimental.** The Guardrail was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import secrets
import time
from unittest import mock

from openai.types.chat.chat_completion import ChatCompletion, Choice
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.completion_usage import CompletionUsage
from pydantic import SecretStr

from smarter.apps.guardrail.services import GuardrailBlockedError
from smarter.apps.llmclient.models import LLMClient, LLMClientGuardrails
from smarter.apps.prompt.models import Prompt
from smarter.apps.provider.models import Provider
from smarter.apps.provider.services.text_completion.const import OpenAIMessageKeys
from smarter.apps.provider.services.text_completion.lib.openai_compatible_chat_provider import (
    BLOCKED_MESSAGE_PLACEHOLDER,
    OpenAISmarterClient,
)

from .base_classes import GuardrailTestBase, get_test_data

PROMPTS = get_test_data("prompts.yaml")
SYSTEM_ROLE = "You are a helpful assistant."
CREATE_PATCH = (
    "smarter.apps.provider.services.text_completion.lib.openai_compatible_chat_provider.openai.chat.completions.create"
)
# Celery tasks that write rows that refer to the prompt, or charge for it. Celery is not eager in tests, so
# unpatched, they run in the live worker, which can write a row while tearDownClass deletes the prompt.
PROMPT_TASK_PATCHES = (
    "smarter.apps.prompt.receivers.create_prompt_history",
    "smarter.apps.provider.services.text_completion.lib.mixins.create_prompt_tool_call_history",
    "smarter.apps.provider.services.text_completion.lib.mixins.create_prompt_plugin_usage",
    "smarter.apps.provider.services.text_completion.lib.mixins.create_charge",
)


def completion(content: str) -> ChatCompletion:
    """Return an LLM's chat completion with a reply."""
    return ChatCompletion(
        id="test",
        model="gpt-6-luna",
        choices=[
            Choice(message=ChatCompletionMessage(role="assistant", content=content), finish_reason="stop", index=0)
        ],
        usage=CompletionUsage(prompt_tokens=10, completion_tokens=10, total_tokens=20),
        created=int(time.time()),
        object="chat.completion",
    )


class TestGuardrailPromptIntegration(GuardrailTestBase):
    """Test the protection of prompts by guardrails."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        for target in PROMPT_TASK_PATCHES:
            patcher = mock.patch(target)
            patcher.start()
            cls.addClassCleanup(patcher.stop)
        cls.llmclient = LLMClient.objects.create(
            name="test_guardrail_prompt_llmclient", user_profile=cls.user_profile, deployed=False, app_name="Smarter"
        )
        cls.prompt = Prompt.objects.create(
            session_key=secrets.token_hex(32),
            user_profile=cls.user_profile,
            llmclient=cls.llmclient,
            ip_address="192.1.1.1",
            user_agent="unit test",
            url="https://www.test.com",
        )
        cls.redact = cls.create_guardrail(
            "test_prompt_redact",
            stage="both",
            category="pii",
            strategy="detector",
            config={"detectors": ["credit_card", "email"]},
            action="redact",
            priority=1,
        )
        cls.block = cls.create_guardrail("test_prompt_block", message="That was blocked.", priority=2)

    @classmethod
    def tearDownClass(cls):
        cls.prompt.delete()
        cls.llmclient.delete()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        for guardrail in (self.redact, self.block):
            LLMClientGuardrails.objects.create(llmclient=self.llmclient, guardrail=guardrail)
        self.addCleanup(LLMClientGuardrails.objects.filter(llmclient=self.llmclient).delete)

    def provider(self, user_text: str) -> OpenAISmarterClient:
        """Return a chat provider for the test prompt, with a system message and the user's message."""
        provider_orm = Provider.objects.filter(name="openai").first()
        if provider_orm is None:
            self.skipTest("the platform's openai Provider does not exist.")
        provider = OpenAISmarterClient(
            provider=provider_orm,
            provider_name="openai",
            base_url="https://api.example.com/v1/",
            api_key=SecretStr("sk-test"),
            default_model="gpt-6-luna",
        )
        provider.prompt = self.prompt
        provider.messages = [
            {
                OpenAIMessageKeys.MESSAGE_ROLE_KEY: OpenAIMessageKeys.SYSTEM_MESSAGE_KEY,
                OpenAIMessageKeys.MESSAGE_CONTENT_KEY: SYSTEM_ROLE,
            },
            {
                OpenAIMessageKeys.MESSAGE_ROLE_KEY: OpenAIMessageKeys.USER_MESSAGE_KEY,
                OpenAIMessageKeys.MESSAGE_CONTENT_KEY: user_text,
            },
        ]
        provider.input_text = user_text
        return provider

    def user_message(self, provider) -> str:
        """Return the provider's latest user message."""
        return [
            m[OpenAIMessageKeys.MESSAGE_CONTENT_KEY]
            for m in provider.messages
            if m[OpenAIMessageKeys.MESSAGE_ROLE_KEY] == OpenAIMessageKeys.USER_MESSAGE_KEY
        ][-1]

    def smarter_messages(self, provider) -> list[str]:
        """Return the provider's Smarter messages."""
        return [
            m[OpenAIMessageKeys.MESSAGE_CONTENT_KEY]
            for m in provider.messages
            if m[OpenAIMessageKeys.MESSAGE_ROLE_KEY] == OpenAIMessageKeys.SMARTER_MESSAGE_KEY
        ]

    def test_guardrails_for(self):
        """Test that LLMClientGuardrails.guardrails_for returns the active guardrails, in order of priority."""
        inactive = self.new_guardrail("test_prompt_inactive", is_active=False, priority=0)
        LLMClientGuardrails.objects.create(llmclient=self.llmclient, guardrail=inactive)
        self.assertEqual(LLMClientGuardrails.guardrails_for(self.llmclient), [self.redact, self.block])

    def test_input_redacted(self):
        """Test that the user's message is redacted before it is sent to the LLM, and the plugins see it redacted."""
        provider = self.provider(PROMPTS["pii"])
        provider.handle_input_guardrails()
        user = self.user_message(provider)
        self.assertEqual(user, "My card is [REDACTED], and my email is [REDACTED].")
        self.assertEqual(provider.input_text, user)
        self.assertEqual(provider.messages[0][OpenAIMessageKeys.MESSAGE_CONTENT_KEY], SYSTEM_ROLE)
        self.assertTrue(any("redacted" in m for m in self.smarter_messages(provider)))

    def test_input_blocked(self):
        """Test that a blocked user message raises GuardrailBlockedError, with the guardrail's message."""
        provider = self.provider("a forbidden question")
        with self.assertRaises(GuardrailBlockedError) as cm:
            provider.handle_input_guardrails()
        self.assertEqual(cm.exception.message, "That was blocked.")
        # the blocked message is replaced in the history, so that later prompts do not send it to the LLM
        self.assertEqual(self.user_message(provider), BLOCKED_MESSAGE_PLACEHOLDER)
        self.assertEqual(provider.input_text, BLOCKED_MESSAGE_PLACEHOLDER)

    def test_input_allowed(self):
        """Test that an allowed message is unchanged, and adds no Smarter message."""
        provider = self.provider(PROMPTS["benign"])
        provider.handle_input_guardrails()
        self.assertEqual(self.user_message(provider), PROMPTS["benign"])
        self.assertEqual(self.smarter_messages(provider), [])

    def test_no_guardrails(self):
        """Test that an LLMClient without guardrails has no pipeline."""
        LLMClientGuardrails.objects.filter(llmclient=self.llmclient).delete()
        provider = self.provider(PROMPTS["pii"])
        provider.handle_input_guardrails()
        self.assertIsNone(provider.guardrail_pipeline)
        response = completion(PROMPTS["pii"])
        self.assertIs(provider.handle_output_guardrails(response), response)

    def test_output_redacted(self):
        """Test that the LLM's reply is redacted."""
        provider = self.provider(PROMPTS["benign"])
        provider.handle_input_guardrails()
        response = provider.handle_output_guardrails(completion("Email jane.doe@example.com for help."))
        self.assertEqual(response.choices[0].message.content, "Email [REDACTED] for help.")

    def test_output_blocked(self):
        """Test that a blocked reply is replaced with the guardrail's message."""
        output_block = self.new_guardrail("test_prompt_output_block", stage="output", message="Reply withheld.")
        LLMClientGuardrails.objects.create(llmclient=self.llmclient, guardrail=output_block)
        provider = self.provider(PROMPTS["benign"])
        provider.handle_input_guardrails()
        response = provider.handle_output_guardrails(completion("a forbidden reply"))
        self.assertEqual(response.choices[0].message.content, "Reply withheld.")
        self.assertEqual(response.choices[0].finish_reason, "content_filter")

    def test_handler_blocked_does_not_call_the_llm(self):
        """Test that the handler answers a blocked message with the guardrail's message, without calling the LLM."""
        provider = self.provider("a forbidden question")
        data = {
            "session_key": self.prompt.session_key,
            "messages": [
                {"role": "system", "content": SYSTEM_ROLE},
                {"role": "user", "content": "a forbidden question"},
            ],
        }
        with mock.patch(CREATE_PATCH) as create:
            response = provider.handler(self.user_profile, self.prompt, data)
        create.assert_not_called()
        self.assertIn("That was blocked.", str(response))
        self.assertIn("content_filter", str(response))
        self.assertNotIn("a forbidden question", str(response))

    def test_handler_redacts_before_calling_the_llm(self):
        """Test that the LLM receives the redacted message, and the user receives the redacted reply."""
        provider = self.provider(PROMPTS["pii"])
        data = {
            "session_key": self.prompt.session_key,
            "messages": [{"role": "system", "content": SYSTEM_ROLE}, {"role": "user", "content": PROMPTS["pii"]}],
        }
        with mock.patch(CREATE_PATCH, return_value=completion("I emailed jane.doe@example.com.")) as create:
            response = provider.handler(self.user_profile, self.prompt, data)
        sent = str(create.call_args.kwargs["messages"])
        self.assertNotIn("4111 1111 1111 1111", sent)
        self.assertNotIn("jane.doe@example.com", sent)
        self.assertNotIn("jane.doe@example.com", str(response.get("body", response)))
