"""Test the web server's startup banner."""

import io
import os
from unittest.mock import patch

from django.test import override_settings

from smarter.lib.unittest.base_classes import SmarterTestBase

from ..startup_banner import (
    LOGO,
    LOGO_WIDTH,
    banner_facts,
    mask_url,
    platform_summary,
    print_startup_banner,
    startup_banner,
)

MODULE = "smarter.common.helpers.startup_banner"


class TestStartupBanner(SmarterTestBase):
    """Test the web server's startup banner."""

    def test_logo_lines_are_the_same_width(self):
        self.assertTrue(all(len(line) == LOGO_WIDTH for line in LOGO))

    def test_mask_url_masks_the_password(self):
        self.assertEqual(mask_url("redis://:secret@smarter-redis:6379/1"), "redis://:**@smarter-redis:6379/1")
        self.assertEqual(mask_url("redis://user:secret@host/0"), "redis://user:**@host/0")

    def test_mask_url_without_a_password(self):
        self.assertEqual(mask_url("redis://smarter-redis:6379/1"), "redis://smarter-redis:6379/1")
        self.assertEqual(mask_url(None), "unknown")
        self.assertEqual(mask_url(""), "unknown")

    def test_banner_facts(self):
        facts = dict(banner_facts())
        self.assertEqual(
            list(facts),
            ["environment", "url", "database", "cache", "sessions", "broker", "log level", "debug", "runtime"],
        )
        self.assertTrue(facts["database"].startswith("mysql://"))
        self.assertIn(facts["debug"], ("ON", "OFF"))
        self.assertIn("python", facts["runtime"])

    def test_banner_never_shows_a_password(self):
        with override_settings(CELERY_BROKER_URL="redis://:hunter2@broker:6379/1"):
            banner = startup_banner()
        self.assertNotIn("hunter2", banner)
        self.assertIn("redis://:**@broker:6379/1", banner)

    def test_a_failing_setting_shows_unknown(self):
        with patch(f"{MODULE}._database_url", side_effect=RuntimeError("boom")):
            self.assertEqual(dict(banner_facts())["database"], "unknown")

    def test_banner_without_color(self):
        banner = startup_banner(color=False)
        self.assertNotIn("\033[", banner)
        self.assertIn("S  M  A  R  T  E  R", banner)
        for line in LOGO:
            self.assertIn(line, banner)
        self.assertIn("smarter@", banner)

    def test_banner_with_color(self):
        banner = startup_banner(color=True)
        self.assertIn("\033[38;5;202m", banner)
        self.assertIn("\033[38;5;220m", banner)
        self.assertIn("\033[0m", banner)

    def test_print_startup_banner_honors_no_color(self):
        out = io.StringIO()
        with patch.dict(os.environ, {"NO_COLOR": "1"}), patch("sys.stdout", out):
            print_startup_banner()
        self.assertIn("smarter@", out.getvalue())
        self.assertNotIn("\033[", out.getvalue())

    def test_print_startup_banner_swallows_errors(self):
        out = io.StringIO()
        with patch(f"{MODULE}.startup_banner", side_effect=RuntimeError("boom")), patch("sys.stdout", out):
            print_startup_banner()
        self.assertEqual(out.getvalue(), "")

    def test_only_the_first_worker_prints(self):
        out = io.StringIO()
        with patch(f"{MODULE}.is_first_worker", return_value=False) as first, patch("sys.stdout", out):
            print_startup_banner()
        first.assert_called_once_with("startup-banner")
        self.assertEqual(out.getvalue(), "")

    def test_platform_summary_on_linux(self):
        with (
            patch(f"{MODULE}.platform.system", return_value="Linux"),
            patch(f"{MODULE}.platform.machine", return_value="x86_64"),
            patch(f"{MODULE}.platform.freedesktop_os_release", return_value={"ID": "amzn", "VERSION_ID": "2023"}),
        ):
            self.assertEqual(platform_summary(), "linux  ·  amzn 2023  ·  x86_64")

    def test_platform_summary_without_os_release(self):
        with (
            patch(f"{MODULE}.platform.system", return_value="Darwin"),
            patch(f"{MODULE}.platform.machine", return_value="arm64"),
            patch(f"{MODULE}.platform.freedesktop_os_release", side_effect=OSError),
        ):
            self.assertEqual(platform_summary(), "darwin  ·  arm64")

    def test_banner_shows_the_platform_summary(self):
        with patch(f"{MODULE}.platform_summary", return_value="linux  ·  test 1  ·  x86_64"):
            banner = startup_banner(color=False)
        self.assertIn("linux  ·  test 1  ·  x86_64", banner)
