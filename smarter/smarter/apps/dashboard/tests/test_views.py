"""
Test the dashboard's tool pages: the Prompt Passthrough, the Terminal and the manifest drop zone.

They are the single-page console's (ADR-035). This module also tests the passthrough's providers api, the sidebar's
Terminal item, and the paths of the dashboard's endpoints in the web console's api.
"""

from http import HTTPStatus
from unittest.mock import patch

from django.test import Client

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.dashboard.context_processors import sidebar_context
from smarter.apps.dashboard.views.dropzone.names import DropzoneReverseNames
from smarter.apps.dashboard.views.passthrough.api.urls import PassthroughApiReverseNames
from smarter.apps.dashboard.views.passthrough.urls import PassthroughReverseNames
from smarter.apps.dashboard.views.terminal_emulator.api.names import (
    DashboardLogsApiReverseNames,
    DashboardTerminalApiReverseNames,
)
from smarter.apps.dashboard.views.terminal_emulator.names import (
    DashboardTerminalReverseNames,
)
from smarter.apps.dashboard.views.views.api.urls import DashboardApiReverseNames
from smarter.apps.dashboard.views.views.urls import DashboardReverseNames
from smarter.common.conf import smarter_settings
from smarter.lib import json
from smarter.lib.django.shortcuts import reverse
from smarter.lib.unittest.resource_views import assert_console_page

DASHBOARD = DashboardReverseNames.namespace
TERMINAL_ENABLED = "smarter.apps.dashboard.views.terminal_emulator.enabled.terminal_enabled"
SETTINGS = "smarter.apps.dashboard.context_processors.smarter_settings"


class SettingsWith:
    """Smarter_settings, which is frozen, with some of its values replaced."""

    def __init__(self, **values):
        self.__dict__.update(values)

    def __getattr__(self, name):
        return getattr(smarter_settings, name)


