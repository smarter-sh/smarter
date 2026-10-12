"""Test the Prompt model and its cached lookup by session key."""

import secrets

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.llmclient.models import LLMClient
from smarter.apps.prompt.models import Prompt
from smarter.apps.prompt.models.prompt import get_cached_prompt_by_session_key


class TestGetCachedPromptBySessionKey(TestAccountMixin):
    """Test get_cached_prompt_by_session_key()."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.llmclient = LLMClient.objects.create(
            name=f"test_prompt_model_{cls.hash_suffix}", user_profile=cls.user_profile
        )

    @classmethod
    def tearDownClass(cls):
        cls.llmclient.delete()
        super().tearDownClass()

    def new_prompt(self) -> Prompt:
        prompt = Prompt.objects.create(
            session_key=f"test_prompt_model_{secrets.token_urlsafe(16)}",
            llmclient=self.llmclient,
            user_profile=self.user_profile,
            url="https://localhost:9357/test-prompt-model",
            ip_address="192.1.1.1",
            user_agent="unittest",
        )
        self.addCleanup(Prompt.objects.filter(pk=prompt.pk).delete)
        return prompt

    def test_returns_the_sessions_prompt(self):
        """The session's Prompt is returned, with its LLMClient."""
        prompt = self.new_prompt()
        cached = get_cached_prompt_by_session_key(prompt.session_key)
        self.assertEqual(cached.pk, prompt.pk)
        self.assertEqual(cached.llmclient.pk, self.llmclient.pk)

    def test_missing_prompt_is_not_cached(self):
        """A session without a Prompt raises, and finds its Prompt once it is created."""
        session_key = f"test_prompt_model_{secrets.token_urlsafe(16)}"
        with self.assertRaises(Prompt.DoesNotExist):
            get_cached_prompt_by_session_key(session_key)
        prompt = Prompt.objects.create(
            session_key=session_key,
            llmclient=self.llmclient,
            user_profile=self.user_profile,
            url="https://localhost:9357/test-prompt-model",
            ip_address="192.1.1.1",
            user_agent="unittest",
        )
        self.addCleanup(Prompt.objects.filter(pk=prompt.pk).delete)
        self.assertEqual(get_cached_prompt_by_session_key(session_key).pk, prompt.pk)

    def test_delete_invalidates(self):
        """Deleting a Prompt invalidates its cached copy."""
        prompt = self.new_prompt()
        session_key = prompt.session_key
        get_cached_prompt_by_session_key(session_key)
        prompt.delete()
        with self.assertRaises(Prompt.DoesNotExist):
            get_cached_prompt_by_session_key(session_key)
