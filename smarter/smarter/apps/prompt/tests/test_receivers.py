"""Test :mod:`smarter.apps.prompt.receivers`.

See :class:`smarter.lib.unittest.receivers.ReceiversTestMixin`.
"""

from unittest.mock import MagicMock, patch

from smarter.apps.prompt import receivers
from smarter.lib.unittest.base_classes import SmarterTestBase
from smarter.lib.unittest.receivers import ReceiversTestMixin


class TestPromptReceivers(ReceiversTestMixin, SmarterTestBase):
    """Call each receiver of the prompt app with mock arguments."""

    receivers_module = receivers
    # these serialize a real request, or read attributes of the sending provider instance.
    skip = (
        "handle_chat_completion_response_received",
        "handle_chat_response_success",
        "handle_chat_provider_initialized",
    )

    def test_session_invoked_logs_at_debug(self):
        """The session's string form includes its session_key, so it's logged at DEBUG, not INFO."""
        with patch.object(receivers, "logger") as mock_logger:
            receivers.handle_chat_session_invoked(sender=SmarterTestBase, instance=MagicMock(), request=None)
        mock_logger.debug.assert_called_once()
        mock_logger.info.assert_not_called()

    def test_chat_response_success_without_a_prompt_logs_no_warning(self):
        """The passthrough api never has a Prompt, so a response without one is expected: no warning, no history."""
        with patch.object(receivers, "logger") as mock_logger:
            with patch.object(receivers, "create_prompt_history") as mock_task:
                receivers.handle_chat_response_success(
                    sender=SmarterTestBase, prompt=None, request=None, response=None
                )
        mock_logger.warning.assert_not_called()
        mock_task.delay.assert_not_called()
