"""Test the settings diagnostics that every environment logs: :mod:`smarter.settings.base`."""

from unittest.mock import MagicMock, patch

from smarter.lib.unittest.base_classes import SmarterTestBase
from smarter.settings.base import log_smtp_configuration

MODULE = "smarter.settings.base"

SMTP_SETTINGS = {
    "SMTP_HOST": "smtp.example.com",
    "SMTP_PORT": 587,
    "SMTP_USE_SSL": False,
    "SMTP_USE_TLS": True,
}
"""An environment's SMTP settings, with a placeholder host."""


class TestLogSmtpConfiguration(SmarterTestBase):
    """The SMTP diagnostics warn only when a process that sends email has no SMTP server."""

    def patch_settings(self, smtp_is_configured: bool, database_unavailable: bool) -> None:
        settings = MagicMock(smtp_is_configured=smtp_is_configured, database_unavailable=database_unavailable)
        patcher = patch(f"{MODULE}.smarter_settings", settings)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_a_configured_server_is_logged_at_debug(self):
        """A configured server is logged, with its host and port, and nothing warns."""
        self.patch_settings(smtp_is_configured=True, database_unavailable=False)
        with self.assertLogs(MODULE, level="DEBUG") as logs:
            log_smtp_configuration(SMTP_SETTINGS)
        self.assertEqual([record.levelname for record in logs.records], ["DEBUG"])
        self.assertIn("smtp.example.com:587", logs.output[0])

    def test_a_missing_server_warns(self):
        """A process that sends email, and has no SMTP server, warns."""
        self.patch_settings(smtp_is_configured=False, database_unavailable=False)
        with self.assertLogs(MODULE, level="WARNING") as logs:
            log_smtp_configuration(SMTP_SETTINGS)
        self.assertIn("SMTP server not configured", logs.output[0])

    def test_the_tool_worker_confirms_that_smtp_is_disabled(self):
        """The tool worker has no SMTP server by design (ADR-038): it confirms that at INFO, and doesn't warn."""
        self.patch_settings(smtp_is_configured=False, database_unavailable=True)
        with self.assertLogs(MODULE, level="DEBUG") as logs:
            log_smtp_configuration(SMTP_SETTINGS)
        self.assertEqual([record.levelname for record in logs.records], ["INFO"])
        self.assertIn("SMTP is disabled in the tool worker", logs.output[0])
