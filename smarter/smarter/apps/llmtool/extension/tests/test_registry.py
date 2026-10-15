"""Tests of smarter.apps.llmtool.extension.registry, against a signed index served by a patched transport."""

import base64
import hashlib
import json
from types import SimpleNamespace
from unittest.mock import patch

from nacl.signing import SigningKey

from smarter.apps.llmtool.extension import registry
from smarter.apps.llmtool.extension.exceptions import SmarterExtensionRegistryError
from smarter.apps.llmtool.extension.registry import RegistryIndex, RegistryVersion
from smarter.apps.llmtool.models import Extension, ExtensionSource, ExtensionTrustBadge
from smarter.apps.llmtool.plugin.safe_http import SafeHttpError, SafeResponse
from smarter.apps.llmtool.tasks import check_extension_updates
from smarter.lib.unittest.base_classes import SmarterTestBase

from .mixins import ExtensionTestMixin, fixture_archive

INDEX_URL = "https://registry.example.com/index.json"
ARCHIVE_URL = "https://registry.example.com/echo-{version}.zip"


class RegistryServer:
    """A registry: a signed index of the echo extension's versions, and their archives, served by a patched fetch()."""

    def __init__(self, versions: tuple[str, ...] = ("1.0.0", "1.1.0"), badge: str = "official"):
        self.key = SigningKey.generate()
        self.archives = {
            ARCHIVE_URL.format(version=version): fixture_archive("echo", version=version) for version in versions
        }
        index = {
            "schema_version": 1,
            "generated_at": "2026-10-15T12:00:00Z",
            "publishers": [{"id": "smarter-sh", "name": "Smarter", "url": "https://smarter.sh", "badge": badge}],
            "extensions": [
                {
                    "slug": "echo",
                    "display_name": "Echo",
                    "description": "Echoes what it is sent.",
                    "publisher": "smarter-sh",
                    "homepage": "https://example.com/echo",
                    "license": "AGPL-3.0",
                    "docs_rst": "Echo\n====\n\nEchoes.",
                    "a_future_field": True,
                    "versions": [
                        {
                            "version": version,
                            "archive_url": ARCHIVE_URL.format(version=version),
                            "sha256": hashlib.sha256(self.archives[ARCHIVE_URL.format(version=version)]).hexdigest(),
                            "requires_smarter": ">=0.1",
                        }
                        for version in versions
                    ]
                    + [
                        {
                            "version": "9.0.0",
                            "archive_url": ARCHIVE_URL.format(version="9.0.0"),
                            "sha256": "0" * 64,
                            "requires_smarter": "<0.1",
                        }
                    ],
                }
            ],
        }
        self.index = json.dumps(index).encode()
        self.signature = base64.b64encode(self.key.sign(self.index).signature)
        self.requests: list[str] = []

    @property
    def public_key(self) -> str:
        return base64.b64encode(bytes(self.key.verify_key)).decode()

    def fetch(self, url: str, **kwargs) -> SafeResponse:
        """Serve the index, its signature, and the archives."""
        self.requests.append(url)
        content = {INDEX_URL: self.index, INDEX_URL + ".sig": self.signature, **self.archives}.get(url)
        if content is None:
            raise SafeHttpError(f"{url} responded with HTTP 404", status_code=404)
        return SafeResponse(url=url, status_code=200, headers={}, content=content)


