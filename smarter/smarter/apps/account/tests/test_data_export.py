"""
Test Download My Data: :mod:`smarter.apps.account.data_export`, the.

:class:`~smarter.apps.account.models.DataExport` model, and its Celery tasks.

Every test runs against an in-memory provider, whose storage keeps the zip files in memory, and an
in-memory email service, so nothing reaches S3 or sends real email.
"""

import io
import zipfile
from datetime import timedelta
from unittest.mock import patch

from django.utils import timezone

from smarter.apps.account import data_export
from smarter.apps.account.data_export import (
    DATA_EXPORT_LINK_SECONDS,
    DATA_EXPORTS_PER_DAY,
    REDACTED_SECRET_VALUE,
    DataExportOverviewResponse,
    DataExportStartRefused,
    DataExportStatusResponse,
    ExportResource,
    delete_expired_data_exports,
    manifest_path,
    owned_resources,
    redact_secret,
    run_data_export,
    start_data_export,
)
from smarter.apps.account.models import (
    DataExport,
    DataExportStatus,
    DataExportStep,
    User,
)
from smarter.apps.account.tasks import (
    create_data_export,
)
from smarter.apps.account.tasks import (
    delete_expired_data_exports as delete_expired_data_exports_task,
)
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.connection.tests.factories import secret_factory
from smarter.apps.infrastructure.providers import configure_provider
from smarter.apps.infrastructure.providers.memory import InMemoryProvider
from smarter.apps.infrastructure.services import (
    InMemoryEmailService,
    configure_email,
)
from smarter.apps.secret.models import Secret

SECRET_VALUE = "sk-data-export-test-value-1234567890"
TASK = "smarter.apps.account.tasks.create_data_export"


