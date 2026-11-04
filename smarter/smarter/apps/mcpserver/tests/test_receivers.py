"""Test smarter.apps.mcpserver.receivers."""

from unittest.mock import patch

from smarter.apps.mcpserver.receivers import handle_mcpserver_tool_called
from smarter.lib.unittest.base_classes import SmarterTestBase

RECEIVERS_LOGGER = "smarter.apps.mcpserver.receivers.logger"


def logged_text(calls) -> str:
    """
    Join the arguments of a mock logger's calls into one string.

    :param calls: The ``call_args_list`` of one of the mock logger's methods.
    :returns: Every argument of every call, as text.
    """
    parts = []
    for call in calls:
        for arg in call.args:
            parts.append(str(arg))
    text = " ".join(parts)
    return text


class TestHandleMCPServerToolCalled(SmarterTestBase):
    """Test that a tool call's argument values never reach the INFO log."""

    arguments = {
        "author": {"name": "Test Author", "email": "test-author@example.com"},
        "files": [{"path": "README.md", "content": "a whole file's content"}],
    }

    def call(self, is_error: bool = False):
        """
        Call the receiver with a patched logger.

        :param is_error: Whether the tool returned an error.
        :returns: The mock logger.
        """
        with patch(RECEIVERS_LOGGER) as logger:
            handle_mcpserver_tool_called(
                sender=None,
                server="smarter-project",
                tool_name="create_pull_request",
                arguments=self.arguments,
                is_error=is_error,
                characters=42,
            )
        return logger

    def test_info_logs_argument_names_not_values(self):
        """The INFO line names the tool and its arguments, and holds none of their values."""
        logger = self.call()
        info = logged_text(logger.info.call_args_list)
        self.assertIn("create_pull_request", info)
        self.assertIn("author, files", info)
        self.assertIn("42", info)
        self.assertNotIn("test-author@example.com", info)
        self.assertNotIn("a whole file's content", info)

    def test_debug_logs_argument_values(self):
        """The argument values are logged at DEBUG, for local development."""
        logger = self.call()
        debug = logged_text(logger.debug.call_args_list)
        self.assertIn("test-author@example.com", debug)

    def test_error_is_logged(self):
        """A tool that returned an error says so."""
        logger = self.call(is_error=True)
        info = logged_text(logger.info.call_args_list)
        self.assertIn("an error", info)
