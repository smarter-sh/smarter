"""
Test the prompt app's Celery tasks.

The tasks are called directly, which runs
them synchronously, in this process.
"""

import secrets

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.llmclient.models import LLMClient
from smarter.apps.prompt.models import Prompt, PromptHistory, PromptToolCall
from smarter.apps.prompt.tasks import (
    aggregate_prompt_history,
    create_prompt_history,
    create_prompt_plugin_usage,
    create_prompt_tool_call_history,
)
from smarter.common.exceptions import SmarterValueError

MISSING_ID = 999999999


class TestPromptTasks(TestAccountMixin):
    """Test the prompt history tasks."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.llmclient = LLMClient.objects.create(
            name=f"test_prompt_tasks_{cls.hash_suffix}", user_profile=cls.user_profile
        )
        cls.prompt = Prompt.objects.create(
            session_key=f"test_prompt_tasks_{secrets.token_urlsafe(16)}",
            llmclient=cls.llmclient,
            user_profile=cls.user_profile,
            url="https://localhost:9357/test-prompt-tasks",
            ip_address="192.1.1.1",
            user_agent="unittest",
        )

    @classmethod
    def tearDownClass(cls):
        cls.prompt.delete()
        cls.llmclient.delete()
        super().tearDownClass()

    def test_create_prompt_history(self):
        create_prompt_history(self.prompt.id, {"q": 1}, {"a": 2}, [{"role": "user", "content": "hi"}])
        history = PromptHistory.objects.filter(prompt=self.prompt).latest("id")
        self.addCleanup(history.delete)
        self.assertEqual(history.request, {"q": 1})
        self.assertEqual(history.response, {"a": 2})
        self.assertEqual(history.messages[0]["content"], "hi")

    def test_create_prompt_history_unknown_prompt(self):
        before = PromptHistory.objects.count()
        self.assertIsNone(create_prompt_history(MISSING_ID, {}, {}, []))
        self.assertEqual(PromptHistory.objects.count(), before)

    def test_aggregate_prompt_history(self):
        self.assertIsNone(aggregate_prompt_history())

    def test_create_prompt_tool_call_history(self):
        create_prompt_tool_call_history(self.prompt.id, None, "get_weather", '{"city": "Paris"}', {"q": 1}, {"a": 2})
        tool_call = PromptToolCall.objects.filter(prompt=self.prompt).latest("id")
        self.addCleanup(tool_call.delete)
        self.assertIsNone(tool_call.plugin)
        self.assertEqual(tool_call.function_name, "get_weather")
        self.assertEqual(tool_call.response, {"a": 2})

    def test_create_prompt_tool_call_history_errors(self):
        with self.assertRaises(SmarterValueError):
            create_prompt_tool_call_history(MISSING_ID, None, "f", "{}", {}, {})
        with self.assertRaises(SmarterValueError):
            create_prompt_tool_call_history(self.prompt.id, MISSING_ID, "f", "{}", {}, {})
        self.assertFalse(PromptToolCall.objects.filter(prompt=self.prompt, function_name="f").exists())

    def test_create_prompt_plugin_usage_errors(self):
        cases = [
            {},
            {"prompt_id": self.prompt.id},
            {"prompt_id": self.prompt.id, "plugin_id": MISSING_ID},
            {"prompt_id": MISSING_ID, "plugin_id": MISSING_ID, "input_text": "hi"},
            {"prompt_id": self.prompt.id, "plugin_id": MISSING_ID, "input_text": "hi"},
        ]
        for kwargs in cases:
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(SmarterValueError):
                    create_prompt_plugin_usage(**kwargs)
