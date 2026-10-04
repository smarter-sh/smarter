"""Test the dashboard's "Quick Actions" api view, :mod:`smarter.apps.dashboard.views.views.api.quick_actions`."""

from http import HTTPStatus

from django.test import Client
from django.urls import reverse

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.dashboard.views.views.api.urls import DashboardApiReverseNames
from smarter.lib import json

from ..const import namespace


class TestQuickActionsApiView(TestAccountMixin):
    """Test QuickActionsView, which lists links to the console pages that users visit most."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.addCleanup(self.client.logout)
        self.url = reverse(f"{namespace}:{DashboardApiReverseNames.namespace}:{DashboardApiReverseNames.quick_actions}")

    def test_quick_actions(self):
        self.client.force_login(self.non_admin_user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:300])
        actions = json.loads(response.content)
        self.assertTrue(actions)
        for action in actions:
            with self.subTest(action=action["name"]):
                self.assertTrue(action["description"])
                self.assertTrue(action["icon"].startswith("ki-"))
                self.assertTrue(action["url"].startswith(("/", "https://")))
                if action["url"].startswith("/"):
                    self.assertNotEqual(self.client.get(action["url"]).status_code, HTTPStatus.NOT_FOUND)

    def test_quick_actions_anonymous(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
