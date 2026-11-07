"""Tests of scripts/fetch_console.py, with tarballs made here and served from file:// urls."""

import io
import sys
import tarfile
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import fetch_console  # noqa: E402  pylint: disable=wrong-import-position


def make_tarball(files: dict[str, str]) -> bytes:
    """A gzipped tarball of these files, by their paths in it."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name, text in files.items():
            data = text.encode()
            member = tarfile.TarInfo(name)
            member.size = len(data)
            archive.addfile(member, io.BytesIO(data))
    return buffer.getvalue()


A_RELEASE = {
    "react/@smarter/console/index.html": "<!doctype html><title>console</title>",
    "react/@smarter/console/assets/index-abc12345.js": "console.log(1);",
    "react/@smarter/llmclient-deployment/manifest.json": "{}",
}


class TestFetchConsole(unittest.TestCase):
    """Test that a release or a local build replaces the static folder's react/, and nothing else."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.static = self.root / "static"
        # an old build, and a static file of Django's own, which must survive.
        (self.static / "react" / "@smarter" / "old-list").mkdir(parents=True)
        (self.static / "react" / "@smarter" / "old-list" / "index.js").write_text("old")
        (self.static / "js").mkdir()
        (self.static / "js" / "smarter-base.js").write_text("base")
        # a releases url whose v1.2.0 has a tarball.
        self.releases = self.root / "releases"
        (self.releases / "v1.2.0").mkdir(parents=True)
        (self.releases / "v1.2.0" / "smarter-console-1.2.0.tar.gz").write_bytes(make_tarball(A_RELEASE))
        self.releases_url = self.releases.as_uri()

    def run_main(self, *args: str) -> tuple[int, str, str]:
        """Run the script with the test's static folder and releases, and return its exit code and output."""
        out, err = io.StringIO(), io.StringIO()
        argv = [*args, "--static-dir", str(self.static), "--releases-url", self.releases_url]
        with redirect_stdout(out), redirect_stderr(err):
            code = fetch_console.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_installs_a_release(self):
        code, out, _ = self.run_main("--version", "1.2.0")
        self.assertEqual(code, 0)
        self.assertIn("Installed the web console 1.2.0", out)
        self.assertTrue((self.static / "react/@smarter/console/index.html").is_file())
        self.assertTrue((self.static / "react/@smarter/llmclient-deployment/manifest.json").is_file())
        # the old builds are gone, and Django's own static files are not.
        self.assertFalse((self.static / "react/@smarter/old-list").exists())
        self.assertEqual((self.static / "js/smarter-base.js").read_text(), "base")

    def test_a_leading_v_is_allowed(self):
        code, _, _ = self.run_main("--version", "v1.2.0")
        self.assertEqual(code, 0)

    def test_the_pinned_version(self):
        version_file = self.root / "smarter-console-version.txt"
        version_file.write_text("v1.2.0\n")
        self.assertEqual(fetch_console.pinned_version(version_file), "1.2.0")
        self.assertEqual(
            fetch_console.release_url("1.2.0"),
            "https://github.com/smarter-sh/smarter-console/releases/download/v1.2.0/smarter-console-1.2.0.tar.gz",
        )
        # the repository's own pin is a version.
        self.assertRegex(fetch_console.pinned_version(), r"^\d+\.\d+\.\d+")

    def test_a_missing_release_changes_nothing(self):
        code, _, err = self.run_main("--version", "9.9.9")
        self.assertEqual(code, 1)
        self.assertIn("Could not install the web console", err)
        self.assertTrue((self.static / "react/@smarter/old-list/index.js").is_file())

    def test_a_build_without_the_console_changes_nothing(self):
        (self.releases / "v2.0.0").mkdir()
        tarball = make_tarball({"react/@smarter/other/index.html": "x"})
        (self.releases / "v2.0.0" / "smarter-console-2.0.0.tar.gz").write_bytes(tarball)
        code, _, err = self.run_main("--version", "2.0.0")
        self.assertEqual(code, 1)
        self.assertIn("not a build of smarter-console", err)
        self.assertTrue((self.static / "react/@smarter/old-list/index.js").is_file())

    def test_a_member_outside_the_folder_is_refused(self):
        (self.releases / "v3.0.0").mkdir()
        tarball = make_tarball({**A_RELEASE, "../escaped.txt": "x"})
        (self.releases / "v3.0.0" / "smarter-console-3.0.0.tar.gz").write_bytes(tarball)
        code, _, _ = self.run_main("--version", "3.0.0")
        self.assertEqual(code, 1)
        self.assertFalse((self.root / "escaped.txt").exists())

    def test_installs_a_local_build(self):
        dist = self.root / "dist"
        for name, text in A_RELEASE.items():
            (dist / name).parent.mkdir(parents=True, exist_ok=True)
            (dist / name).write_text(text)
        code, out, _ = self.run_main("--from-dir", str(dist))
        self.assertEqual(code, 0)
        self.assertIn("local build", out)
        self.assertTrue((self.static / "react/@smarter/console/assets/index-abc12345.js").is_file())
        self.assertFalse((self.static / "react/@smarter/old-list").exists())


if __name__ == "__main__":
    unittest.main()
