"""Test helpers for Smarter Extensions: the fixture extensions in ./data/extensions, and their cleanup."""

import shutil
import tempfile
from pathlib import Path
from typing import Optional

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.llmtool.extension.archive import build_archive
from smarter.apps.llmtool.extension.installer import ExtensionInstaller
from smarter.apps.llmtool.extension.loader import load_version
from smarter.apps.llmtool.models import Extension
from smarter.apps.secret.models import Secret

EXTENSIONS_DATA = Path(__file__).parent / "data" / "extensions"
"""The fixture extensions' source directories: echo, broken and incompatible."""
FIXTURE_SLUGS = ("echo", "broken", "incompatible")
ECHO_SECRET = "echo_extension_test_secret"
"""The Secret that the echo extension's manifests/secret.yaml creates."""


def fixture_source(name: str) -> Path:
    """Return the source directory of a fixture extension."""
    return EXTENSIONS_DATA / name


def fixture_archive(name: str = "echo", version: Optional[str] = None, without: tuple[str, ...] = ()) -> bytes:
    """
    Build the archive of a fixture extension, optionally as another version or without some files.

    :param name: The fixture's name.
    :param version: A version to write into its ``pyproject.toml`` instead of 1.0.0.
    :param without: Paths, relative to the source directory, to leave out.
    :returns: The archive's bytes.
    """
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / name
        shutil.copytree(fixture_source(name), source)
        if version:
            pyproject = source / "pyproject.toml"
            pyproject.write_text(
                pyproject.read_text(encoding="utf-8").replace('version = "1.0.0"', f'version = "{version}"', 1),
                encoding="utf-8",
            )
        for path in without:
            target = source / path
            if target.is_dir():
                shutil.rmtree(target)
            elif target.exists():
                target.unlink()
        return build_archive(source)


class ExtensionTestMixin(TestAccountMixin):
    """
    Install fixture extensions, and remove everything they create.

    Each test gets a fresh :attr:`installer`. The echo extension's lifecycle hooks record
    their calls in a list that is cleared before each test: see :meth:`echo_calls`.
    """

    installer: ExtensionInstaller

    def setUp(self):
        super().setUp()
        self.installer = ExtensionInstaller(user=self.admin_user)
        self.secrets: list[Secret] = []

    def tearDown(self):
        for extension in Extension.objects.filter(slug__in=FIXTURE_SLUGS):
            try:
                self.installer.uninstall(extension)
            # a test may have left an extension whose hooks refuse to uninstall.
            # pylint: disable=broad-exception-caught
            except Exception:
                extension.delete()
        Secret.objects.filter(name=ECHO_SECRET).delete()
        for secret in self.secrets:
            Secret.objects.filter(pk=secret.pk).delete()
        super().tearDown()

    def install_echo(self, **kwargs) -> Extension:
        """Install the echo extension, version 1.0.0 unless ``version`` is given."""
        extension = self.installer.install(fixture_archive("echo", **kwargs))
        self.echo_hooks(extension)["CALLS"].clear()
        self.echo_hooks(extension)["FAIL"].clear()
        return extension

    def echo_hooks(self, extension: Extension) -> dict:
        """Return the echo extension's lifecycle module's ``CALLS`` and ``FAIL``."""
        extension.refresh_from_db()
        loaded = load_version(extension.installed_version)  # type: ignore[arg-type]
        return {
            "CALLS": loaded.entry_point("echo.lifecycle:CALLS"),
            "FAIL": loaded.entry_point("echo.lifecycle:FAIL"),
        }

    def secret(self, name: str, value: str = "a-test-value") -> Secret:
        """Create a Secret, owned by the platform admin as extension secrets are, that is deleted after the test."""
        secret = Secret.objects.create(
            name=name,
            user_profile=smarter_cached_objects.smarter_admin_user_profile,
            encrypted_value=Secret.encrypt(value),
        )
        self.secrets.append(secret)
        return secret

    def enable_echo(self) -> Extension:
        """Install, configure and enable the echo extension."""
        extension = self.install_echo()
        self.installer.configure(extension, {"api_key": self.secret(f"echo_api_key_{self.hash_suffix}")})
        return self.installer.enable(extension)


__all__ = ["ECHO_SECRET", "EXTENSIONS_DATA", "ExtensionTestMixin", "fixture_archive", "fixture_source"]