class TestDataExport(TestAccountMixin):
    """Export a user's manifests, zip them, save them to private storage, and email the link."""

    secret_name: str
    secret: Secret

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.secret_name = f"data_export_secret_{cls.hash_suffix}"
        cls.secret = secret_factory(cls.non_admin_user_profile, cls.secret_name, SECRET_VALUE)

    @classmethod
    def tearDownClass(cls):
        cls.secret.delete()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.provider = InMemoryProvider()
        configure_provider(lambda: self.provider)
        self.addCleanup(configure_provider, None)
        self.email = InMemoryEmailService()
        configure_email(lambda: self.email)
        self.addCleanup(configure_email, None)
        self.user = self.non_admin_user
        self.addCleanup(lambda: DataExport.objects.filter(user=self.user).delete())

    def new_export(self) -> DataExport:
        return DataExport.objects.create(user=self.user)

    def archive(self, export: DataExport) -> zipfile.ZipFile:
        stored = self.provider.storage.objects[export.object_key]
        return zipfile.ZipFile(io.BytesIO(stored.content))

    # --------------------------------------------------------------------------
    # running an export
    # --------------------------------------------------------------------------
    def test_run_exports_zips_and_emails(self):
        """Each manifest is zipped with a README, saved to private storage, and the link is emailed."""
        export = run_data_export(self.new_export().pk)

        self.assertEqual(export.status, DataExportStatus.SUCCEEDED)
        self.assertEqual(export.step, DataExportStep.DONE)
        self.assertGreaterEqual(export.resource_count, 1)
        self.assertEqual(export.manifest_count, export.resource_count)
        self.assertEqual(export.failed_count, 0)
        self.assertIsNotNone(export.completed_at)
        self.assertTrue(export.object_key.startswith(f"data-exports/{self.user.pk}/{export.pk}/"))
        self.assertGreater(export.size_bytes, 0)
        link_seconds = export.link_expires_in().total_seconds()  # type: ignore[union-attr]
        self.assertAlmostEqual(link_seconds, DATA_EXPORT_LINK_SECONDS, delta=60)

        stored = self.provider.storage.objects[export.object_key]
        self.assertEqual(stored.content_type, "application/zip")
        self.assertEqual(len(stored.content), export.size_bytes)

        names = self.archive(export).namelist()
        folder = names[0].split("/")[0]
        self.assertTrue(folder.startswith("smarter-data-"))
        self.assertIn(f"{folder}/README.md", names)
        account_number = self.non_admin_user_profile.account.account_number
        self.assertIn(f"{folder}/{account_number}/Secret/{self.secret_name}.yaml", names)

        self.assertEqual(len(self.email.outbox), 1)
        sent = self.email.outbox[0]
        self.assertEqual(sent.recipients, [self.user.email])
        self.assertEqual(sent.bcc, [])
        self.assertIn("storage.memory.example", sent.body)
        self.assertIn(".zip", sent.body)

    def test_secret_values_are_redacted(self):
        """A Secret's value is never in the zip file."""
        export = run_data_export(self.new_export().pk)
        archive = self.archive(export)
        everything = b"".join(archive.read(name) for name in archive.namelist())
        self.assertNotIn(SECRET_VALUE.encode(), everything)
        secret_files = [name for name in archive.namelist() if name.endswith(f"/Secret/{self.secret_name}.yaml")]
        secret_yaml = archive.read(secret_files[0]).decode()
        self.assertIn(REDACTED_SECRET_VALUE, secret_yaml)
        self.assertIn(f"name: {self.secret_name}", secret_yaml)

    def test_resources_without_a_manifest_are_listed(self):
        """A resource that can't be described is counted, and named in the README."""
        with patch("smarter.apps.dashboard.resource_detail.manifest_data", return_value=(None, "it is broken")):
            export = run_data_export(self.new_export().pk)
        self.assertEqual(export.status, DataExportStatus.SUCCEEDED)
        self.assertEqual(export.manifest_count, 0)
        self.assertEqual(export.failed_count, export.resource_count)
        archive = self.archive(export)
        readme = archive.read(archive.namelist()[0]).decode()
        self.assertIn("Resources that could not be exported", readme)
        self.assertIn("it is broken", readme)

    def test_progress_is_saved_while_manifests_are_written(self):
        """The manifest count is saved every few manifests, so that the console's progress bar moves."""
        with (
            patch.object(data_export, "MANIFEST_PROGRESS_INTERVAL", 1),
            patch.object(data_export, "update_export", wraps=data_export.update_export) as update,
        ):
            run_data_export(self.new_export().pk)
        counts = [call.kwargs["manifest_count"] for call in update.call_args_list if "manifest_count" in call.kwargs]
        self.assertGreaterEqual(len(counts), 2)

    def test_storage_failure(self):
        """An export that can't be saved fails, says why, and sends no email."""
        self.provider.storage.fail = "the bucket is gone"
        export = run_data_export(self.new_export().pk)
        self.assertEqual(export.status, DataExportStatus.FAILED)
        self.assertEqual(export.step, DataExportStep.UPLOAD)
        self.assertIn("the bucket is gone", export.error)
        self.assertIsNotNone(export.completed_at)
        self.assertEqual(self.email.outbox, [])

    def test_email_failure(self):
        """An export whose email can't be sent fails."""
        self.email.fail = "SMTP is down"
        export = run_data_export(self.new_export().pk)
        self.assertEqual(export.status, DataExportStatus.FAILED)
        self.assertEqual(export.step, DataExportStep.EMAIL)
        self.assertTrue(export.error)

    def test_finished_export_is_not_run_again(self):
        """An export that already finished is left as it is."""
        export = self.new_export()
        DataExport.objects.filter(pk=export.pk).update(status=DataExportStatus.FAILED, error="earlier")
        again = run_data_export(export.pk)
        self.assertEqual(again.error, "earlier")
        self.assertEqual(self.provider.storage.objects, {})

    def test_task(self):
        """The Celery task runs the export, and returns its status."""
        export = self.new_export()
        self.assertEqual(create_data_export(export.pk), DataExportStatus.SUCCEEDED)

    # --------------------------------------------------------------------------
    # starting an export
    # --------------------------------------------------------------------------
    def test_start_queues_the_task_once(self):
        """Starting an export queues its task; starting again while it runs returns the same export."""
        with patch(TASK) as task:
            export, started = start_data_export(self.user)
            again, started_again = start_data_export(self.user)
        self.assertTrue(started)
        self.assertFalse(started_again)
        self.assertEqual(again.pk, export.pk)
        task.delay.assert_called_once_with(export.pk)

    def test_start_after_a_stale_export(self):
        """An export that was abandoned doesn't keep the user from starting another."""
        stale = self.new_export()
        long_ago = timezone.now() - timedelta(hours=1)
        DataExport.objects.filter(pk=stale.pk).update(created_at=long_ago)
        stale.refresh_from_db()
        self.assertTrue(stale.is_stale)
        self.assertFalse(stale.is_in_progress)
        with patch(TASK):
            export, started = start_data_export(self.user)
        self.assertTrue(started)
        self.assertNotEqual(export.pk, stale.pk)

    def test_start_is_limited_per_day(self):
        """A user may start only a few exports a day."""
        for _ in range(DATA_EXPORTS_PER_DAY):
            DataExport.objects.create(user=self.user, status=DataExportStatus.SUCCEEDED)
        with patch(TASK) as task, self.assertRaises(DataExportStartRefused):
            start_data_export(self.user)
        task.delay.assert_not_called()
        overview = DataExportOverviewResponse.for_user(self.user)
        self.assertEqual(overview.exports_left_today, 0)

    def test_start_needs_an_email_address(self):
        """A user without an email address can't be sent the link."""
        user = User(username=f"no_email_{self.hash_suffix}", email="")
        with (
            patch.object(data_export, "latest_data_export", return_value=None),
            self.assertRaises(DataExportStartRefused),
        ):
            start_data_export(user)

    def test_overview(self):
        """The overview names the address, the link's lifetime, the limit, and the latest export."""
        overview = DataExportOverviewResponse.for_user(self.user)
        self.assertEqual(overview.email, self.user.email)
        self.assertEqual(overview.link_hours, 24)
        self.assertEqual(overview.exports_left_today, DATA_EXPORTS_PER_DAY)
        self.assertIsNone(overview.latest)

        export = self.new_export()
        dumped = DataExportOverviewResponse.for_user(self.user).model_dump(mode="json")
        self.assertEqual(dumped["latest"]["id"], export.pk)
        self.assertEqual(dumped["latest"]["status"], "queued")
        self.assertIn("exportsLeftToday", dumped)
        self.assertIsNone(dumped["latest"]["expiresAt"])

    def test_status_response(self):
        """An export's progress is camelCase JSON."""
        export = run_data_export(self.new_export().pk)
        dumped = DataExportStatusResponse.from_model(export).model_dump(mode="json")
        self.assertEqual(dumped["status"], "succeeded")
        self.assertEqual(dumped["manifestCount"], export.manifest_count)
        self.assertEqual(dumped["email"], self.user.email)
        self.assertIsNotNone(dumped["expiresAt"])

    # --------------------------------------------------------------------------
    # cleaning up
    # --------------------------------------------------------------------------
    def test_delete_expired_data_exports(self):
        """The zip files of expired links are deleted, and the exports are kept as a record."""
        export = run_data_export(self.new_export().pk)
        self.assertEqual(delete_expired_data_exports(), 0)
        DataExport.objects.filter(pk=export.pk).update(expires_at=timezone.now() - timedelta(minutes=1))
        self.assertEqual(delete_expired_data_exports_task(), 1)
        export.refresh_from_db()
        self.assertEqual(export.object_key, "")
        self.assertEqual(self.provider.storage.objects, {})
        self.assertIsNone(export.link_expires_in())

    def test_delete_expired_keeps_going_after_a_failure(self):
        """A file that can't be deleted is tried again next time."""
        export = run_data_export(self.new_export().pk)
        DataExport.objects.filter(pk=export.pk).update(expires_at=timezone.now() - timedelta(minutes=1))
        self.provider.storage.fail = "no"
        self.assertEqual(delete_expired_data_exports(), 0)
        export.refresh_from_db()
        self.assertTrue(export.object_key)

    def test_delete_expired_task_without_storage(self):
        """The task does nothing while private storage isn't ready."""
        self.provider.ready = False
        self.assertEqual(delete_expired_data_exports_task(), 0)

    # --------------------------------------------------------------------------
    # helpers
    # --------------------------------------------------------------------------
    def test_owned_resources(self):
        """The user's own resources are found once each, and another user's aren't."""
        resources = owned_resources(self.user)
        secrets = [resource for resource in resources if resource.name == self.secret_name]
        self.assertEqual(len(secrets), 1)
        self.assertEqual(secrets[0].kind, "Secret")
        self.assertEqual(secrets[0].account_number, self.non_admin_user_profile.account.account_number)
        others = owned_resources(self.admin_user)
        self.assertNotIn(self.secret_name, [resource.name for resource in others])

    def test_owned_resources_without_a_kind(self):
        """A resource whose kind isn't known is left out."""
        with patch("smarter.apps.dashboard.resource_detail.kind_of_instance", return_value=None):
            self.assertEqual(owned_resources(self.user), [])

    def test_redact_secret(self):
        """Only a Secret's spec.config.value is replaced, and a malformed manifest is left alone."""
        manifest = {"spec": {"config": {"value": "x", "description": "kept"}}}
        self.assertEqual(
            redact_secret(manifest)["spec"]["config"], {"value": REDACTED_SECRET_VALUE, "description": "kept"}
        )
        self.assertEqual(redact_secret({"spec": None}), {"spec": None})
        self.assertEqual(redact_secret({"spec": {"config": "x"}}), {"spec": {"config": "x"}})
        self.assertEqual(redact_secret({"spec": {"config": {}}}), {"spec": {"config": {}}})

    def test_manifest_path(self):
        """A path is unique, and safe for any file system."""
        taken: set[str] = set()
        first = ExportResource(kind="Guardrail", instance=self.secret, account_number="1234")
        self.assertEqual(manifest_path(first, taken), f"1234/Guardrail/{self.secret_name}.yaml")
        self.assertEqual(manifest_path(first, taken), f"1234/Guardrail/{self.secret_name}_{self.secret.pk}.yaml")

        class Unnamed:
            name = "../../"
            pk = 7

        unnamed = ExportResource(kind="Secret", instance=Unnamed(), account_number="1234")  # type: ignore[arg-type]
        self.assertEqual(manifest_path(unnamed, taken), "1234/Secret/unnamed.yaml")

    def test_model(self):
        """An export's state, as the dialog and the admin read it."""
        export = self.new_export()
        self.assertIn(self.user.username, str(export))
        self.assertTrue(export.is_in_progress)
        self.assertFalse(export.is_stale)
        self.assertIsNone(export.link_expires_in())
        export.status = DataExportStatus.SUCCEEDED
        self.assertTrue(export.is_finished)
        self.assertFalse(export.is_stale)
        self.assertFalse(export.is_in_progress)
        export.expires_at = timezone.now() + timedelta(hours=1)
        self.assertGreater(export.link_expires_in().total_seconds(), 3500)  # type: ignore[union-attr]