class RegistryTestMixin(ExtensionTestMixin):
    """Serve a registry, and point the platform's settings at it."""

    def setUp(self):
        super().setUp()
        self.server = RegistryServer()
        self.serve(self.server, self.server.public_key)
        # a released platform, so that each version's requires_smarter is checked.
        patcher = patch.object(registry, "smarter_version", "0.27.0")
        patcher.start()
        self.addCleanup(patcher.stop)

    def serve(self, server: RegistryServer, public_key: str):
        """Serve ``server``'s registry, verified with ``public_key``."""
        registry.fetch_index_files.invalidate(INDEX_URL)
        settings = SimpleNamespace(extension_registry_url=INDEX_URL, extension_registry_public_key=public_key)
        for patcher in (
            patch.object(registry, "smarter_settings", settings),
            patch.object(registry, "fetch", server.fetch),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.addCleanup(registry.fetch_index_files.invalidate, INDEX_URL)


class TestRegistryIndex(RegistryTestMixin):
    """Test reading and verifying the registry's index."""

    def test_get_index(self):
        """The index is verified, parsed, and cached; unknown fields are ignored."""
        index = registry.get_index()
        self.assertTrue(registry.is_enabled())
        entry = index.extension("echo")
        self.assertEqual(entry.latest_compatible().version, "1.1.0")  # type: ignore[union-attr]
        self.assertEqual(entry.find_version("1.0.0").version, "1.0.0")  # type: ignore[union-attr]
        self.assertIsNone(entry.find_version("2.0.0"))  # type: ignore[union-attr]
        self.assertEqual(index.badge_of(entry), "official")  # type: ignore[arg-type]
        self.assertIsNone(index.extension("nope"))
        self.assertIsNone(index.publisher("nope"))
        registry.get_index()
        self.assertEqual(self.server.requests.count(INDEX_URL), 1)
        registry.refresh_index()
        self.assertEqual(self.server.requests.count(INDEX_URL), 2)

    def test_disabled(self):
        """Without a public key, the registry is disabled."""
        self.serve(self.server, "")
        self.assertFalse(registry.is_enabled())
        with self.assertRaisesRegex(SmarterExtensionRegistryError, "disabled"):
            registry.get_index()
        self.assertEqual(check_extension_updates(), [])

    def test_wrong_key(self):
        """An index signed by another key is refused, and not kept in the cache."""
        self.serve(self.server, RegistryServer().public_key)
        with self.assertRaisesRegex(SmarterExtensionRegistryError, "does not match"):
            registry.get_index()
        with self.assertRaisesRegex(SmarterExtensionRegistryError, "does not match"):
            registry.get_index()
        self.assertEqual(self.server.requests.count(INDEX_URL), 2)

    def test_malformed_key(self):
        """A key that is not base64 is reported."""
        self.serve(self.server, "not base64!")
        with self.assertRaisesRegex(SmarterExtensionRegistryError, "malformed"):
            registry.get_index()

    def test_unreachable(self):
        """A registry that cannot be reached is reported."""
        with patch.object(registry, "fetch", side_effect=SafeHttpError("timed out")):
            registry.fetch_index_files.invalidate(INDEX_URL)
            with self.assertRaisesRegex(SmarterExtensionRegistryError, "cannot be reached"):
                registry.get_index()

    def test_invalid_index(self):
        """An authentic index that is not valid, or of another format, is refused."""
        for document, message in ((b"[]", "not valid"), (json.dumps({"schema_version": 2}).encode(), "format 2")):
            with self.subTest(message=message):
                self.server.index = document
                self.server.signature = base64.b64encode(self.server.key.sign(document).signature)
                registry.fetch_index_files.invalidate(INDEX_URL)
                with self.assertRaisesRegex(SmarterExtensionRegistryError, message):
                    registry.get_index()

    def test_version_compatibility(self):
        """A version without requires_smarter, or on an unreleased build, is compatible; an invalid one sorts first."""
        version = RegistryVersion(version="x", archive_url="https://x", sha256="0" * 64, requires_smarter="nonsense")
        self.assertFalse(version.is_compatible("1.0.0"))
        self.assertTrue(version.is_compatible("9999.0.0"))
        self.assertFalse(version.is_compatible())
        self.assertTrue(RegistryVersion(version="1", archive_url="https://x", sha256="0" * 64).is_compatible("1.0.0"))
        self.assertEqual(str(version.sort_key()), "0")
        self.assertEqual(RegistryIndex(schema_version=1).badge_of(SimpleNamespace(publisher="x")), "community")  # type: ignore[arg-type]


class TestRegistryInstall(RegistryTestMixin):
    """Test installing and updating extensions from the registry."""

    def test_install_and_update(self):
        """An install records the source, badge and publisher; an update is found and installed."""
        extension = registry.install_from_registry("echo", "1.0.0", user=self.admin_user)
        self.assertEqual(extension.source, ExtensionSource.REGISTRY)
        self.assertEqual(extension.trust_badge, ExtensionTrustBadge.OFFICIAL)
        self.assertEqual(extension.publisher, "smarter-sh")
        self.assertEqual(extension.latest_version, "1.1.0")
        self.assertTrue(extension.update_available)
        self.assertEqual(extension.installed_version.source_url, ARCHIVE_URL.format(version="1.0.0"))  # type: ignore[union-attr]

        self.assertEqual([item.slug for item in registry.check_for_updates()], ["echo"])
        self.assertEqual(check_extension_updates(), ["echo"])
        extension = registry.install_from_registry("echo", user=self.admin_user)
        self.assertEqual(extension.installed_version.version, "1.1.0")  # type: ignore[union-attr]
        self.assertEqual(registry.check_for_updates(), [])

    def test_install_errors(self):
        """Unknown extensions and versions, and uploads with the same slug, are refused."""
        with self.assertRaisesRegex(SmarterExtensionRegistryError, "no extension"):
            registry.install_from_registry("nope")
        with self.assertRaisesRegex(SmarterExtensionRegistryError, "no version 2.0.0"):
            registry.install_from_registry("echo", "2.0.0")
        self.install_echo()
        with self.assertRaisesRegex(SmarterExtensionRegistryError, "uploaded archive"):
            registry.install_from_registry("echo")

    def test_no_compatible_version(self):
        """An extension with no compatible version cannot be installed."""
        server = RegistryServer(versions=())
        self.serve(server, server.public_key)
        with self.assertRaisesRegex(SmarterExtensionRegistryError, "no version of echo is compatible"):
            registry.install_from_registry("echo")

    def test_tampered_archive(self):
        """An archive that does not match the signed index's sha256 is not installed."""
        self.server.archives[ARCHIVE_URL.format(version="1.1.0")] = fixture_archive(
            "echo", version="1.1.0", without=("README.md",)
        )
        with self.assertRaisesRegex(SmarterExtensionRegistryError, "sha256"):
            registry.install_from_registry("echo")
        self.assertFalse(Extension.objects.filter(slug="echo").exists())

    def test_download_failure(self):
        """An archive that cannot be downloaded is reported."""
        version = RegistryVersion(version="1", archive_url="https://registry.example.com/missing.zip", sha256="0" * 64)
        with self.assertRaisesRegex(SmarterExtensionRegistryError, "cannot be downloaded"):
            registry.download(version)

    def test_check_failure(self):
        """The beat task logs, rather than raises, when the registry cannot be read."""
        with patch.object(registry, "check_for_updates", side_effect=SmarterExtensionRegistryError("down")):
            self.assertEqual(check_extension_updates(), [])

    def test_uploads_are_not_checked(self):
        """An extension installed from an upload is never offered a registry update."""
        extension = self.install_echo()
        registry.check_for_updates()
        extension.refresh_from_db()
        self.assertEqual(extension.latest_version, "")


class TestRegistryIndexSchema(SmarterTestBase):
    """Test that the committed JSON Schema of the registry's index is current."""

    def test_schema_is_current(self):
        committed = json.loads(registry.INDEX_SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            committed,
            json.loads(json.dumps(registry.index_json_schema())),
            "The registry index's JSON Schema is out of date. Run `python manage.py export_extension_registry_schema` "
            "in the smarter-app container, copy the file to the host, and to the registry's schema/ directory.",
        )
