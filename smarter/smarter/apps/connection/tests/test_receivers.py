"""Test :mod:`smarter.apps.connection.receivers`, for the failures that the SqlConnection model reports."""

import logging
from unittest.mock import MagicMock

from smarter.apps.connection import receivers
from smarter.lib.unittest.base_classes import SmarterTestBase
from smarter.lib.unittest.log_capture import WrappedLoggerCapture


class TestSqlConnectionFailedReceiver(SmarterTestBase):
    """Test that a failed connection is logged once, at ERROR, with what failed."""

    def test_the_stage_is_logged(self):
        capture = WrappedLoggerCapture(self, receivers.logger)
        connection = MagicMock()
        connection.get_connection_string.return_value = "mysql://user:****@db:3306/test"
        receivers.handle_sql_connection_failed(
            sender=None, connection=connection, stage="SSH connection", error="host unreachable"
        )
        error = capture.text(logging.ERROR)
        self.assertIn("SSH connection failed: host unreachable", error)
        self.assertIn("****", error)

    def test_the_stage_defaults_to_connection(self):
        capture = WrappedLoggerCapture(self, receivers.logger)
        receivers.handle_sql_connection_failed(sender=None, connection=MagicMock(), error="refused")
        self.assertIn("connection failed: refused", capture.text(logging.ERROR))
