"""Test :mod:`smarter.apps.doodle.admin`."""

from unittest.mock import MagicMock

from django.test import RequestFactory

from smarter.apps.dashboard.admin import smarter_restricted_admin_site
from smarter.apps.doodle.admin import DoodleAdmin, DoodleThemeAdmin
from smarter.apps.doodle.models import Doodle, DoodleSource, DoodleTheme
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

    def test_themes_are_read_only(self):
        theme_admin = DoodleThemeAdmin(DoodleTheme, smarter_restricted_admin_site)
        self.assertFalse(theme_admin.has_add_permission(self.request))
        self.assertFalse(theme_admin.has_change_permission(self.request))

    def test_str(self):
        doodle = plan_doodle(QUIET_DAY, DoodleRegion.GLOBAL)
        self.assertEqual(str(doodle), f"{QUIET_DAY} global default")
        self.assertEqual(str(doodle.theme), "default")
        self.assertEqual(str(doodle.artwork), doodle.artwork.sha256[:12])
