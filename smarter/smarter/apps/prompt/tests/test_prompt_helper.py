"""Test :class:`smarter.apps.prompt.models.prompt_helper.PromptHelper`."""

from unittest.mock import MagicMock, patch

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
            self.assertIs(PromptHelper.llmclient.fget(helper), llmclient)
            lookup.assert_called_once_with(request=helper.smarter_request)
        self.assertIs(helper._llmclient, llmclient)

    def test_later_reads_do_not_look_it_up_again(self):
        llmclient = MagicMock()
        helper = MagicMock(_llmclient=llmclient)
        with patch(f"{MODULE}.get_cached_llmclient_by_request") as lookup:
            self.assertIs(PromptHelper.llmclient.fget(helper), llmclient)
            lookup.assert_not_called()
