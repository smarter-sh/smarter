"""Tests of smarter.apps.llmtool.extension.archive."""

import io
import shutil
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch

from smarter.apps.llmtool.extension import archive as archive_module
from smarter.apps.llmtool.extension.archive import ExtensionArchive, build_archive
from smarter.apps.llmtool.extension.exceptions import (
    SmarterExtensionArchiveError,
    SmarterExtensionManifestError,
)
from smarter.lib.unittest.base_classes import SmarterTestBase

from .mixins import fixture_archive, fixture_source

PYPROJECT = (fixture_source("echo") / "pyproject.toml").read_text()


def make_zip(files: dict[str, str], symlink: str = "") -> bytes:
    """Return a zip of ``files``, by path, with an optional symbolic link."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, text in files.items():
            archive.writestr(name, text)
        if symlink:
            info = zipfile.ZipInfo(symlink)
            info.external_attr = 0o120777 << 16
            archive.writestr(info, "/etc/passwd")
    return buffer.getvalue()


class TestExtensionArchive(SmarterTestBase):
    """Test validating and reading extension archives."""

    def test_fixture_archive(self):
        """The echo fixture's archive has its manifest, docstring, assets and docs."""
        archive = ExtensionArchive(fixture_archive("echo"))
        self.assertEqual(archive.manifest.slug, "echo")
        self.assertEqual(len(archive.sha256), 64)
        self.assertIn("Echoes what it is sent", archive.docstring)
        self.assertEqual(archive.package_files("static"), ["icon.svg"])
        self.assertEqual(archive.package_files("docs"), ["usage.md"])
        self.assertIn("README.md", archive.names)
        self.assertIsNone(archive.read_text("no/such/file"))

    def test_build_is_reproducible_and_excludes_caches(self):
        """Building the same source twice gives the same bytes, without caches."""
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "echo"
            shutil.copytree(fixture_source("echo"), source)
            (source / "echo" / "__pycache__").mkdir(exist_ok=True)
            (source / "echo" / "__pycache__" / "tools.cpython-314.pyc").write_bytes(b"junk")
            (source / "echo" / ".hidden").write_text("x")
            first, second = build_archive(source), build_archive(source)
        self.assertEqual(first, second)
        names = ExtensionArchive(first).names
        self.assertFalse(any("__pycache__" in name or ".hidden" in name for name in names))

    def test_build_errors(self):
        """A directory without a pyproject.toml, or without its package, cannot be built."""
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(SmarterExtensionManifestError):
                build_archive(Path(directory))
            (Path(directory) / "pyproject.toml").write_text(PYPROJECT)
            with self.assertRaises(SmarterExtensionArchiveError):
                build_archive(Path(directory))

    def test_wrapped_archive(self):
        """An archive whose files are all in one top-level directory, as GitHub's are, is accepted."""
        data = make_zip({"echo-1.0.0/pyproject.toml": PYPROJECT, "echo-1.0.0/echo/__init__.py": '"""Doc."""'})
        archive = ExtensionArchive(data)
        self.assertEqual(archive.names, ["echo/__init__.py", "pyproject.toml"])
        self.assertEqual(archive.docstring, "Doc.")

    def test_rejects_invalid_archives(self):
        """Archives that are not zips, empty, unsafe, or laid out wrongly are rejected."""
        cases = {
            "not a zip": b"not a zip",
            "empty": make_zip({}),
            "traversal": make_zip({"pyproject.toml": PYPROJECT, "../evil.py": ""}),
            "absolute": make_zip({"pyproject.toml": PYPROJECT, "/evil.py": ""}),
            "symlink": make_zip({"pyproject.toml": PYPROJECT, "echo/__init__.py": ""}, symlink="echo/link"),
            "no package": make_zip({"pyproject.toml": PYPROJECT}),
            "syntax error": make_zip({"pyproject.toml": PYPROJECT, "echo/__init__.py": "def ("}),
        }
        for label, data in cases.items():
            with self.subTest(label=label):
                with self.assertRaises(SmarterExtensionArchiveError):
                    archive = ExtensionArchive(data)
                    archive.docstring  # pylint: disable=pointless-statement
        for label, data in {
            "no pyproject": make_zip({"echo/__init__.py": ""}),
            "two roots": make_zip({"a/pyproject.toml": PYPROJECT, "b/x.py": ""}),
        }.items():
            with self.subTest(label=label):
                with self.assertRaises(SmarterExtensionManifestError):
                    ExtensionArchive(data)

    def test_pyproject_not_utf8(self):
        """A pyproject.toml that is not UTF-8 text is rejected."""
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("pyproject.toml", b"\xff\xfe")
        with self.assertRaisesRegex(SmarterExtensionManifestError, "UTF-8"):
            ExtensionArchive(buffer.getvalue())

    def test_size_limits(self):
        """Archives that are too large, expand too much, or have too many files are rejected."""
        data = fixture_archive("echo")
        with patch.object(archive_module, "MAX_ARCHIVE_BYTES", 10):
            with self.assertRaisesRegex(SmarterExtensionArchiveError, "largest"):
                ExtensionArchive(data)
        with patch.object(archive_module, "MAX_UNCOMPRESSED_BYTES", 10):
            with self.assertRaisesRegex(SmarterExtensionArchiveError, "expands"):
                ExtensionArchive(data)
        with patch.object(archive_module, "MAX_FILES", 2):
            with self.assertRaisesRegex(SmarterExtensionArchiveError, "files"):
                ExtensionArchive(data)

    def test_duplicate_names(self):
        """An archive cannot have two files with the same path."""
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("pyproject.toml", PYPROJECT)
            archive.writestr("echo/__init__.py", "")
            with self.assertWarns(UserWarning):
                archive.writestr("echo/__init__.py", "")
        with self.assertRaisesRegex(SmarterExtensionArchiveError, "two files"):
            ExtensionArchive(buffer.getvalue())

    def test_extract_to(self):
        """Extraction writes every file under the target directory."""
        archive = ExtensionArchive(fixture_archive("echo"))
        with tempfile.TemporaryDirectory() as directory:
            archive.extract_to(Path(directory) / "out")
            self.assertTrue((Path(directory) / "out" / "echo" / "tools.py").is_file())
            self.assertTrue((Path(directory) / "out" / "pyproject.toml").is_file())
