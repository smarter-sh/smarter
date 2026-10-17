"""Test server_logs_enabled(), require_server_logs(), terminal_enabled() and require_terminal(), which decide whether users can view their server logs, and superusers open a terminal, in the browser."""

from unittest.mock import MagicMock, patch

from django.contrib.auth.models import AnonymousUser
from django.http import Http404, HttpResponse
from django.test import RequestFactory

from smarter.apps.dashboard.views.terminal_emulator.enabled import (
    require_server_logs,
    require_terminal,
    server_logs_enabled,
    terminal_enabled,
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


class TestTerminalEnabled(SmarterTestBase):
    """The terminal is enabled by its setting alone, which is off by default."""

    def test_follows_the_setting(self):
        for setting in (True, False):
            with patch(f"{MODULE}.smarter_settings", MagicMock(enable_web_console_terminal=setting)):
                self.assertIs(terminal_enabled(), setting)


class TestRequireTerminal(SmarterTestBase):
    """A Terminal view is a 404 while the terminal is disabled, and for every signed in user but a superuser."""

    def setUp(self):
        super().setUp()
        self.view = MagicMock(return_value=HttpResponse("terminal"))
        self.request = RequestFactory().get("/dashboard/terminal/")

    def call(self, enabled: bool, user) -> HttpResponse:
        self.request.user = user
        with patch(f"{MODULE}.terminal_enabled", return_value=enabled):
            return require_terminal(self.view)(self.request)

    def test_a_superuser(self):
        response = self.call(True, MagicMock(is_authenticated=True, is_superuser=True))
        self.assertEqual(response.content, b"terminal")

    def test_an_anonymous_user_reaches_the_view_which_redirects_to_login(self):
        response = self.call(True, AnonymousUser())
        self.assertEqual(response.content, b"terminal")

    def test_a_user_who_is_not_a_superuser(self):
        with self.assertRaises(Http404):
            self.call(True, MagicMock(is_authenticated=True, is_superuser=False))
        self.view.assert_not_called()

    def test_disabled(self):
        with self.assertRaises(Http404):
            self.call(False, MagicMock(is_authenticated=True, is_superuser=True))
        self.view.assert_not_called()
