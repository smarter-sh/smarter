"""Test reading the installed web console release's source: :mod:`smarter.lib.unittest.console_source`."""

import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from django.test import override_settings

from smarter.lib.unittest import console_source as source
from smarter.lib.unittest.base_classes import SmarterTestBase

ONBOARDING_CONST = "packages/smarter-onboarding/src/lib/const.ts"


class TestConsoleSource(SmarterTestBase):
    """Test the installed version, the release's urls, and reading a file of the release."""

    def setUp(self):
        super().setUp()
        project = tempfile.TemporaryDirectory()
        self.addCleanup(project.cleanup)
        self.project_root = Path(project.name)
        self.version_file = self.project_root / "console" / "version.txt"
        self.version_file.parent.mkdir()
        project_settings = override_settings(PROJECT_ROOT=self.project_root)
        project_settings.enable()
        self.addCleanup(project_settings.disable)

    def test_installed_console_version(self):
        self.version_file.write_text("1.0.3\n", encoding="utf-8")
        self.assertEqual(source.installed_console_version(), "1.0.3")

    def test_no_console_installed_skips(self):
        with self.assertRaisesRegex(unittest.SkipTest, "run make console"):
            source.installed_console_version()

    def test_a_local_build_skips(self):
        self.version_file.write_text("local\n", encoding="utf-8")
        with self.assertRaisesRegex(unittest.SkipTest, "local build"):
            source.installed_console_version()

    def test_url(self):
        self.assertEqual(
            source.console_source_url(ONBOARDING_CONST, "1.0.3"),
            f"https://raw.githubusercontent.com/smarter-sh/smarter-console/v1.0.3/{ONBOARDING_CONST}",
        )

    def test_reads_the_release_file(self):
        """The file is read at the installed release's tag."""
        self.version_file.write_text("1.0.3\n", encoding="utf-8")

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return b"export const OnboardingHints = {} as const;"

        with patch.object(source.urllib.request, "urlopen", return_value=Response()) as urlopen:
            self.assertIn("OnboardingHints", source.console_source(ONBOARDING_CONST))
        self.assertEqual(urlopen.call_args.args[0], source.console_source_url(ONBOARDING_CONST, "1.0.3"))

    def test_a_missing_file_fails(self):
        """The release exists, so a file it doesn't have means the test or the console changed."""
        self.version_file.write_text("1.0.3\n", encoding="utf-8")
        missing = urllib.error.HTTPError("https://raw.githubusercontent.com/x", 404, "Not Found", {}, None)
        with patch.object(source.urllib.request, "urlopen", side_effect=missing):
            with self.assertRaisesRegex(AssertionError, "answered 404"):
                source.console_source(ONBOARDING_CONST)

    def test_github_out_of_reach_skips(self):
        self.version_file.write_text("1.0.3\n", encoding="utf-8")
        with patch.object(source.urllib.request, "urlopen", side_effect=urllib.error.URLError("no network")):
            with self.assertRaisesRegex(unittest.SkipTest, "Could not read"):
                source.console_source(ONBOARDING_CONST)
