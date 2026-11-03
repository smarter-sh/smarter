"""Test :mod:`smarter.apps.doodle.admin`."""

from unittest.mock import MagicMock, patch

from django.test import RequestFactory

from smarter.apps.dashboard.admin import smarter_restricted_admin_site
from smarter.apps.doodle.admin import (
    DoodleAdmin,
    DoodleEditorRunAdmin,
    DoodleThemeAdmin,
)
from smarter.apps.doodle.models import (
    Doodle,
    DoodleEditorRun,
    DoodleEditorRunStatus,
    DoodleSource,
    DoodleStatus,
    DoodleTheme,
)
from smarter.apps.doodle.planner import plan_doodle
from smarter.apps.doodle.regions import DoodleRegion

from .mixins import QUIET_DAY, DoodleTestMixin


class TestDoodleAdmin(DoodleTestMixin):
    """A superuser overrides a day's doodle in the admin."""

    def setUp(self):
        super().setUp()
        self.addCleanup(self.delete_doodles, QUIET_DAY)
        self.doodle_admin = DoodleAdmin(Doodle, smarter_restricted_admin_site)
        self.request = RequestFactory().post("/admin/")
        self.request.user = MagicMock(username="test_superuser")

    def test_choosing_another_theme(self):
        doodle = plan_doodle(QUIET_DAY, DoodleRegion.US)
        doodle.theme = self.theme("pi-day")
        form = MagicMock(changed_data=["theme"])
        self.doodle_admin.save_model(self.request, doodle, form, change=True)
        doodle.refresh_from_db()
        self.assertEqual(doodle.source, DoodleSource.HUMAN)
        self.assertEqual(doodle.title, "Pi Day")
        self.assertEqual(doodle.artwork, doodle.theme.artwork)
        self.assertIn("test_superuser", doodle.reason)

    def test_changing_only_the_caption(self):
        doodle = plan_doodle(QUIET_DAY, DoodleRegion.CA)
        doodle.caption = "Hello!"
        form = MagicMock(changed_data=["caption"])
        self.doodle_admin.save_model(self.request, doodle, form, change=True)
        doodle.refresh_from_db()
        self.assertEqual(doodle.caption, "Hello!")
        self.assertEqual(doodle.source, DoodleSource.HUMAN)

    def test_preview(self):
        doodle = plan_doodle(QUIET_DAY, DoodleRegion.MX)
        html = DoodleAdmin.preview(doodle)
        self.assertIn(doodle.artwork.sha256, html)
        self.assertIn("<img", html)

    def test_approve_and_reject(self):
        doodle = plan_doodle(QUIET_DAY, DoodleRegion.AFRICA)
        Doodle.objects.filter(pk=doodle.pk).update(status=DoodleStatus.PROPOSED, source=DoodleSource.LLM)
        queryset = Doodle.objects.filter(pk=doodle.pk)
        with patch.object(self.doodle_admin, "message_user") as message_user:
            self.doodle_admin.approve(self.request, queryset)
        message_user.assert_called_once_with(self.request, "Approved 1 doodles.")
        doodle.refresh_from_db()
        self.assertEqual(doodle.status, DoodleStatus.APPROVED)
        self.assertEqual(doodle.source, DoodleSource.LLM)
        with patch.object(self.doodle_admin, "message_user"):
            self.doodle_admin.reject(self.request, queryset)
        doodle.refresh_from_db()
        self.assertEqual(doodle.status, DoodleStatus.REJECTED)

    def test_editor_runs_are_read_only(self):
        run_admin = DoodleEditorRunAdmin(DoodleEditorRun, smarter_restricted_admin_site)
        self.assertFalse(run_admin.has_add_permission(self.request))
        self.assertFalse(run_admin.has_change_permission(self.request))
        run = DoodleEditorRun.objects.create(date=QUIET_DAY, status=DoodleEditorRunStatus.FAILED, error="down")
        self.addCleanup(run.delete)
        self.assertEqual(str(run), f"{QUIET_DAY} failed")

    def test_themes_are_read_only(self):
        theme_admin = DoodleThemeAdmin(DoodleTheme, smarter_restricted_admin_site)
        self.assertFalse(theme_admin.has_add_permission(self.request))
        self.assertFalse(theme_admin.has_change_permission(self.request))

    def test_str(self):
        doodle = plan_doodle(QUIET_DAY, DoodleRegion.GLOBAL)
        self.assertEqual(str(doodle), f"{QUIET_DAY} global default")
        self.assertEqual(str(doodle.theme), "default")
        self.assertEqual(str(doodle.artwork), doodle.artwork.sha256[:12])
