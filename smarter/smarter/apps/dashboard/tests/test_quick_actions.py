"""Test the dashboard's "Quick Actions" api view, :mod:`smarter.apps.dashboard.views.views.api.quick_actions`."""

from http import HTTPStatus

from django.test import Client
from django.urls import reverse

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.dashboard.views.views.api.urls import DashboardApiReverseNames
from smarter.lib import json
from smarter.lib.typing import SmarterDictType

from ..const import namespace


class TestQuickActionsApiView(TestAccountMixin):
    """Test QuickActionsView, which lists links to the console pages that users visit most."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.addCleanup(self.client.logout)
        self.url = reverse(f"{namespace}:{DashboardApiReverseNames.namespace}:{DashboardApiReverseNames.quick_actions}")

    def quick_actions(self) -> list[SmarterDictType]:
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:300])
        return json.loads(response.content)

    def test_quick_actions(self):
        self.client.force_login(self.non_admin_user)
        actions = self.quick_actions()
        self.assertTrue(actions)
        names = [action["name"] for action in actions]
        self.assertIn("Guardrails", names)
        self.assertIn("API Reference", names)
        self.assertNotIn("Extensions", names)
        self.assertNotIn("Infrastructure", names)
        for action in actions:
            with self.subTest(action=action["name"]):
                self.assertTrue(action["description"])
                self.assertTrue(action["icon"].startswith("ki-"))
                self.assertTrue(action["url"].startswith(("/", "https://")))
                if action["url"].startswith("/"):
                    self.assertNotEqual(self.client.get(action["url"]).status_code, HTTPStatus.NOT_FOUND)

    def test_quick_actions_superuser(self):
        """Test that superusers also get the pages that only they may open, and can open them."""
        self.client.force_login(self.admin_user)
        actions = {action["name"]: action for action in self.quick_actions()}
        for name in ("Extensions", "Infrastructure"):
            with self.subTest(name=name):
                self.assertIn(name, actions)
                self.assertNotEqual(self.client.get(actions[name]["url"]).status_code, HTTPStatus.NOT_FOUND)

    def test_quick_actions_anonymous(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
