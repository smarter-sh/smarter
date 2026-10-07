"""Test :class:`smarter.apps.provider.services.text_completion.lib.mixins.ChatDbMixin` directly, with its Celery tasks patched."""

import secrets
from unittest.mock import patch

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.llmclient.models import LLMClient
from smarter.apps.prompt.models import Prompt, PromptHistory
from smarter.apps.provider.models import Provider
from smarter.apps.provider.services.text_completion.lib.mixins import ChatDbMixin
from smarter.common.const import SMARTER_CHAT_SESSION_KEY_NAME
from smarter.common.exceptions import SmarterValueError

MODULE = "smarter.apps.provider.services.text_completion.lib.mixins"


class TestChatDbMixin(TestAccountMixin):
    """Test the ChatDbMixin's prompt-backed querysets, provider lookup and record inserts."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        patcher = patch("smarter.apps.prompt.receivers.create_prompt_history")
        patcher.start()
        cls.addClassCleanup(patcher.stop)
        cls.llmclient = LLMClient.objects.create(
            name=f"test_chat_db_mixin_{cls.hash_suffix}", user_profile=cls.user_profile, deployed=False
        )
        cls.prompt = Prompt.objects.create(
            session_key=secrets.token_hex(32),
            user_profile=cls.user_profile,
            llmclient=cls.llmclient,
            ip_address="192.1.1.1",
            user_agent="unit test",
            url="https://www.test.com",
        )
        cls.provider = Provider.objects.create(
            name=f"test_chat_db_mixin_{cls.hash_suffix}",
            user_profile=cls.user_profile,
            base_url="https://api.example.com/v1/",
            is_active=True,
        )

    @classmethod
    def tearDownClass(cls):
        PromptHistory.objects.filter(prompt=cls.prompt).delete()
        cls.prompt.delete()
        cls.llmclient.delete()
        cls.provider.delete()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.tasks = {}
        for name in ("create_prompt_tool_call_history", "create_prompt_plugin_usage", "create_charge"):
            patcher = patch(f"{MODULE}.{name}")
            self.tasks[name] = patcher.start()
            self.addCleanup(patcher.stop)

    def mixin(self, **kwargs) -> ChatDbMixin:
        kwargs.setdefault("user_profile", self.user_profile)
        return ChatDbMixin(**kwargs)

    def test_ready_with_a_prompt(self):
        """The mixin is ready once it has a prompt, and stays ready."""
        mixin = self.mixin(prompt=self.prompt)
        self.assertTrue(mixin.ready)
        self.assertTrue(mixin.ready)
        self.assertEqual(mixin.prompt, self.prompt)

    def test_not_ready_without_a_prompt(self):
        """Without a prompt, the mixin isn't ready and its querysets are empty."""
        mixin = self.mixin()
        self.assertFalse(mixin.ready)
        self.assertFalse(mixin.db_chat_tool_call.exists())
        self.assertFalse(mixin.db_chat_plugin_usage.exists())
        self.assertIsNone(mixin.provider_name)

    def test_prompt_from_the_session_key(self):
        """A session key loads the prompt."""
        mixin = self.mixin(**{SMARTER_CHAT_SESSION_KEY_NAME: self.prompt.session_key})
        self.assertEqual(mixin.prompt.pk, self.prompt.pk)

    def test_prompt_setter_rejects_other_types(self):
        """The prompt setter only accepts a Prompt or None."""
        mixin = self.mixin(prompt=self.prompt)
        with self.assertRaises(SmarterValueError):
            mixin.prompt = "not a prompt"  # type: ignore[assignment]
        mixin.prompt = None  # type: ignore[assignment]
        self.assertIsNone(mixin.prompt)

    def test_querysets(self):
        """The prompt's tool calls and plugin usage are queried, and db_refresh() keeps the prompt."""
        mixin = self.mixin(prompt=self.prompt)
        self.assertFalse(mixin.db_chat_tool_call.exists())
        self.assertFalse(mixin.db_chat_plugin_usage.exists())
        mixin.db_refresh()
        self.assertEqual(mixin.prompt, self.prompt)

    def test_message_history(self):
        """The message history comes from the newest prompt history record, and is cached."""
        messages = [{"role": "user", "content": "hello"}]
        history = PromptHistory.objects.create(prompt=self.prompt, request={}, response={}, messages=messages)
        self.addCleanup(history.delete)
        mixin = self.mixin(prompt=self.prompt)
        self.assertEqual(mixin.db_message_history, messages)
        self.assertIs(mixin.db_message_history, mixin.db_message_history)

    def test_provider_given(self):
        """A provider passed in is used as is."""
        mixin = self.mixin(prompt=self.prompt, provider=self.provider)
        self.assertEqual(mixin.provider, self.provider)
        self.assertEqual(mixin.provider_name, self.provider.name)

    def test_provider_by_name(self):
        """The provider is looked up by name among the active providers the user can read."""
        mixin = self.mixin(prompt=self.prompt, provider_name=self.provider.name)
        self.assertEqual(mixin.provider, self.provider)
        self.assertEqual(mixin.provider_name, self.provider.name)
        missing = self.mixin(prompt=self.prompt, provider_name=f"no_such_provider_{self.hash_suffix}")
        self.assertIsNone(missing.provider)

    def test_insert_tool_call_and_plugin_usage(self):
        """Tool calls and plugin usage are queued as Celery tasks, and skipped without a prompt."""
        mixin = self.mixin(prompt=self.prompt)
        mixin.db_insert_chat_tool_call(function_name="get_current_weather", function_args={"location": "x"})
        self.tasks["create_prompt_tool_call_history"].delay.assert_called_once()
        mixin.db_insert_chat_plugin_usage(prompt=self.prompt, input_text="hello")
        self.tasks["create_prompt_plugin_usage"].delay.assert_called_once()

        no_prompt = self.mixin()
        no_prompt.db_insert_chat_tool_call(function_name="get_current_weather")
        no_prompt.db_insert_chat_plugin_usage(input_text="hello")
        self.tasks["create_prompt_tool_call_history"].delay.assert_called_once()
        self.tasks["create_prompt_plugin_usage"].delay.assert_called_once()

    def test_insert_charge(self):
        """A charge is queued for each resource locator, plus the user profile and account."""
        mixin = self.mixin(prompt=self.prompt)
        mixin.db_insert_charge(
            resource_locators=["llmclient:test"],
            charge_type="completion",
            completion_tokens=1,
            prompt_tokens=2,
            total_tokens=3,
        )
        self.assertEqual(self.tasks["create_charge"].delay.call_count, 3)

    def test_insert_charge_errors(self):
        """A charge needs resource locators and a prompt."""
        kwargs = {"charge_type": "completion", "completion_tokens": 1, "prompt_tokens": 2, "total_tokens": 3}
        with self.assertRaises(SmarterValueError):
            self.mixin(prompt=self.prompt).db_insert_charge(resource_locators=[], **kwargs)
        with self.assertRaises(SmarterValueError):
            self.mixin().db_insert_charge(resource_locators=["llmclient:test"], **kwargs)
        self.tasks["create_charge"].delay.assert_not_called()
