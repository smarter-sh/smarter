"""Test the dashboard's "Recent Activity" api view, :mod:`smarter.apps.dashboard.views.views.api.activity`."""

from http import HTTPStatus

from django.test import Client
from django.urls import reverse

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.dashboard.views.views.api.activity import (
    MAX_ITEMS,
    MAX_MESSAGE_LENGTH,
    journal_message,
)
from smarter.apps.dashboard.views.views.api.urls import DashboardApiReverseNames
from smarter.lib import json
from smarter.lib.journal.models import SAMJournal

from ..const import namespace


class TestActivityApiView(TestAccountMixin):
    """Test ActivityView, which lists the user's recent manifest commands from the journal."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.addCleanup(self.client.logout)
        self.client.force_login(self.admin_user)
        self.url = reverse(f"{namespace}:{DashboardApiReverseNames.namespace}:{DashboardApiReverseNames.activity}")

    def journal(self, user, command: str, status_code: int = HTTPStatus.OK, response=None) -> SAMJournal:
        entry = SAMJournal.objects.create(
            user=user,
            thing="Plugin",
            command=command,
            request={},
            response=response if response is not None else {"message": f"Plugin test {command} successfully"},
            status_code=status_code,
        )
        self.addCleanup(entry.delete)
        return entry

    def activity(self) -> dict:
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:300])
        return json.loads(response.content)

    def test_journal_message(self):
        self.assertEqual(journal_message({"message": "applied"}), "applied")
        self.assertEqual(journal_message({"error": {"description": "invalid manifest"}}), "invalid manifest")
        self.assertEqual(journal_message({"message": "x" * 1000}), "x" * MAX_MESSAGE_LENGTH)
        self.assertIsNone(journal_message({"data": {}}))
        self.assertIsNone(journal_message(["not", "a", "dict"]))

    def test_activity(self):
        """Test that the user's commands that change something are listed, newest first."""
        self.journal(self.admin_user, "apply")
        self.journal(self.admin_user, "get")
        self.journal(
            self.admin_user,
            "delete",
            status_code=HTTPStatus.NOT_FOUND,
            response={"error": {"description": "Plugin test not found"}},
        )
        data = self.activity()
        self.assertIsInstance(data["journal_enabled"], bool)
        commands = [(item["command"], item["status_code"], item["message"]) for item in data["items"]]
        self.assertEqual(
            commands[:2],
            [("delete", 404, "Plugin test not found"), ("apply", 200, "Plugin test apply successfully")],
        )
        self.assertNotIn("get", [item["command"] for item in data["items"]])

    def test_activity_is_the_users_own(self):
        self.journal(self.non_admin_user, "deploy")
        self.assertNotIn("deploy", [item["command"] for item in self.activity()["items"]])

    def test_activity_is_limited(self):
        for _ in range(MAX_ITEMS + 2):
            self.journal(self.admin_user, "apply")
        self.assertEqual(len(self.activity()["items"]), MAX_ITEMS)

    def test_activity_anonymous(self):
        self.client.logout()
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
