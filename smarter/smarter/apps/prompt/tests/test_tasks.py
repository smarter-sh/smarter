"""
Test the prompt app's Celery tasks.

The tasks are called directly, which runs
them synchronously, in this process.
"""

import datetime
import json
import secrets
from unittest.mock import patch

from django.db import DataError
from django.db.models import QuerySet
from django.utils import timezone

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.llmclient.models import LLMClient
from smarter.apps.llmtool.models import PluginMeta
from smarter.apps.prompt.models import (
    Prompt,
    PromptHistory,
    PromptPluginUsage,
    PromptToolCall,
)
from smarter.apps.prompt.models.prompt import get_cached_prompt_by_session_key
from smarter.apps.prompt.tasks import (
    aggregate_prompt_history,
    create_prompt,
    create_prompt_history,
    create_prompt_plugin_usage,
    create_prompt_tool_call_history,
    purge_prompt_history,
)
from smarter.common.exceptions import SmarterValueError
from smarter.lib.django.models import TimestampedModel
from smarter.lib.typing import SmarterDictType

MISSING_ID = 999999999

# The tests share the dev database, so the purge's cutoff is far older than any real row: it deletes only the
# rows that the tests backdate.
KEEP_DAYS = 10000


class TestPromptTasks(TestAccountMixin):
    """Test the prompt history tasks."""

    llmclient: LLMClient
    prompt: Prompt

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
        assert history.messages is not None
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

    def test_create_prompt_tool_call_history_long_arguments(self):
        """Arguments longer than 255 characters, e.g. an MCP web search, are saved in full."""
        query = "x" * 1000
        function_args = json.dumps({"query": query})
        create_prompt_tool_call_history(self.prompt.id, None, "web_search", function_args, {}, {})
        tool_call = PromptToolCall.objects.filter(prompt=self.prompt).latest("id")
        self.addCleanup(tool_call.delete)
        self.assertEqual(tool_call.function_name, "web_search")
        self.assertEqual(tool_call.function_args, function_args)

    def test_tasks_do_not_retry_data_errors(self):
        """A DataError fails the same way on every retry, so no task retries it."""
        tasks = [
            create_prompt_history,
            aggregate_prompt_history,
            create_prompt,
            create_prompt_tool_call_history,
            create_prompt_plugin_usage,
        ]
        for task in tasks:
            with self.subTest(task=task.name):
                # Celery sets dont_autoretry_for from the task decorator's options; its stubs don't declare it.
                self.assertIn(DataError, task.dont_autoretry_for)  # type: ignore[attr-defined]

    def test_create_prompt_tool_call_history_errors(self):
        with self.assertRaises(SmarterValueError):
            create_prompt_tool_call_history(MISSING_ID, None, "f", "{}", {}, {})
        with self.assertRaises(SmarterValueError):
            create_prompt_tool_call_history(self.prompt.id, MISSING_ID, "f", "{}", {}, {})
        self.assertFalse(PromptToolCall.objects.filter(prompt=self.prompt, function_name="f").exists())

    def test_create_prompt_plugin_usage_errors(self):
        cases: list[SmarterDictType] = [
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


class TestPurgePromptHistory(TestAccountMixin):
    """Test purge_prompt_history()."""

    llmclient: LLMClient
    plugin: PluginMeta

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.llmclient = LLMClient.objects.create(
            name=f"test_purge_prompt_history_{cls.hash_suffix}", user_profile=cls.user_profile
        )
        cls.plugin = PluginMeta.objects.create(
            name=f"test_purge_prompt_history_{cls.hash_suffix}", user_profile=cls.user_profile, plugin_class="static"
        )

    @classmethod
    def tearDownClass(cls):
        Prompt.objects.filter(llmclient=cls.llmclient).delete()
        cls.plugin.delete()
        cls.llmclient.delete()
        super().tearDownClass()

    @staticmethod
    def backdate(model: type[TimestampedModel], pk: int, days_old: int) -> None:
        """Set a row's created_at to ``days_old`` days ago."""
        created_at = timezone.now() - datetime.timedelta(days=days_old)
        model._default_manager.filter(pk=pk).update(created_at=created_at)

    def session(self, days_old: int = 0) -> Prompt:
        """Create a Prompt (a chat session), ``days_old`` days old."""
        prompt = Prompt.objects.create(
            session_key=f"test_purge_prompt_history_{secrets.token_urlsafe(16)}",
            llmclient=self.llmclient,
            user_profile=self.user_profile,
            url="https://localhost:9357/test-purge-prompt-history",
            ip_address="192.1.1.1",
            user_agent="unittest",
        )
        self.addCleanup(Prompt.objects.filter(pk=prompt.pk).delete)
        self.backdate(Prompt, prompt.pk, days_old)
        return prompt

    def history(self, prompt: Prompt, days_old: int) -> PromptHistory:
        """Create a PromptHistory row of ``prompt``, ``days_old`` days old."""
        row = PromptHistory.objects.create(prompt=prompt, request={}, response={}, messages=[])
        self.backdate(PromptHistory, row.pk, days_old)
        return row

    def tool_call(self, prompt: Prompt, days_old: int) -> PromptToolCall:
        """Create a PromptToolCall row of ``prompt``, ``days_old`` days old."""
        row = PromptToolCall.objects.create(prompt=prompt, function_name="get_weather", function_args="{}")
        self.backdate(PromptToolCall, row.pk, days_old)
        return row

    def plugin_usage(self, prompt: Prompt, days_old: int) -> PromptPluginUsage:
        """Create a PromptPluginUsage row of ``prompt``, ``days_old`` days old."""
        row = PromptPluginUsage.objects.create(prompt=prompt, plugin=self.plugin, input_text="hi")
        self.backdate(PromptPluginUsage, row.pk, days_old)
        return row

    @staticmethod
    def ids(rows: QuerySet) -> set[int]:
        """Return the ids of ``rows``."""
        pks = rows.values_list("pk", flat=True)
        return set(pks)

    def test_old_rows_of_an_active_session(self):
        """A session in use keeps its recent rows, and loses those older than the setting."""
        prompt = self.session(KEEP_DAYS + 1)
        recent_history = self.history(prompt, KEEP_DAYS - 1)
        self.history(prompt, KEEP_DAYS + 1)
        recent_tool_call = self.tool_call(prompt, KEEP_DAYS - 1)
        self.tool_call(prompt, KEEP_DAYS + 1)
        recent_plugin_usage = self.plugin_usage(prompt, KEEP_DAYS - 1)
        self.plugin_usage(prompt, KEEP_DAYS + 1)

        with patch("smarter.apps.prompt.tasks.smarter_settings") as settings:
            settings.prompt_history_max_age = KEEP_DAYS
            deleted = purge_prompt_history()

        self.assertGreaterEqual(deleted["PromptHistory"], 1)
        self.assertGreaterEqual(deleted["PromptToolCall"], 1)
        self.assertGreaterEqual(deleted["PromptPluginUsage"], 1)
        self.assertTrue(Prompt.objects.filter(pk=prompt.pk).exists())
        self.assertEqual(self.ids(PromptHistory.objects.filter(prompt=prompt)), {recent_history.pk})
        self.assertEqual(self.ids(PromptToolCall.objects.filter(prompt=prompt)), {recent_tool_call.pk})
        self.assertEqual(self.ids(PromptPluginUsage.objects.filter(prompt=prompt)), {recent_plugin_usage.pk})

    def test_idle_session(self):
        """A session older than the cutoff, whose rows are all older, is deleted with its rows."""
        prompt = self.session(KEEP_DAYS + 2)
        self.history(prompt, KEEP_DAYS + 1)
        self.tool_call(prompt, KEEP_DAYS + 1)
        self.plugin_usage(prompt, KEEP_DAYS + 1)
        empty = self.session(KEEP_DAYS + 1)

        deleted = purge_prompt_history(days=KEEP_DAYS)

        self.assertGreaterEqual(deleted["Prompt"], 2)
        self.assertFalse(Prompt.objects.filter(pk__in=[prompt.pk, empty.pk]).exists())

    def test_new_session_without_history(self):
        """A session newer than the cutoff is kept, even before its first prompt."""
        prompt = self.session(KEEP_DAYS - 1)
        purge_prompt_history(days=KEEP_DAYS)
        self.assertTrue(Prompt.objects.filter(pk=prompt.pk).exists())

    def test_deleting_a_session_clears_its_cached_lookup(self):
        """An idle session is deleted with Prompt.delete(), so its cached lookup is gone too."""
        prompt = self.session(KEEP_DAYS + 1)
        self.assertEqual(get_cached_prompt_by_session_key(prompt.session_key).pk, prompt.pk)
        purge_prompt_history(days=KEEP_DAYS)
        with self.assertRaises(Prompt.DoesNotExist):
            get_cached_prompt_by_session_key(prompt.session_key)

    def test_batches(self):
        """More expired rows than one batch are all deleted."""
        prompt = self.session()
        for _ in range(5):
            self.history(prompt, KEEP_DAYS + 1)
        with patch("smarter.apps.prompt.tasks.PROMPT_HISTORY_PURGE_BATCH_SIZE", 2):
            deleted = purge_prompt_history(days=KEEP_DAYS)
        self.assertGreaterEqual(deleted["PromptHistory"], 5)
        self.assertEqual(self.ids(PromptHistory.objects.filter(prompt=prompt)), set())
