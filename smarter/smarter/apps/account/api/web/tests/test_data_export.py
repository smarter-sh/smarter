"""
Test the user menu's Download My Data api: :mod:`smarter.apps.account.api.web.data_export`.

The Celery task is patched, so no export runs: the views' job is to start one, refuse one, and report progress.
"""

from http import HTTPStatus
from unittest.mock import patch

from django.test import Client
from django.urls import reverse

from smarter.apps.account.api.web.urls import AccountApiWebReverseNames
from smarter.apps.account.data_export import DATA_EXPORTS_PER_DAY
from smarter.apps.account.models import DataExport, DataExportStatus
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.lib import json

TASK = "smarter.apps.account.tasks.create_data_export"


class TestDataExportViews(TestAccountMixin):
    """Start a data export, and follow its progress, as the console's dialog does."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.client.force_login(self.non_admin_user)
        self.addCleanup(lambda: DataExport.objects.filter(user__in=[self.non_admin_user, self.admin_user]).delete())
        self.url = reverse(f"{AccountApiWebReverseNames.namespace}:{AccountApiWebReverseNames.data_export}")

    def detail_url(self, export_id: int) -> str:
        name = f"{AccountApiWebReverseNames.namespace}:{AccountApiWebReverseNames.data_export_detail}"
        return reverse(name, kwargs={"export_id": export_id})

    def test_url(self):
        """The api is under the console's account api."""
        self.assertEqual(self.url, "/api/web/account/data-export/")
        self.assertEqual(self.detail_url(3), "/api/web/account/data-export/3/")

    def test_overview(self):
        """GET says where the link goes, and how many exports are left today."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        body = json.loads(response.content)
        self.assertEqual(body["email"], self.non_admin_user.email)
        self.assertEqual(body["linkHours"], 24)
        self.assertEqual(body["exportsPerDay"], DATA_EXPORTS_PER_DAY)
        self.assertIsNone(body["latest"])

    def test_start_and_poll(self):
        """POST starts an export (202), again returns it (200), and its detail reports its progress."""
        with patch(TASK) as task:
            response = self.client.post(self.url)
            again = self.client.post(self.url)
        self.assertEqual(response.status_code, HTTPStatus.ACCEPTED)
        self.assertEqual(again.status_code, HTTPStatus.OK)
        started = json.loads(response.content)
        self.assertEqual(started["status"], "queued")
        self.assertEqual(json.loads(again.content)["id"], started["id"])
        task.delay.assert_called_once_with(started["id"])

        progress = self.client.get(self.detail_url(started["id"]))
        self.assertEqual(progress.status_code, HTTPStatus.OK)
        self.assertEqual(json.loads(progress.content)["step"], "queued")

    def test_refused(self):
        """POST answers 429, with the reason, once the day's exports are used up."""
        for _ in range(DATA_EXPORTS_PER_DAY):
            DataExport.objects.create(user=self.non_admin_user, status=DataExportStatus.SUCCEEDED)
        with patch(TASK) as task:
            response = self.client.post(self.url)
        self.assertEqual(response.status_code, HTTPStatus.TOO_MANY_REQUESTS)
        self.assertIn("error", json.loads(response.content))
        task.delay.assert_not_called()

    def test_another_users_export_is_not_found(self):
        """A user can't see another user's export."""
        export = DataExport.objects.create(user=self.admin_user)
        response = self.client.get(self.detail_url(export.pk))
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_anonymous(self):
        """An anonymous user is sent to sign in."""
        response = Client().get(self.url)
        self.assertNotEqual(response.status_code, HTTPStatus.OK)
