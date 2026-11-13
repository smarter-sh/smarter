"""Test the REST api's Download My Data, :mod:`smarter.apps.account.api.v1.views.data_export`."""

from http import HTTPStatus
from unittest.mock import patch

from rest_framework.test import APIClient

from smarter.apps.account.data_export import DATA_EXPORTS_PER_DAY
from smarter.apps.account.models import DataExport, DataExportStatus
from smarter.apps.api.v1.contract.tests.mixins import OpenApiResponseMixin
from smarter.apps.api.v1.tests.base_class import ApiV1TestBase

URL = "/api/v1/accounts/data-exports/"
TASK = "smarter.apps.account.tasks.create_data_export"


class TestDataExportViews(OpenApiResponseMixin, ApiV1TestBase):
    """Test the data exports' overview, start and progress, with an api key.

    The Celery task is never queued.
    """

    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_key}")
        self.addCleanup(DataExport.objects.filter(user=self.admin_user).delete)
        patcher = patch(TASK)
        self.task = patcher.start()
        self.addCleanup(patcher.stop)

    def test_overview(self):
        """The overview names the address and how many exports are left today."""
        response = self.client.get(URL)
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:300])
        data = response.json()
        self.assertValidResponse("/accounts/data-exports/", "get", data)
        self.assertEqual(data["email"], self.admin_user.email)
        self.assertEqual(data["exportsPerDay"], DATA_EXPORTS_PER_DAY)
        self.assertIsNone(data["latest"])

    def test_start_and_progress(self):
        """An export is started, 202; starting again returns it, 200; its progress is read by id."""
        response = self.client.post(URL)
        self.assertEqual(response.status_code, HTTPStatus.ACCEPTED, response.content[:300])
        self.assertValidResponse("/accounts/data-exports/", "post", response.json(), HTTPStatus.ACCEPTED)
        export_id = response.json()["id"]
        self.assertEqual(response.json()["status"], "queued")
        self.task.delay.assert_called_once_with(export_id)

        again = self.client.post(URL)
        self.assertEqual(again.status_code, HTTPStatus.OK)
        self.assertValidResponse("/accounts/data-exports/", "post", again.json(), HTTPStatus.OK)
        self.assertEqual(again.json()["id"], export_id)

        progress = self.client.get(f"{URL}{export_id}/")
        self.assertEqual(progress.status_code, HTTPStatus.OK)
        self.assertValidResponse("/accounts/data-exports/{export_id}/", "get", progress.json())
        self.assertEqual(progress.json()["id"], export_id)
        self.assertEqual(self.client.get(URL).json()["latest"]["id"], export_id)

    def test_refused(self):
        """A user who started too many exports today is refused, 429."""
        for _ in range(DATA_EXPORTS_PER_DAY):
            DataExport.objects.create(user=self.admin_user, status=DataExportStatus.SUCCEEDED)
        response = self.client.post(URL)
        self.assertEqual(response.status_code, HTTPStatus.TOO_MANY_REQUESTS)
        self.assertValidResponse("/accounts/data-exports/", "post", response.json(), HTTPStatus.TOO_MANY_REQUESTS)
        self.assertIn("detail", response.json())
        self.task.delay.assert_not_called()

    def test_someone_elses_export(self):
        """Another user's export, or one that doesn't exist, is a 404."""
        export = DataExport.objects.create(user=self.non_admin_user, status=DataExportStatus.SUCCEEDED)
        self.addCleanup(export.delete)
        response = self.client.get(f"{URL}{export.pk}/")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertEqual(response.json(), {"detail": f"You have no data export {export.pk}."})
        self.assertEqual(self.client.get(f"{URL}999999999/").status_code, HTTPStatus.NOT_FOUND)
