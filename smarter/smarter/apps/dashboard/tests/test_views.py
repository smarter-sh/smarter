"""Test the dashboard's React page views: the prompt passthrough page and its providers api, the terminal emulator (logs) page, and the manifest dropzone page."""

from http import HTTPStatus
from unittest.mock import patch

from django.test import Client

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.dashboard.views.dropzone.names import DropzoneReverseNames
from smarter.apps.dashboard.views.passthrough.api.urls import PassthroughApiReverseNames
from smarter.apps.dashboard.views.passthrough.urls import PassthroughReverseNames
from smarter.apps.dashboard.views.terminal_emulator.api.urls import (
    DashboardLogsApiReverseNames,
)
from smarter.apps.dashboard.views.terminal_emulator.names import (
    DashboardLogsReverseNames,
)
from smarter.apps.dashboard.views.views.urls import DashboardReverseNames
from smarter.lib import json
from smarter.lib.django.shortcuts import reverse

DASHBOARD = DashboardReverseNames.namespace


class TestDashboardReactViews(TestAccountMixin):
    """Test that each React page renders its root element for a logged in user, and redirects an anonymous one."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.addCleanup(self.client.logout)
        self.client.force_login(self.admin_user)

    def assert_page(self, url: str, root_id: str):
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:500])
        self.assertIn(root_id.encode(), response.content)
        self.client.logout()
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_passthrough(self):
        url = reverse(DASHBOARD, PassthroughReverseNames.namespace, PassthroughReverseNames.view)
        self.assert_page(url, "smarter-prompt-passthrough-root")

    def test_terminal_emulator(self):
        url = reverse(DASHBOARD, DashboardLogsReverseNames.namespace, DashboardLogsReverseNames.terminal_emulator_view)
        self.assert_page(url, "smarter-terminal-emulator-root")

    def test_sidebar_server_logs(self):
        """Test that the sidebar has a Server Logs item only while server logs are viewable in the browser."""
        url = reverse(DASHBOARD, DropzoneReverseNames.namespace, DropzoneReverseNames.dropzone)
        menu_item = b">Server Logs</span>"
        with patch("smarter.apps.dashboard.context_processors.server_logs_enabled", return_value=False):
            self.assertNotIn(menu_item, self.client.get(url).content)
        with patch("smarter.apps.dashboard.context_processors.server_logs_enabled", return_value=True):
            self.assertIn(menu_item, self.client.get(url).content)

    def test_server_logs_are_not_found_while_disabled(self):
        """Test that the Server Logs page and its log stream are a 404 while server logs are disabled."""
        page = reverse(DASHBOARD, DashboardLogsReverseNames.namespace, DashboardLogsReverseNames.terminal_emulator_view)
        stream = reverse(
            DASHBOARD,
            DashboardLogsReverseNames.namespace,
            DashboardLogsApiReverseNames.namespace,
            DashboardLogsApiReverseNames.stream,
        )
        with patch("smarter.apps.dashboard.views.terminal_emulator.enabled.server_logs_enabled", return_value=False):
            self.assertEqual(self.client.get(page).status_code, HTTPStatus.NOT_FOUND)
            self.assertEqual(self.client.get(stream).status_code, HTTPStatus.NOT_FOUND)
        with patch("smarter.apps.dashboard.views.terminal_emulator.enabled.server_logs_enabled", return_value=True):
            self.assertEqual(self.client.get(page).status_code, HTTPStatus.OK)

    def test_dropzone(self):
        url = reverse(DASHBOARD, DropzoneReverseNames.namespace, DropzoneReverseNames.dropzone)
        self.assert_page(url, "smarter-manifest-dropzone-root")

    def test_providers_api(self):
        """Test that the passthrough page's providers api returns the providers that the user can read."""
        url = reverse(
            DASHBOARD,
            PassthroughReverseNames.namespace,
            PassthroughApiReverseNames.namespace,
            PassthroughApiReverseNames.api_providers,
        )
        response = self.client.post(url)
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:500])
        self.assertIsInstance(json.loads(response.content)["providers"], list)
