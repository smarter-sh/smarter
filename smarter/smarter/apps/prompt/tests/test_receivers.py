"""Test :mod:`smarter.apps.prompt.receivers`.

See :class:`smarter.lib.unittest.receivers.ReceiversTestMixin`.
"""

from unittest.mock import MagicMock, patch

from smarter.apps.prompt import receivers
from smarter.lib.unittest.base_classes import SmarterTestBase
from smarter.lib.unittest.receivers import ReceiversTestMixin

#: A stand-in for chat content, e.g. a user's date of birth, which no log may show.
CHAT_CONTENT_MARKER = "I was born on the marker date 31-dec-1999"


def passthrough_request() -> dict:
    """Return a request, as the passthrough api sends it as a failed iteration's data."""
    system_message = {"role": "system", "content": "You are a date calculator."}
    user_message = {"role": "user", "content": CHAT_CONTENT_MARKER}
    request = {"model": "gpt-test-model", "messages": [system_message, user_message]}
    return request


def provider_iteration() -> dict:
    """Return an iteration's data, as the chat providers send it: its request and the LLM's response."""
    response_message = {"role": "assistant", "content": CHAT_CONTENT_MARKER}
    response = {"choices": [{"message": response_message}]}
    iteration = {"request": passthrough_request(), "response": response}
    return iteration


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
                receivers.handle_chat_response_success(sender=SmarterTestBase, prompt=None, request=None, response=None)
        mock_logger.warning.assert_not_called()
        mock_task.delay.assert_not_called()

    def test_chat_response_success_saves_the_history_now(self):
        """A finished prompt's history is saved before its response returns, not by a Celery task.

        The next prompt of the conversation reads it, and a queued task could run after that prompt arrived.
        """
        prompt = MagicMock(id=7)
        messages = [{"role": "user", "content": "What is 2 to the 10th power?"}]
        with patch.object(receivers, "create_prompt_history") as mock_task:
            receivers.handle_chat_response_success(
                sender=SmarterTestBase, prompt=prompt, request=None, response={"id": "x"}, messages=messages
            )
        mock_task.assert_called_once_with(7, None, {"id": "x"}, messages)
        mock_task.delay.assert_not_called()

    def test_save_prompt_history_queues_the_task_when_the_save_fails(self):
        """A save that fails is queued as the Celery task, which retries it, and is logged without the chat."""
        with patch.object(receivers, "logger") as mock_logger:
            with patch.object(receivers, "create_prompt_history") as mock_task:
                mock_task.side_effect = RuntimeError(CHAT_CONTENT_MARKER)
                receivers.save_prompt_history(7, None, None, [{"role": "user", "content": CHAT_CONTENT_MARKER}])
        mock_task.delay.assert_called_once()
        mock_logger.error.assert_called_once()
        self.assertNotIn(CHAT_CONTENT_MARKER, str(mock_logger.error.call_args))

    def test_chat_response_failure_logs_no_chat_content(self):
        """A failed prompt logs the model and the number of messages, never the messages or the response (issue #970)."""
        exception = ValueError("The model does not exist.")
        with patch.object(receivers, "logger") as mock_logger:
            receivers.handle_chat_response_failure(
                sender=SmarterTestBase, iteration=1, exception=exception, first_iteration=passthrough_request()
            )
            receivers.handle_chat_response_failure(
                sender=SmarterTestBase, iteration=2, exception=exception, second_iteration=provider_iteration()
            )
        logged = str(mock_logger.mock_calls)
        self.assertNotIn(CHAT_CONTENT_MARKER, logged)
        self.assertIn("gpt-test-model", logged)
        self.assertEqual(mock_logger.error.call_count, 4)

    def test_chat_response_failure_client_error_logs_one_warning(self):
        """A provider's 4xx is the client's error: one warning without the stack trace, and no error (issue #984)."""
        exception = ValueError("Invalid 'temperature': decimal above maximum value.")
        with patch.object(receivers, "logger") as mock_logger:
            receivers.handle_chat_response_failure(
                sender=SmarterTestBase,
                iteration=1,
                exception=exception,
                first_iteration=passthrough_request(),
                stack_trace="Traceback (most recent call last): marker-stack-trace",
                client_error=True,
            )
        mock_logger.error.assert_not_called()
        mock_logger.warning.assert_called_once()
        logged = str(mock_logger.mock_calls)
        self.assertIn("temperature", logged)
        self.assertIn("gpt-test-model", logged)
        self.assertNotIn("marker-stack-trace", logged)
        self.assertNotIn(CHAT_CONTENT_MARKER, logged)

    def test_iteration_summary(self):
        """The summary of either shape of an iteration's data is its model and number of messages."""
        expected = {"model": "gpt-test-model", "messages": 2}
        self.assertEqual(receivers.iteration_summary(passthrough_request()), expected)
        self.assertEqual(receivers.iteration_summary(provider_iteration()), expected)
        self.assertEqual(receivers.iteration_summary({}), {"model": None, "messages": 0})
        self.assertIsNone(receivers.iteration_summary(None))
