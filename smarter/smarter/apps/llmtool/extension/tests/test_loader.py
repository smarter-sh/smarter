"""Tests of smarter.apps.llmtool.extension.loader."""

import sys
import tempfile
from pathlib import Path
from unittest import mock
from unittest.mock import patch

from cache_results import lazy_cache

from smarter.apps.llmtool.extension import loader
from smarter.apps.llmtool.extension.archive import ExtensionArchive
from smarter.apps.llmtool.extension.exceptions import SmarterExtensionLoadError
from smarter.apps.llmtool.extension.loader import (
    MARKER,
    archive_cache_key,
    cached_archive,
    identifier,
    load_archive,
    load_by_key,
    load_version,
    materialize,
    module_name_for,
    publish_archive,
    unload,
)
from smarter.apps.llmtool.extension.toolkit import ExtensionToolkit
from smarter.apps.llmtool.runner import ToolCallResult
from smarter.common.conf.settings import Settings
from smarter.lib.unittest.base_classes import SmarterTestBase

from .mixins import ExtensionTestMixin, fixture_archive


def without_the_database():
    """Patch the settings as the tool worker's are: it has no database.

    The settings are frozen, so their class is patched.
    """
    return mock.patch.object(
        Settings, "database_unavailable", new_callable=mock.PropertyMock, return_value=True, create=True
    )


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


class TestArchiveForTheToolWorker(ExtensionTestMixin):
    """Test that the tool worker, which has no database, loads an extension's code from the cache."""

    def setUp(self):
        super().setUp()
        self.extension = self.enable_echo()
        self.version = self.extension.installed_version
        lazy_cache.delete(archive_cache_key(self.version.sha256))  # type: ignore[union-attr]
        self.addCleanup(lazy_cache.delete, archive_cache_key(self.version.sha256))  # type: ignore[union-attr]

    def test_publish_and_load_without_the_database(self):
        """A published archive is loaded by its sha256 from the cache, in a process that has no database."""
        version = self.version
        assert version is not None
        self.assertIsNone(cached_archive(version.sha256))
        publish_archive(version)
        archive = cached_archive(version.sha256)
        assert archive is not None
        self.assertEqual(archive.sha256, version.sha256)
        unload("echo")
        with (
            without_the_database(),
            mock.patch("smarter.apps.llmtool.models.ExtensionVersion.objects") as versions,
        ):
            loaded = load_by_key("echo", version.sha256)
        versions.filter.assert_not_called()
        self.assertEqual(loaded.sha256, version.sha256)
        self.assertIn("echo", loaded.tools)

    def test_publish_touches_rather_than_copies(self):
        """An archive already in the cache is only renewed, not read from the database again."""
        version = self.version
        assert version is not None
        publish_archive(version)
        with mock.patch.object(type(version).objects, "values_list") as values_list:
            publish_archive(version)
        values_list.assert_not_called()

    def test_without_the_database_or_the_cache(self):
        """A process without a database fails a call whose archive isn't in the cache, saying so."""
        unload("echo")
        with without_the_database():
            with self.assertRaises(SmarterExtensionLoadError) as context:
                load_by_key("echo", self.version.sha256)  # type: ignore[union-attr]
        self.assertIn("isn't in the cache", str(context.exception))

    def test_cached_bytes_must_match_the_sha256(self):
        """Bytes in the cache that aren't the archive with that sha256 are refused."""
        version = self.version
        assert version is not None
        lazy_cache.set(archive_cache_key(version.sha256), b"not the archive", timeout=60)
        with self.assertRaises(SmarterExtensionLoadError):
            cached_archive(version.sha256)

    def test_toolkit_publishes_only_for_the_remote_runner(self):
        """Resolving a call publishes the archive when the runner is remote, and not otherwise."""
        toolkit = ExtensionToolkit([self.extension], account=self.account, user_profile=self.user_profile).load()
        with mock.patch("smarter.apps.llmtool.extension.toolkit.publish_archive") as publish:
            toolkit.call("ext_echo_echo", {"text": "in process"})
            publish.assert_not_called()
            with (
                mock.patch("smarter.apps.llmtool.extension.toolkit.smarter_settings") as settings,
                mock.patch("smarter.apps.llmtool.runner.runner.smarter_settings") as runner_settings,
                mock.patch("smarter.apps.llmtool.extension.toolkit.get_tool_runner") as get_runner,
            ):
                settings.app_llmtool_tool_runner = "remote"
                runner_settings.app_llmtool_tool_runner = "in_process"
                get_runner.return_value.run.return_value = ToolCallResult(value={"echo": "x"})
                toolkit.call("ext_echo_echo", {"text": "remote"})
            publish.assert_called_once()
