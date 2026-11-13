"""Test :class:`smarter.apps.prompt.models.prompt_helper.PromptHelper`."""

from unittest.mock import MagicMock, patch

from smarter.apps.prompt.models.prompt import Prompt
from smarter.apps.prompt.models.prompt_helper import PromptHelper
from smarter.lib.unittest.base_classes import SmarterTestBase

MODULE = "smarter.apps.prompt.models.prompt_helper"


class TestPromptHelperLLMClient(SmarterTestBase):
    """Test the lazy ``llmclient`` property."""

    def test_first_read_returns_the_llmclient_it_looks_up(self):
        """The first read returns the llmclient that it found for the request, rather than None."""
        helper = MagicMock(_llmclient=None)
        llmclient = MagicMock()
        with patch(f"{MODULE}.get_cached_llmclient_by_request", return_value=llmclient) as lookup:
            # mypy types a property read from its class as its getter, not as the property.
            self.assertIs(PromptHelper.llmclient.fget(helper), llmclient)  # type: ignore[attr-defined]
            lookup.assert_called_once_with(request=helper.smarter_request)
        self.assertIs(helper._llmclient, llmclient)

    def test_later_reads_do_not_look_it_up_again(self):
        llmclient = MagicMock()
        helper = MagicMock(_llmclient=llmclient)
        with patch(f"{MODULE}.get_cached_llmclient_by_request") as lookup:
            # mypy types a property read from its class as its getter, not as the property.
            self.assertIs(PromptHelper.llmclient.fget(helper), llmclient)  # type: ignore[attr-defined]
            lookup.assert_not_called()


class TestPromptHelperGetCachedChatUserAgent(SmarterTestBase):
    """Test the User-Agent that ``get_cached_chat()`` stores in a new session's Prompt."""

    def created_user_agent(self, user_agent):
        """Return the user_agent that get_cached_chat() passes to Prompt.objects.create() for a new session."""
        helper = MagicMock(
            smarter_request=MagicMock(),
            session_key="session-key",
            url="http://example.com/config/",
            user_agent=user_agent,
        )
        with (
            patch(f"{MODULE}.get_cached_prompt_by_session_key", side_effect=Prompt.DoesNotExist),
            patch.object(Prompt, "objects") as objects,
        ):
            PromptHelper.get_cached_chat(helper)
        objects.create.assert_called_once()
        return objects.create.call_args.kwargs["user_agent"]

    def test_a_user_agent_longer_than_its_column_is_truncated(self):
        """A User-Agent longer than Prompt.user_agent is truncated, rather than failing with a DataError."""
        max_length = Prompt._meta.get_field("user_agent").max_length
        assert max_length is not None
        self.assertEqual(self.created_user_agent("x" * (max_length + 745)), "x" * max_length)

    def test_a_short_user_agent_is_stored_as_is(self):
        self.assertEqual(self.created_user_agent("Mozilla/5.0"), "Mozilla/5.0")

    def test_a_missing_user_agent_gets_the_default(self):
        self.assertEqual(self.created_user_agent(None), "user_agent")
