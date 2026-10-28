"""Tests of smarter.apps.provider.services.text_completion.lib.prompt_cache, and the provider methods that use it."""

import datetime
import secrets
from http import HTTPStatus
from unittest.mock import MagicMock, patch

from openai.types.chat import ChatCompletion
from pydantic import SecretStr

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.llmclient.models import LLMClient
from smarter.apps.prompt.models import Prompt
from smarter.apps.provider.models import Provider
from smarter.apps.provider.services.text_completion.lib import (
    openai_compatible_chat_provider as provider_module,
)
from smarter.apps.provider.services.text_completion.lib import prompt_cache
from smarter.apps.provider.services.text_completion.lib.openai_compatible_chat_provider import (
    OpenAISmarterClient,
)
from smarter.apps.provider.services.text_completion.lib.prompt_cache import (
    CACHED_RESPONSE_ID_PREFIX,
    PromptCacheHit,
    PromptCacheKey,
    cache_prompt_response,
    claim_first_message,
    get_cached_prompt_response,
    message_digest,
    normalize_message,
)
from smarter.lib.typing import SmarterDictType
from smarter.lib.unittest.base_classes import SmarterTestBase

from .test_openai_compatible_chat_provider import CREATE_PATCH, PROMPT_TASK_PATCHES


def chat_completion(content: str = "Sunny, 21 degrees.", finish_reason: str = "stop") -> ChatCompletion:
    """Return a ChatCompletion with one message, and its token usage."""
    return ChatCompletion.model_validate(
        {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "created": 0,
            "model": "gpt-test",
            "choices": [
                {"index": 0, "finish_reason": finish_reason, "message": {"role": "assistant", "content": content}},
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }
    )


class TestPromptCache(SmarterTestBase):
    """Test the cache of the LLM's answers to the first message of a conversation."""

    def key(self, message: str = "What's the weather in Paris?", **fields) -> PromptCacheKey:
        values = {
            "llmclient_id": 1,
            "llmclient_updated_at": "2026-10-28T00:00:00+00:00",
            "provider": "openai",
            "model": "gpt-test",
            "temperature": 0.5,
            "max_completion_tokens": 256,
            "message": message_digest(message),
        }
        values.update(fields)
        return PromptCacheKey(**values)

    def setUp(self):
        super().setUp()
        # every test uses its own LLMClient id, so that none sees another's cached answers.
        self.llmclient_id = abs(hash(self.id())) % 1_000_000_000

    def test_normalize_message(self):
        """Case, whitespace and trailing punctuation don't change a message."""
        self.assertEqual(normalize_message("  What's the   Weather in PARIS?! "), "what's the weather in paris")
        self.assertEqual(message_digest("What's the weather in Paris?"), message_digest("what's the weather in paris"))
        self.assertNotEqual(message_digest("weather in Paris"), message_digest("weather in London"))
        self.assertEqual(len(message_digest("hello")), 64)

    def test_a_miss_returns_none(self):
        """A message whose answer is not cached returns None, and stores nothing."""
        key = self.key(llmclient_id=self.llmclient_id)
        self.assertIsNone(get_cached_prompt_response(key))
        self.assertIsNone(get_cached_prompt_response(key))

    def test_a_cached_answer_costs_no_tokens(self):
        """A cached answer is returned with zero tokens, and an id that says it was cached."""
        key = self.key(llmclient_id=self.llmclient_id)
        cache_prompt_response(key, chat_completion())
        cached = get_cached_prompt_response(self.key("what's the weather in paris", llmclient_id=self.llmclient_id))
        self.assertIsNotNone(cached)
        self.assertEqual(cached.choices[0].message.content, "Sunny, 21 degrees.")  # type: ignore[union-attr]
        self.assertEqual(cached.id, f"{CACHED_RESPONSE_ID_PREFIX}chatcmpl-test")  # type: ignore[union-attr]
        self.assertEqual(cached.usage.total_tokens, 0)  # type: ignore[union-attr]
        self.assertEqual(cached.usage.prompt_tokens, 0)  # type: ignore[union-attr]

    def test_an_answer_without_usage(self):
        """An answer that reports no usage is returned without usage."""
        key = self.key(llmclient_id=self.llmclient_id)
        cache_prompt_response(key, chat_completion().model_copy(update={"usage": None}))
        self.assertIsNone(get_cached_prompt_response(key).usage)  # type: ignore[union-attr]

    def test_the_key_includes_everything_that_changes_the_answer(self):
        """Another LLMClient, version of it, model, temperature or message has its own answer."""
        key = self.key(llmclient_id=self.llmclient_id)
        cache_prompt_response(key, chat_completion())
        for other in (
            self.key(llmclient_id=self.llmclient_id + 1),
            self.key(llmclient_id=self.llmclient_id, llmclient_updated_at="2026-10-29T00:00:00+00:00"),
            self.key(llmclient_id=self.llmclient_id, model="gpt-other"),
            self.key(llmclient_id=self.llmclient_id, temperature=0.9),
            self.key("What's the weather in London?", llmclient_id=self.llmclient_id),
        ):
            with self.subTest(other=other):
                self.assertIsNone(get_cached_prompt_response(other))

    def test_a_newer_answer_replaces_the_cached_one(self):
        """Caching an answer again replaces the cached answer."""
        key = self.key(llmclient_id=self.llmclient_id)
        cache_prompt_response(key, chat_completion("first"))
        cache_prompt_response(key, chat_completion("second"))
        self.assertEqual(get_cached_prompt_response(key).choices[0].message.content, "second")  # type: ignore[union-attr]

    def test_expiration_zero_disables_the_cache(self):
        """With prompt_response_cache_expiration 0, nothing is cached or returned."""
        key = self.key(llmclient_id=self.llmclient_id)
        with patch.object(prompt_cache, "smarter_settings", MagicMock(prompt_response_cache_expiration=0)):
            cache_prompt_response(key, chat_completion())
            self.assertIsNone(get_cached_prompt_response(key))
        self.assertIsNone(get_cached_prompt_response(key))

    def test_claim_first_message(self):
        """A conversation's first message is claimed once, so a later message sent before its history is saved is not."""
        self.assertTrue(claim_first_message(self.llmclient_id))
        self.assertFalse(claim_first_message(self.llmclient_id))
        self.assertTrue(claim_first_message(self.llmclient_id + 1))

    def test_prompt_cache_hit(self):
        """PromptCacheHit carries the cached answer."""
        response = chat_completion()
        self.assertIs(PromptCacheHit(response).response, response)


class TestHandlerPromptCache(TestAccountMixin):
    """Test that the handler answers a repeated first message from the cache, without calling the LLM."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        for target in PROMPT_TASK_PATCHES:
            patcher = patch(target)
            patcher.start()
            cls.addClassCleanup(patcher.stop)
        cls.llmclient = LLMClient.objects.create(
            name=f"test_prompt_cache_{cls.hash_suffix}",
            user_profile=cls.user_profile,
            deployed=False,
            default_model="gpt-test",
        )

    @classmethod
    def tearDownClass(cls):
        Prompt.objects.filter(llmclient=cls.llmclient).delete()
        cls.llmclient.delete()
        super().tearDownClass()

    def prompt(self) -> Prompt:
        """Return a new conversation with the test LLMClient."""
        return Prompt.objects.create(
            session_key=secrets.token_hex(32),
            user_profile=self.user_profile,
            llmclient=self.llmclient,
            ip_address="192.1.1.1",
            user_agent="unit test",
            url="https://www.test.com",
        )

    def ask(self, prompt: Prompt, message: str) -> SmarterDictType:
        """Send a message in a conversation, and return the handler's response."""
        provider_orm = Provider.objects.filter(name="openai").first()
        if provider_orm is None:
            self.skipTest("the platform's openai Provider does not exist.")
        provider = OpenAISmarterClient(
            provider=provider_orm,
            provider_name="openai",
            base_url="https://api.example.com/v1/",
            api_key=SecretStr("sk-test"),
            default_model="gpt-test",
        )
        provider.prompt = prompt
        data = {"session_key": prompt.session_key, "messages": [{"role": "user", "content": message}]}
        return provider.handler(self.user_profile, prompt, data)  # type: ignore[return-value]

    def test_a_repeated_first_message_is_answered_from_the_cache(self):
        """The second conversation that opens with the same message gets the first one's answer, without the LLM."""
        message = f"What's the weather in Paris, {self.hash_suffix}?"
        with patch(CREATE_PATCH, return_value=chat_completion()) as create:
            first = self.ask(self.prompt(), message)
            second = self.ask(self.prompt(), message.upper())
        self.assertEqual(create.call_count, 1)
        self.assertEqual(first["statusCode"], HTTPStatus.OK)
        self.assertEqual(second["statusCode"], HTTPStatus.OK)
        self.assertIn("Sunny, 21 degrees.", second["body"])
        self.assertIn(CACHED_RESPONSE_ID_PREFIX, second["body"])

    def test_later_messages_call_the_llm(self):
        """A message that follows another in its conversation is never answered from the cache."""
        message = f"Tell me more, {self.hash_suffix}."
        conversation = self.prompt()
        with patch(CREATE_PATCH, return_value=chat_completion()) as create:
            self.ask(self.prompt(), message)
            self.ask(conversation, "Hello")
            self.ask(conversation, message)
        self.assertEqual(create.call_count, 3)

    def test_an_error_is_not_cached(self):
        """A first message whose LLM call fails is sent to the LLM again."""
        message = f"Will this fail, {self.hash_suffix}?"
        with patch(CREATE_PATCH, side_effect=RuntimeError("the provider is down")) as create:
            self.ask(self.prompt(), message)
            self.ask(self.prompt(), message)
        self.assertEqual(create.call_count, 2)


class TestProviderPromptCache(SmarterTestBase):
    """Test the provider's use of the prompt cache, on a client without its handler state."""

    def setUp(self):
        super().setUp()
        self.client = OpenAISmarterClient.__new__(OpenAISmarterClient)
        self.llmclient = MagicMock(pk=abs(hash(self.id())) % 1_000_000_000)
        self.llmclient.updated_at = datetime.datetime(2026, 10, 28, tzinfo=datetime.timezone.utc)
        self.client._chat = MagicMock(spec=Prompt, llmclient=self.llmclient, pk=self.llmclient.pk)
        self.client.input_text = "What's the weather in Paris?"
        # these tests look up one conversation's first message more than once.
        claim = patch.object(provider_module, "claim_first_message", return_value=True)
        claim.start()
        self.addCleanup(claim.stop)
        self.client.model = "gpt-test"
        self.client.temperature = 0.5
        self.client.max_completion_tokens = 256
        self.client.mcp_toolkit = None
        self.client.extension_toolkit = None
        self.client._messages = [
            {"role": "system", "content": "You are a test."},
            {"role": "assistant", "content": "Welcome!"},
            {"role": "user", "content": "What's the weather in Paris?"},
        ]
        patcher = patch.object(OpenAISmarterClient, "provider_name", "openai")
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_first_message_cache_key(self):
        """The first message of a conversation has a cache key."""
        key = self.client.first_message_cache_key()
        self.assertEqual(key.llmclient_id, self.llmclient.pk)  # type: ignore[union-attr]
        self.assertEqual(key.provider, "openai")  # type: ignore[union-attr]
        self.assertEqual(key.message, message_digest("what's the weather in paris"))  # type: ignore[union-attr]

    def test_later_messages_have_no_cache_key(self):
        """A message that follows another in the conversation is never cached."""
        self.client._messages = self.client._messages + [
            {"role": "assistant", "content": "Sunny."},
            {"role": "user", "content": "And in London?"},
        ]
        self.assertIsNone(self.client.first_message_cache_key())

    def test_no_cache_key_without_an_llmclient_or_when_disabled(self):
        """Without an LLMClient, a message or the cache, there is no key."""
        with patch.object(provider_module, "smarter_settings", MagicMock(prompt_response_cache_expiration=0)):
            self.assertIsNone(self.client.first_message_cache_key())
        self.client._chat = MagicMock(spec=Prompt, llmclient=None)
        self.assertIsNone(self.client.first_message_cache_key())
        self.client.input_text = ""
        self.assertIsNone(self.client.first_message_cache_key())

    def test_lookup_and_store(self):
        """A first message's answer is stored, and the next identical first message is a hit."""
        self.client.handle_prompt_cache_lookup()
        self.assertTrue(self.client.prompt_cacheable)
        self.client.handle_prompt_cache_store(chat_completion())
        with self.assertRaises(PromptCacheHit) as hit:
            self.client.handle_prompt_cache_lookup()
        self.assertEqual(hit.exception.response.choices[0].message.content, "Sunny, 21 degrees.")

    def test_lookup_of_a_later_message(self):
        """A later message is neither looked up nor cacheable."""
        self.client._messages = self.client._messages + [{"role": "user", "content": "And in London?"}]
        self.client.handle_prompt_cache_lookup()
        self.assertFalse(self.client.prompt_cacheable)
        self.assertIsNone(self.client.prompt_cache_key)

    def test_store_skips_uncacheable_and_unfinished_answers(self):
        """An answer is not stored when a tool made the prompt uncacheable, or the LLM did not finish."""
        self.client.handle_prompt_cache_lookup()
        self.client.handle_prompt_cache_store(chat_completion(finish_reason="length"))
        self.client.handle_prompt_cache_store(None)
        self.client.prompt_cacheable = False
        self.client.handle_prompt_cache_store(chat_completion())
        self.assertIsNone(get_cached_prompt_response(self.client.prompt_cache_key))  # type: ignore[arg-type]

    def test_tool_call_is_cacheable(self):
        """Read-only MCP tools, extension tools with cache_ttl and GET plugins keep the answer cacheable."""
        self.client.mcp_toolkit = MagicMock()
        self.client.mcp_toolkit.is_mcp_function.side_effect = lambda name: name.startswith("mcp")
        self.client.mcp_toolkit.functions = {
            "mcp1_read": MagicMock(read_only=True, mcpclient=MagicMock(cache_ttl=3600)),
            "mcp1_write": MagicMock(read_only=False, mcpclient=MagicMock(cache_ttl=3600)),
            "mcp2_read": MagicMock(read_only=True, mcpclient=MagicMock(cache_ttl=0)),
        }
        self.client.extension_toolkit = MagicMock()
        self.client.extension_toolkit.is_extension_function.side_effect = lambda name: name.startswith("ext")
        self.client.extension_toolkit.functions = {
            "ext_cached": MagicMock(tool=MagicMock(cache_ttl=60)),
            "ext_uncached": MagicMock(tool=MagicMock(cache_ttl=0)),
        }
        get_plugin = MagicMock(plugin_data=MagicMock(method="GET"))
        post_plugin = MagicMock(plugin_data=MagicMock(method="POST"))
        sql_plugin = MagicMock(plugin_data=MagicMock(spec=[]))
        cases = [
            ("mcp1_read", "result", None, True),
            ("mcp1_write", "result", None, False),
            ("mcp2_read", "result", None, False),
            ("mcp1_read", "Error: the server is down", None, False),
            ("ext_cached", {"forecast": "sunny"}, None, True),
            ("ext_cached", {"error": "no such city"}, None, False),
            ("ext_uncached", {"forecast": "sunny"}, None, False),
            ("smarter_plugin_1", "rows", get_plugin, True),
            ("smarter_plugin_1", "rows", sql_plugin, True),
            ("smarter_plugin_1", "rows", post_plugin, False),
            ("smarter_plugin_1", "", get_plugin, False),
            ("smarter_plugin_1", '{"error": "budget_exceeded"}', get_plugin, False),
            ("unknown", "result", None, False),
        ]
        for function_name, response, plugin, expected in cases:
            with self.subTest(function_name=function_name, response=response):
                self.assertEqual(self.client.tool_call_is_cacheable(function_name, response, plugin), expected)
