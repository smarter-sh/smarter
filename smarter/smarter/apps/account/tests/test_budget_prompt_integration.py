"""
Test that budgets are enforced on prompts: an exceeded budget is answered in the chat window, without calling the LLM.

This tests :meth:`OpenAISmarterClient.authorize_budgets` and :meth:`OpenAISmarterClient.tool_budget_refusal`,
with a mocked LLM.
"""

import secrets
import time
from decimal import Decimal
from unittest import mock

from openai.types.chat.chat_completion import ChatCompletion, Choice
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.completion_usage import CompletionUsage
from pydantic import SecretStr

from smarter.apps.account.models import Budget, Charge, ChargeTypes
from smarter.apps.account.models.budget import get_resource_lock_message
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.llmclient.models import LLMClient
from smarter.apps.plugin.models import PluginMeta
from smarter.apps.prompt.models import Prompt
from smarter.apps.provider.models import Provider
from smarter.apps.provider.services.text_completion.lib.openai_compatible_chat_provider import (
    OpenAISmarterClient,
)
from smarter.common.conf import smarter_settings
from smarter.lib import json

SYSTEM_ROLE = "You are a helpful assistant."
CREATE_PATCH = (
    "smarter.apps.provider.services.text_completion.lib.openai_compatible_chat_provider.openai.chat.completions.create"
)
CHARGE_PATCH = "smarter.apps.provider.services.text_completion.lib.mixins.create_charge"
# Celery tasks that write rows that refer to the prompt. Celery is not eager in tests, so unpatched,
# they run in the live worker, which can write a row while tearDownClass deletes the prompt.
PROMPT_TASK_PATCHES = (
    "smarter.apps.prompt.receivers.create_prompt_history",
    "smarter.apps.provider.services.text_completion.lib.mixins.create_prompt_tool_call_history",
    "smarter.apps.provider.services.text_completion.lib.mixins.create_prompt_plugin_usage",
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


class TestBudgetPromptIntegration(TestAccountMixin):
    """Test the enforcement of budgets on prompts."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        for target in PROMPT_TASK_PATCHES:
            patcher = mock.patch(target)
            patcher.start()
            cls.addClassCleanup(patcher.stop)
        cls.llmclient = LLMClient.objects.create(
            name="test_budget_prompt_llmclient", user_profile=cls.user_profile, deployed=False, app_name="Smarter"
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
        self.budget = Budget.objects.create(
            name=f"test_budget_prompt_{self.hash_suffix}",
            periodic_limit=Decimal("1.00"),
            message="This assistant has used its budget for the month.",
        )

    def tearDown(self):
        locators = list(self.budget.constraints.values_list("resource_locator", flat=True))  # type: ignore[attr-defined]
        self.budget.delete()
        Charge.objects.filter(resource_locator__in=locators, total_cost=Decimal("5.00")).delete()
        for locator in locators:
            get_resource_lock_message.invalidate(locator)
        super().tearDown()

    def exceed(self, resource):
        """Attach the budget to a resource, and spend more than it."""
        self.budget.attach(resource)
        Charge.objects.create(
            resource_locator=resource.record_locator,
            charge_type=ChargeTypes.PROMPT_COMPLETION.value,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            total_cost=Decimal("5.00"),
        )

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

    def data(self) -> dict:
        return {
            "session_key": self.prompt.session_key,
            "messages": [{"role": "system", "content": SYSTEM_ROLE}, {"role": "user", "content": "Hello"}],
        }

    def test_exceeded_llmclient_budget_is_answered_in_the_chat(self):
        """Test that the handler answers with the budget's message, without calling the LLM."""
        self.exceed(self.llmclient)
        provider = self.provider()
        with mock.patch(CREATE_PATCH) as create, mock.patch(CHARGE_PATCH):
            response = provider.handler(self.user_profile, self.prompt, self.data())
        create.assert_not_called()
        self.assertIn("This assistant has used its budget for the month.", str(response))
        self.assertIn("budget_exceeded", str(response))

    def test_exceeded_user_budget_is_answered_in_the_chat(self):
        """Test that a budget attached to the person who is chatting also stops the prompt."""
        self.exceed(self.user_profile)
        provider = self.provider()
        with mock.patch(CREATE_PATCH) as create, mock.patch(CHARGE_PATCH):
            response = provider.handler(self.user_profile, self.prompt, self.data())
        create.assert_not_called()
        self.assertIn("This assistant has used its budget for the month.", str(response))

    def test_within_budget_calls_the_llm(self):
        """Test that a budget that is not exceeded does not stop the prompt."""
        self.budget.attach(self.llmclient)
        provider = self.provider()
        with mock.patch(CREATE_PATCH, return_value=completion("Hi there.")) as create, mock.patch(CHARGE_PATCH):
            response = provider.handler(self.user_profile, self.prompt, self.data())
        create.assert_called_once()
        self.assertIn("Hi there.", str(response))

    def test_tool_budget_refusal(self):
        """Test that a plugin whose budget is exceeded is not called, and the LLM is told why."""
        plugin_meta = PluginMeta.objects.filter(user_profile=self.user_profile).first() or PluginMeta.objects.first()
        if plugin_meta is None:
            self.skipTest("no plugin exists.")
        function_name = f"{smarter_settings.function_calling_identifier_prefix}_{str(plugin_meta.id).zfill(10)}"  # type: ignore[attr-defined]
        provider = self.provider()
        self.assertIsNone(provider.tool_budget_refusal(function_name))
        self.exceed(plugin_meta)
        refusal = json.loads(provider.tool_budget_refusal(function_name))  # type: ignore[arg-type]
        self.assertEqual(refusal["error"], "budget_exceeded")
        self.assertEqual(refusal["message"], "This assistant has used its budget for the month.")
        self.assertIsNone(provider.tool_budget_refusal("calculator"))
