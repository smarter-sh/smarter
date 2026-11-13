"""Test :mod:`smarter.apps.doodle.admin`."""

import datetime
from http import HTTPStatus
from unittest.mock import MagicMock, patch

from django.core.exceptions import PermissionDenied
from django.test import Client, RequestFactory
from django.utils import timezone

from smarter.apps.account.tests.mixins import TestAccountMixin
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
from smarter.lib.typing import required

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
        assert doodle is not None
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
        assert doodle is not None
        doodle.caption = "Hello!"
        form = MagicMock(changed_data=["caption"])
        self.doodle_admin.save_model(self.request, doodle, form, change=True)
        doodle.refresh_from_db()
        self.assertEqual(doodle.caption, "Hello!")
        self.assertEqual(doodle.source, DoodleSource.HUMAN)

    def test_preview(self):
        doodle = plan_doodle(QUIET_DAY, DoodleRegion.MX)
        assert doodle is not None
        html = DoodleAdmin.preview(doodle)
        self.assertIn(doodle.artwork.sha256, html)
        self.assertIn("<img", html)

    def test_approve_and_reject(self):
        doodle = plan_doodle(QUIET_DAY, DoodleRegion.AFRICA)
        assert doodle is not None
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
        assert doodle is not None
        self.assertEqual(str(doodle), f"{QUIET_DAY} global default")
        self.assertEqual(str(doodle.theme), "default")
        self.assertEqual(str(doodle.artwork), doodle.artwork.sha256[:12])


class TestDoodleWeekPreview(DoodleTestMixin, TestAccountMixin):
    """The week's preview shows every region's doodle of every planned day, and approves or rejects them."""

    doodle_admin: DoodleAdmin
    url: str

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.doodle_admin = DoodleAdmin(Doodle, smarter_restricted_admin_site)
        cls.url = cls.doodle_admin.preview_url()

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.client.force_login(self.admin_user)
        self.addCleanup(self.client.logout)
        # the preview starts yesterday in UTC, so its days are the dev platform's too: a far day is ours.
        self.day = timezone.now().date() + datetime.timedelta(days=4000)
        self.addCleanup(self.delete_doodles, self.day)
        self.doodle = required(plan_doodle(self.day, DoodleRegion.OCEANIA), "doodle")
        Doodle.objects.filter(pk=self.doodle.pk).update(status=DoodleStatus.PROPOSED, source=DoodleSource.LLM)

    def test_the_url(self):
        self.assertEqual(self.url, "/admin/doodle/doodle/preview/")

    def test_the_list_links_to_the_preview(self):
        response = self.client.get("/admin/doodle/doodle/")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.content.decode()
        self.assertIn(f'href="{self.url}"', content)
        self.assertIn("Preview the week", content)

    def test_the_preview(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertIn("Doodles of the week", response.content.decode())
        days = response.context["days"]
        ours = [day for day in days if day.date == self.day][0]
        self.assertEqual([cell.region for cell in ours.cells], DoodleRegion.values)
        cell = ours.cells[DoodleRegion.values.index(DoodleRegion.OCEANIA)]
        self.assertEqual(cell.doodle.pk, self.doodle.pk)
        self.assertTrue(cell.is_default)
        self.assertIn(cell.image_url, response.content.decode())
        self.assertIsNone(ours.cells[0].doodle)
        self.assertIn(f'value="{self.doodle.pk}"', response.content.decode())

    def test_approve_and_reject_from_the_preview(self):
        response = self.client.post(self.url, {"doodle_id": self.doodle.pk, "action": "approve"})
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(response["Location"], self.url)
        self.doodle.refresh_from_db()
        self.assertEqual(self.doodle.status, DoodleStatus.APPROVED)
        self.client.post(self.url, {"doodle_id": self.doodle.pk, "action": "reject"})
        self.doodle.refresh_from_db()
        self.assertEqual(self.doodle.status, DoodleStatus.REJECTED)

    def test_a_bad_request_changes_nothing(self):
        for data in [{"doodle_id": self.doodle.pk, "action": "delete"}, {"doodle_id": 0, "action": "approve"}, {}]:
            with self.subTest(data=data):
                response = self.client.post(self.url, data, follow=True)
                self.assertIn("Choose a doodle, and approve or reject it.", response.content.decode())
                self.doodle.refresh_from_db()
                self.assertEqual(self.doodle.status, DoodleStatus.PROPOSED)

    def test_only_superusers(self):
        client = Client()
        client.force_login(self.non_admin_user)
        response = client.get(self.url)
        self.assertNotEqual(response.status_code, HTTPStatus.OK)
        request = RequestFactory().post(self.url, {"doodle_id": self.doodle.pk, "action": "approve"})
        request.user = self.non_admin_user
        with self.assertRaises(PermissionDenied):
            self.doodle_admin.week_preview_view(request)
        with patch.object(DoodleAdmin, "has_view_permission", return_value=True):
            with self.assertRaises(PermissionDenied):
                self.doodle_admin.week_preview_view(request)
        self.doodle.refresh_from_db()
        self.assertEqual(self.doodle.status, DoodleStatus.PROPOSED)

    def test_nothing_planned(self):
        with patch.object(DoodleAdmin, "preview_days", return_value=[]):
            response = self.client.get(self.url)
        self.assertIn("No doodles are planned.", response.content.decode())
