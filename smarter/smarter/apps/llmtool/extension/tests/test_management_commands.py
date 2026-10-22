"""Tests of the extension management commands: validate, package, install, uninstall and install_official_extensions."""

import io
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.core.management import call_command

from smarter.apps.account.management.commands.load_from_github import (
    Command as LoadFromGithub,
)
from smarter.apps.llmtool.const import OFFICIAL_EXTENSIONS
from smarter.apps.llmtool.models import Extension, ExtensionSetting

from .mixins import ExtensionTestMixin, fixture_archive, fixture_source
from .test_registry import RegistryTestMixin


def run(command: str, *args, **kwargs) -> str:
    """Run a command, and return what it wrote."""
    output = io.StringIO()
    call_command(command, *args, stdout=output, stderr=io.StringIO(), **kwargs)
    return output.getvalue()


class TestExtensionCommands(ExtensionTestMixin):
    """Test the commands that validate, package, install and uninstall extensions."""

    def test_validate(self):
        """A valid extension's tools are printed; an invalid one exits with an error."""
        output = run("validate_extension", str(fixture_source("echo")))
        self.assertIn('"name": "echo"', output)
        self.assertIn("is a valid extension", output)
        for name in ("broken", "incompatible"):
            with self.subTest(name=name):
                with self.assertRaises(SystemExit):
                    run("validate_extension", str(fixture_source(name)))

    def test_package_and_install_archive(self):
        """An archive is packaged, validated, and installed from the file."""
        with tempfile.TemporaryDirectory() as directory:
            output = run("package_extension", str(fixture_source("echo")), output=directory)
            archive = Path(directory) / "echo-1.0.0.zip"
            self.assertIn("sha256:", output)
            self.assertEqual(archive.read_bytes(), fixture_archive("echo"))
            self.assertIn("is a valid extension", run("validate_extension", str(archive)))
            self.assertIn("Installed echo 1.0.0, disabled.", run("install_extension", str(archive)))
        with self.assertRaises(SystemExit):
            run("package_extension", "/no/such/directory")

    def test_install_directory_enable_and_uninstall(self):
        """An extension is installed from its source directory, and uninstalled."""
        with self.assertRaises(SystemExit):
            run("install_extension", str(fixture_source("echo")), enable=True)
        self.assertTrue(Extension.objects.filter(slug="echo").exists())
        self.assertIn("Uninstalled echo.", run("uninstall_extension", "echo"))
        with self.assertRaises(SystemExit):
            run("uninstall_extension", "echo")
        with self.assertRaises(SystemExit):
            run("install_extension")

    def test_uninstall_refused(self):
        """A pre_uninstall hook that refuses makes the command fail."""
        extension = self.install_echo()
        self.echo_hooks(extension)["FAIL"].add("pre_uninstall")
        try:
            with self.assertRaises(SystemExit):
                run("uninstall_extension", "echo")
        finally:
            self.echo_hooks(extension)["FAIL"].clear()

    def test_test_extension(self):
        """An extension repository's own tests run in the platform's environment."""
        self.assertIn("OK", run("test_extension", str(fixture_source("echo"))))
        with self.assertRaises(SystemExit):
            run("test_extension", str(fixture_source("broken")))
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "tests").mkdir()
            with self.assertRaises(SystemExit):
                run("test_extension", directory)
            (Path(directory) / "tests" / "__init__.py").write_text("")
            (Path(directory) / "tests" / "test_fails.py").write_text(
                "import unittest\n\nclass T(unittest.TestCase):\n    def test_fails(self):\n        self.fail('x')\n"
            )
            with self.assertRaises(SystemExit):
                run("test_extension", directory)

    def test_install_official_extensions_without_registry(self):
        """Without a registry, nothing is installed."""
        with patch(
            "smarter.apps.llmtool.management.commands.install_official_extensions.registry.is_enabled",
            return_value=False,
        ):
            self.assertIn("registry is disabled", run("install_official_extensions"))

    def test_load_from_github_finds_missing_extensions(self):
        """The extensions of an example LLMClient that are not installed, for which it is skipped, not failed."""
        command = LoadFromGithub()
        self.assertEqual(command.missing_extensions(["echo"]), ["echo"])
        self.install_echo()
        self.assertEqual(command.missing_extensions(["echo", "no-such-extension"]), ["no-such-extension"])


class TestInstallOfficialExtensions(RegistryTestMixin):
    """Test installing the official extensions from a registry."""

    def test_install_official_extensions(self):
        """Official extensions are installed and configured from the platform's Secrets."""
        secret = self.secret("api_key")
        with patch(
            "smarter.apps.llmtool.management.commands.install_official_extensions.OFFICIAL_EXTENSIONS", ("echo",)
        ):
            output = run("install_official_extensions")
        extension = Extension.objects.get(slug="echo")
        self.assertTrue(extension.enabled)
        self.assertEqual(ExtensionSetting.objects.get(extension=extension, name="api_key").secret, secret)
        self.assertIn("Installed and enabled echo 1.1.0", output)
        self.assertEqual(OFFICIAL_EXTENSIONS, ("calculator", "date-calculator", "weather"))

    def test_failure_exits(self):
        """An official extension that cannot be installed doesn't stop the others, and then exits with code 1."""
        self.secret("api_key")  # echo's required setting, without which it cannot be enabled
        output = io.StringIO()
        with patch(
            "smarter.apps.llmtool.management.commands.install_official_extensions.OFFICIAL_EXTENSIONS", ("nope", "echo")
        ):
            with self.assertRaises(SystemExit) as raised:
                call_command("install_official_extensions", stdout=output, stderr=io.StringIO())
        self.assertEqual(raised.exception.code, 1)
        self.assertTrue(Extension.objects.get(slug="echo").enabled)
        self.assertIn("Installed and enabled echo 1.1.0", output.getvalue())
        self.assertIn("nope: ", output.getvalue())

    def test_skips_uploads(self):
        """An official slug that was installed from an upload is left alone."""
        self.install_echo()
        with patch(
            "smarter.apps.llmtool.management.commands.install_official_extensions.OFFICIAL_EXTENSIONS", ("echo",)
        ):
            self.assertIn("Skipped echo", run("install_official_extensions"))
