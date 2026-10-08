"""Test server_logs_enabled() and require_server_logs(), which decide whether users can view their server logs in the browser."""

from unittest.mock import MagicMock, patch

from django.http import Http404, HttpResponse
from django.test import RequestFactory

from smarter.apps.dashboard.views.terminal_emulator.enabled import (
    require_server_logs,
    server_logs_enabled,
)
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.unittest.base_classes import SmarterTestBase

MODULE = "smarter.apps.dashboard.views.terminal_emulator.enabled"


class TestServerLogsEnabled(SmarterTestBase):
    """Server logs are viewable only when the setting is on and the request log context switch is active."""

    def check(self, setting: bool, switch: bool) -> bool:
        with (
            patch(f"{MODULE}.smarter_settings", MagicMock(enable_dashboard_server_logs=setting)),
            patch(f"{MODULE}.switch_is_active", return_value=switch) as switch_is_active,
        ):
            result = server_logs_enabled()
        if setting:
            switch_is_active.assert_called_once_with(SmarterWaffleSwitches.ENABLE_WEB_CONSOLE_SERVER_LOGS)
        return result

    def test_enabled(self):
        self.assertTrue(self.check(setting=True, switch=True))

    def test_disabled_by_the_switch(self):
        self.assertFalse(self.check(setting=True, switch=False))

    def test_disabled_by_the_setting(self):
        self.assertFalse(self.check(setting=False, switch=True))


class TestRequireServerLogs(SmarterTestBase):
    """A Server Logs view is a 404 while server logs are disabled."""

    def setUp(self):
        super().setUp()
        self.view = MagicMock(return_value=HttpResponse("logs"))
        self.request = RequestFactory().get("/dashboard/logs/")

    def test_calls_the_view_while_enabled(self):
        with patch(f"{MODULE}.server_logs_enabled", return_value=True):
            response = require_server_logs(self.view)(self.request, "an arg", key="a kwarg")
        self.assertEqual(response.content, b"logs")
        self.view.assert_called_once_with(self.request, "an arg", key="a kwarg")

    def test_is_a_404_while_disabled(self):
        with patch(f"{MODULE}.server_logs_enabled", return_value=False), self.assertRaises(Http404):
            require_server_logs(self.view)(self.request)
        self.view.assert_not_called()
