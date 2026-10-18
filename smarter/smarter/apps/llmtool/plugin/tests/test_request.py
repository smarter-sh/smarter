"""Unit tests for :py:mod:`smarter.apps.llmtool.plugin.request`."""

from types import SimpleNamespace

from django.dispatch import Signal

from smarter.apps.llmtool.plugin.request import (
    API_PLUGIN_REQUEST_SIGNALS,
    IMAGE_SEARCH_PLUGIN_REQUEST_SIGNALS,
    SKILL_PLUGIN_REQUEST_SIGNALS,
    SQL_PLUGIN_REQUEST_SIGNALS,
    PluginRequest,
    PluginRequestSignals,
)
from smarter.lib.unittest.base_classes import SmarterTestBase

from .base_classes import capture_request_signals, roles

PLUGIN = SimpleNamespace(name="test_plugin_request")


class TestPluginRequest(SmarterTestBase):
    """Test PluginRequest, with a family of test signals."""

    def setUp(self):
        super().setUp()
        self.signals = PluginRequestSignals(
            started=Signal(),
            responded=Signal(),
            failed=Signal(),
            completed=Signal(),
            authenticated=Signal(),
            authentication_failed=Signal(),
        )

    def test_families(self):
        """Test that each plugin family has its own signals, and that only SkillPlugin has no credentials."""
        families = (
            SQL_PLUGIN_REQUEST_SIGNALS,
            API_PLUGIN_REQUEST_SIGNALS,
            IMAGE_SEARCH_PLUGIN_REQUEST_SIGNALS,
            SKILL_PLUGIN_REQUEST_SIGNALS,
        )
        started = [family.started for family in families]
        self.assertEqual(len(set(map(id, started))), len(families))
        for family in families[:3]:
            self.assertIsInstance(family.authenticated, Signal)
            self.assertIsInstance(family.authentication_failed, Signal)
        self.assertIsNone(SKILL_PLUGIN_REQUEST_SIGNALS.authenticated)
        self.assertIsNone(SKILL_PLUGIN_REQUEST_SIGNALS.authentication_failed)

    def test_success(self):
        """Test the signals of a successful request, in order, and their arguments."""
        with capture_request_signals(self.signals) as received:
            with PluginRequest(self.signals, sender=str, plugin=PLUGIN, function_args={"a": 1}) as request:  # type: ignore[arg-type]
                request.authenticated(connection="db")
                request.responded(response="[]", cached=False, sql="SELECT 1;")
        self.assertEqual(roles(received), ["started", "authenticated", "responded", "completed"])
        started, authenticated, responded, completed = (kwargs for _, kwargs in received)
        self.assertEqual(started["function_args"], {"a": 1})
        self.assertIs(started["plugin"], PLUGIN)
        self.assertIs(started["sender"], str)
        self.assertEqual(authenticated["connection"], "db")
        self.assertEqual((responded["response"], responded["cached"], responded["sql"]), ("[]", False, "SELECT 1;"))
        self.assertTrue(completed["success"])
        self.assertGreaterEqual(completed["duration"], 0.0)

    def test_failed(self):
        """Test that a request that calls failed() completes unsuccessfully."""
        with capture_request_signals(self.signals) as received:
            with PluginRequest(self.signals, sender=str, plugin=PLUGIN) as request:  # type: ignore[arg-type]
                request.authentication_failed(error="HTTP 401", status_code=401)
                request.failed(error="request failed")
        self.assertEqual(roles(received), ["started", "authentication_failed", "failed", "completed"])
        self.assertEqual(received[1][1]["status_code"], 401)
        self.assertEqual(received[2][1]["error"], "request failed")
        self.assertFalse(received[3][1]["success"])
        self.assertTrue(request.has_failed)

    def test_exception(self):
        """Test that an exception sends failed, then completed, and is not suppressed."""
        with capture_request_signals(self.signals) as received:
            with self.assertRaises(ValueError):
                with PluginRequest(self.signals, sender=str, plugin=PLUGIN):  # type: ignore[arg-type]
                    raise ValueError("boom")
        self.assertEqual(roles(received), ["started", "failed", "completed"])
        self.assertEqual(received[1][1]["error"], "boom")
        self.assertFalse(received[2][1]["success"])

    def test_exception_after_failed(self):
        """Test that an exception after failed() does not send failed a second time."""
        with capture_request_signals(self.signals) as received:
            with self.assertRaises(ValueError):
                with PluginRequest(self.signals, sender=str, plugin=PLUGIN) as request:  # type: ignore[arg-type]
                    request.failed(error="first")
                    raise ValueError("second")
        self.assertEqual(roles(received), ["started", "failed", "completed"])
        self.assertEqual(received[1][1]["error"], "first")

    def test_family_without_credentials(self):
        """Test that the authentication methods send nothing for a family without credentials."""
        signals = PluginRequestSignals(started=Signal(), responded=Signal(), failed=Signal(), completed=Signal())
        with capture_request_signals(signals) as received:
            with PluginRequest(signals, sender=str, plugin=PLUGIN) as request:  # type: ignore[arg-type]
                request.authenticated()
                request.authentication_failed(error="nope")
                request.responded(response={"a": 1})
        self.assertEqual(roles(received), ["started", "responded", "completed"])
        self.assertTrue(received[2][1]["success"])

    def test_duration_before_start(self):
        """Test that the duration of a request that has not started is zero."""
        self.assertEqual(PluginRequest(self.signals, sender=str, plugin=PLUGIN).duration, 0.0)  # type: ignore[arg-type]