class TestDashboardReactViews(TestAccountMixin):
    """Test that each tool page is the console's, and that the Terminal is a superuser's only."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.addCleanup(self.client.logout)
        self.client.force_login(self.admin_user)

    def test_passthrough(self):
        """The Prompt Passthrough is the console's page, which gets its urls from the console's session."""
        url = reverse(DASHBOARD, PassthroughReverseNames.namespace, PassthroughReverseNames.view)
        self.assertEqual(url, "/dashboard/passthrough/")
        assert_console_page(self, url)

    def test_terminal(self):
        """
        The Terminal is the console's page, for a superuser while the terminal is enabled.

        An anonymous visitor gets the console's page too, which sends them to the sign-in page.
        """
        url = reverse(
            DASHBOARD, DashboardTerminalReverseNames.namespace, DashboardTerminalReverseNames.terminal_emulator_view
        )
        self.assertEqual(url, "/dashboard/terminal/")
        with patch(TERMINAL_ENABLED, return_value=True):
            assert_console_page(self, url)

    def test_terminal_is_not_found_while_disabled_or_for_a_user_who_is_not_a_superuser(self):
        url = reverse(
            DASHBOARD, DashboardTerminalReverseNames.namespace, DashboardTerminalReverseNames.terminal_emulator_view
        )
        with patch(TERMINAL_ENABLED, return_value=False):
            self.assertEqual(self.client.get(url).status_code, HTTPStatus.NOT_FOUND)
        self.client.force_login(self.non_admin_user)
        with patch(TERMINAL_ENABLED, return_value=True):
            self.assertEqual(self.client.get(url).status_code, HTTPStatus.NOT_FOUND)

    def test_sidebar_terminal(self):
        """
        Test that the sidebar's links have the Terminal while the terminal is enabled.

        The session api gives it to superusers only: see smarter.apps.api.web.session.tests.
        """
        terminal = reverse(
            DASHBOARD, DashboardTerminalReverseNames.namespace, DashboardTerminalReverseNames.terminal_emulator_view
        )
        self.addCleanup(sidebar_context.invalidate)
        for enabled in (True, False):
            sidebar_context.invalidate()
            with patch(SETTINGS, SettingsWith(enable_web_console_terminal=enabled)):
                links = sidebar_context()["sidebar"]
            self.assertEqual(links.get("terminal") == terminal, enabled)

    def test_sidebar_has_no_server_logs(self):
        """Test that the sidebar has no Server Logs link: the server logs are a tab of the Prompt Passthrough."""
        sidebar_context.invalidate()
        self.addCleanup(sidebar_context.invalidate)
        with patch("smarter.apps.dashboard.views.terminal_emulator.enabled.server_logs_enabled", return_value=True):
            links = sidebar_context()["sidebar"]
        self.assertFalse([name for name in links if "log" in name])

    def test_server_logs_are_not_found_while_disabled(self):
        """Test that the log stream is a 404 while server logs are disabled."""
        stream = reverse(DashboardLogsApiReverseNames.namespace, DashboardLogsApiReverseNames.stream)
        with patch("smarter.apps.dashboard.views.terminal_emulator.enabled.server_logs_enabled", return_value=False):
            self.assertEqual(self.client.get(stream).status_code, HTTPStatus.NOT_FOUND)

    def test_dropzone(self):
        """The manifest drop zone is the console's page."""
        url = reverse(DASHBOARD, DropzoneReverseNames.namespace, DropzoneReverseNames.dropzone)
        self.assertEqual(url, "/dashboard/dropzone/")
        assert_console_page(self, url)

    def test_providers_api(self):
        """Test that the passthrough page's providers api returns the providers that the user can read."""
        url = reverse(PassthroughApiReverseNames.namespace, PassthroughApiReverseNames.api_providers)
        response = self.client.post(url)
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:500])
        self.assertIsInstance(json.loads(response.content)["providers"], list)

    def test_web_api_paths(self):
        """Test that the dashboard's endpoints are in the web console's api, at /api/web/dashboard/."""
        dashboard = DashboardApiReverseNames
        self.assertEqual(reverse(dashboard.namespace, dashboard.my_resources), "/api/web/dashboard/my-resources/")
        self.assertEqual(reverse(dashboard.namespace, dashboard.service_health), "/api/web/dashboard/service-health/")
        self.assertEqual(reverse(dashboard.namespace, dashboard.token_charges), "/api/web/dashboard/charges/")
        self.assertEqual(reverse(dashboard.namespace, dashboard.budgets), "/api/web/dashboard/budgets/")
        self.assertEqual(
            reverse(f"{dashboard.namespace}:{dashboard.budget_series}", kwargs={"resource_locator": "x"}),
            "/api/web/dashboard/budgets/x/series/",
        )
        self.assertEqual(reverse(dashboard.namespace, dashboard.activity), "/api/web/dashboard/activity/")
        self.assertEqual(reverse(dashboard.namespace, dashboard.getting_started), "/api/web/dashboard/getting-started/")
        self.assertEqual(reverse(dashboard.namespace, dashboard.quick_actions), "/api/web/dashboard/quick-actions/")
        self.assertEqual(reverse(dashboard.namespace, dashboard.global_search), "/api/web/dashboard/search/")
        self.assertEqual(
            reverse(
                f"{dashboard.namespace}:{dashboard.resource_detail}",
                kwargs={"kind": "Guardrail", "record_locator": "guardrail-rMQx"},
            ),
            "/api/web/dashboard/resource/Guardrail/guardrail-rMQx/",
        )
        self.assertEqual(reverse(dashboard.namespace, dashboard.welcome), "/api/web/dashboard/welcome/")
        self.assertEqual(reverse(dashboard.namespace, dashboard.welcome_dismiss), "/api/web/dashboard/welcome/dismiss/")
        self.assertEqual(reverse(dashboard.namespace, dashboard.onboarding_seen), "/api/web/dashboard/onboarding/seen/")
        self.assertEqual(
            reverse(DashboardTerminalApiReverseNames.namespace, DashboardTerminalApiReverseNames.ticket),
            "/api/web/dashboard/terminal/ticket/",
        )
        if smarter_settings.enable_dashboard_passthrough_prompt:
            self.assertEqual(
                reverse(PassthroughApiReverseNames.namespace, PassthroughApiReverseNames.api_providers),
                "/api/web/dashboard/passthrough/providers/",
            )
        if smarter_settings.enable_dashboard_server_logs:
            self.assertEqual(
                reverse(DashboardLogsApiReverseNames.namespace, DashboardLogsApiReverseNames.stream),
                "/api/web/dashboard/logs/stream/",
            )
