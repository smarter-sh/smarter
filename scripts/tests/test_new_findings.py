"""
Tests of scripts/new_findings.py, the git side of the hooks that fail only on new findings.

They need only the standard library, and don't run git. Run them from the repository's root:

    python -m unittest discover -s scripts/tests -t scripts
"""

import importlib.util
import io
import subprocess  # nosec B404: only to build fake results
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPT_PATH = Path(__file__).resolve().parent.parent / "new_findings.py"
spec = importlib.util.spec_from_file_location("new_findings", SCRIPT_PATH)
new_findings = importlib.util.module_from_spec(spec)
spec.loader.exec_module(new_findings)


def completed(stdout: str = "", returncode: int = 0) -> subprocess.CompletedProcess:
    """A finished git command, with its output."""
    return subprocess.CompletedProcess(args=["git"], returncode=returncode, stdout=stdout, stderr="")


class TestChangedFiles(unittest.TestCase):
    """Which files a change touched."""

    def test_python_files_under_the_source_root(self):
        """Changed and untracked Python files are listed once, sorted, under the source root only."""
        diff = completed("smarter/b.py\nsmarter/a.py\nREADME.md\nscripts/c.py\n")
        untracked = completed("smarter/new.py\nsmarter/a.py\n")
        with mock.patch.object(new_findings.subprocess, "run", side_effect=[diff, untracked]):
            files = new_findings.changed_files("HEAD", "smarter/")
        self.assertEqual(files, ["smarter/a.py", "smarter/b.py", "smarter/new.py"])

    def test_every_folder_by_default(self):
        """Without a source root, Python files in every folder are listed."""
        diff = completed("scripts/c.py\nsmarter/a.py\n")
        untracked = completed("")
        with mock.patch.object(new_findings.subprocess, "run", side_effect=[diff, untracked]):
            files = new_findings.changed_files("HEAD")
        self.assertEqual(files, ["scripts/c.py", "smarter/a.py"])


class TestBase(unittest.TestCase):
    """The base's files."""

    def test_files_at_base_skips_new_files(self):
        """A file that git cat-file doesn't find at the base is left out."""
        results = [completed(returncode=0), completed(returncode=128), completed(returncode=0)]
        with mock.patch.object(new_findings.subprocess, "run", side_effect=results):
            existing = new_findings.files_at_base("HEAD", ["a.py", "new.py", "b.py"])
        self.assertEqual(existing, ["a.py", "b.py"])

    def test_export_base_extracts_the_archive(self):
        """Git archive's output is extracted at the same relative paths, and the archive is removed."""
        archive_bytes = io.BytesIO()
        with tarfile.open(fileobj=archive_bytes, mode="w") as archive:
            content = b"x = 1\n"
            member = tarfile.TarInfo("smarter/a.py")
            member.size = len(content)
            archive.addfile(member, io.BytesIO(content))

        def fake_archive(command, stdout, check):
            """Write the archive where git archive would."""
            self.assertEqual(command[1:], ["archive", "HEAD", "--", "smarter/a.py"])
            stdout.write(archive_bytes.getvalue())
            return completed()

        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder)
            with mock.patch.object(new_findings.subprocess, "run", side_effect=fake_archive):
                new_findings.export_base("HEAD", ["smarter/a.py"], destination)
            self.assertEqual((destination / "smarter" / "a.py").read_text(), "x = 1\n")
            self.assertFalse((destination / "base.tar").exists())


if __name__ == "__main__":
    unittest.main()
