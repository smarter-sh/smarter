"""Tests of smarter.apps.llmtool.extension.loader."""

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from smarter.apps.llmtool.extension import loader
from smarter.apps.llmtool.extension.archive import ExtensionArchive
from smarter.apps.llmtool.extension.exceptions import SmarterExtensionLoadError
from smarter.apps.llmtool.extension.loader import (
    MARKER,
    identifier,
    load_archive,
    load_version,
    materialize,
    module_name_for,
    unload,
)
from smarter.lib.unittest.base_classes import SmarterTestBase

from .mixins import ExtensionTestMixin, fixture_archive


class TestLoader(SmarterTestBase):
    """Test materializing and importing extension archives."""

    def setUp(self):
        super().setUp()
        self.directory = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        self.root = patch.object(loader, "extensions_root", return_value=Path(self.directory.name))
        self.root.start()

    def tearDown(self):
        self.root.stop()
        self.directory.cleanup()
        for slug in ("echo", "broken"):
            unload(slug)
        super().tearDown()

    def test_identifier_and_module_name(self):
        """Versions and slugs become identifiers in a namespace unique to the archive's contents."""
        self.assertEqual(identifier("1.2.0-rc.1"), "1_2_0_rc_1")
        archive = ExtensionArchive(fixture_archive("echo"))
        name = module_name_for(archive.manifest, archive.sha256)
        self.assertEqual(name, f"smarter_extensions.echo.v1_0_0_{archive.sha256[:12]}.echo")

    def test_materialize_once(self):
        """An archive is extracted once, and a damaged extraction is replaced."""
        archive = ExtensionArchive(fixture_archive("echo"))
        path = materialize(archive)
        self.assertEqual((path / MARKER).read_text(), archive.sha256)
        (path / "echo" / "tools.py").write_text("tampered")
        self.assertEqual(materialize(archive), path)
        self.assertEqual((path / "echo" / "tools.py").read_text(), "tampered")
        (path / MARKER).write_text("wrong")
        materialize(archive)
        self.assertNotEqual((path / "echo" / "tools.py").read_text(), "tampered")

    def test_load_archive(self):
        """Loading imports the package under its namespace, and finds its tools and lifecycle."""
        archive = ExtensionArchive(fixture_archive("echo"))
        loaded = load_archive(archive)
        self.assertEqual(sorted(loaded.tools), ["echo", "fail", "refuse", "slow", "unserializable"])
        self.assertIsNotNone(loaded.lifecycle)
        self.assertIn(loaded.module_name + ".tools", sys.modules)
        self.assertIs(load_archive(archive), loaded)
        with self.assertRaises(SmarterExtensionLoadError):
            loaded.entry_point("echo.tools:Missing")

    def test_two_versions_side_by_side(self):
        """Two versions of an extension are loaded beside each other."""
        first = load_archive(ExtensionArchive(fixture_archive("echo")))
        second = load_archive(ExtensionArchive(fixture_archive("echo", version="1.1.0")))
        self.assertNotEqual(first.module_name, second.module_name)
        self.assertIsNot(first.tools["echo"], second.tools["echo"])

    def test_broken_code(self):
        """An import error is reported, and its modules are forgotten."""
        archive = ExtensionArchive(fixture_archive("broken"))
        with self.assertRaisesRegex(SmarterExtensionLoadError, "broken on purpose"):
            load_archive(archive)
        self.assertNotIn(module_name_for(archive.manifest, archive.sha256), sys.modules)

    def test_invalid_tools(self):
        """Entry points that are not valid tools or lifecycles are rejected."""
        echo_tools = Path(__file__).parent / "data" / "extensions" / "echo" / "pyproject.toml"
        text = echo_tools.read_text()
        cases = {
            "not a tool": text.replace('tools = ["echo.tools:Echo"', 'tools = ["echo.models:EchoArguments"'),
            "not a lifecycle": text.replace('lifecycle = "echo.lifecycle:Lifecycle"', 'lifecycle = "echo.tools:Echo"'),
            "duplicate name": text.replace('"echo.tools:Fail"', '"echo.tools:Echo2"'),
        }
        for label, pyproject in cases.items():
            with self.subTest(label=label):
                archive = self.archive_with(pyproject, extra_tool=label == "duplicate name")
                with self.assertRaises(SmarterExtensionLoadError):
                    load_archive(archive)

    def test_invalid_tool_class(self):
        """A tool class with problems is rejected."""
        text = (Path(__file__).parent / "data" / "extensions" / "echo" / "pyproject.toml").read_text()
        archive = self.archive_with(text.replace('"echo.tools:Fail"', '"echo.tools:Nameless"'), nameless=True)
        with self.assertRaisesRegex(SmarterExtensionLoadError, "not valid"):
            load_archive(archive)

    def archive_with(self, pyproject: str, extra_tool: bool = False, nameless: bool = False) -> ExtensionArchive:
        """Return the echo archive with a different pyproject.toml, and optionally extra tool classes."""
        # pylint: disable=import-outside-toplevel
        import shutil

        from smarter.apps.llmtool.extension.archive import build_archive

        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "echo"
            shutil.copytree(Path(__file__).parent / "data" / "extensions" / "echo", source)
            (source / "pyproject.toml").write_text(pyproject)
            tools = source / "echo" / "tools.py"
            if extra_tool:
                tools.write_text(tools.read_text() + "\n\nclass Echo2(Echo):\n    name = 'echo'\n")
            if nameless:
                tools.write_text(tools.read_text() + "\n\nclass Nameless(Echo):\n    name = ''\n")
            return ExtensionArchive(build_archive(source))


class TestLoadVersion(ExtensionTestMixin):
    """Test loading an installed version from the database."""

    def test_load_version_reads_deferred_archive(self):
        """A version fetched without its archive is loaded, by reading the archive."""
        extension = self.install_echo()
        unload("echo")
        version = type(extension.installed_version).objects.defer("archive").get(pk=extension.installed_version.pk)  # type: ignore[union-attr]
        loaded = load_version(version)
        self.assertEqual(loaded.version, "1.0.0")
        self.assertIs(load_version(version), loaded)
