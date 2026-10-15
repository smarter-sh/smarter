"""
The Smarter Extension registry: discovery, trust badges and updates.

The registry is a public GitHub repository, ``smarter-sh/extensions-registry``, whose CI
publishes a signed index of every released extension: ``index.json``, and its Ed25519
signature, ``index.json.sig``, at :attr:`~smarter.common.conf.Settings.extension_registry_url`.
Publishers submit releases by pull request; the Smarter team assigns publishers' trust
badges in a file that only it may change.

This module:

- fetches the index, caching the HTTP request for an hour, and verifies its signature with
  :attr:`~smarter.common.conf.Settings.extension_registry_public_key` on every read;
- finds each extension's newest version that is compatible with this platform;
- downloads an archive, and checks it against the sha256 in the signed index;
- installs or updates an extension from the registry, with its publisher's trust badge;
- records the newest compatible version of each installed extension, so that the admin
  console can say an update is available.

The index's models allow fields that they do not know, so that the registry can add fields
without breaking older platforms.
"""

import base64
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

from django.utils import timezone
from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from smarter.__version__ import __version__ as smarter_version
from smarter.apps.account.models import User
from smarter.apps.llmtool.const import ONE_HOUR
from smarter.apps.llmtool.models import Extension, ExtensionSource, ExtensionTrustBadge
from smarter.apps.llmtool.plugin.safe_http import SafeHttpError, fetch
from smarter.common.conf import smarter_settings
from smarter.lib import logging
from smarter.lib.cache import cache_results
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .archive import MAX_ARCHIVE_BYTES
from .exceptions import SmarterExtensionRegistryError
from .installer import ExtensionInstaller
from .manifest import is_development_version

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.EXTENSION_LOGGING])
logger_prefix = logging.formatted_text(__name__)

MAX_INDEX_BYTES = 5 * 1024 * 1024
SIGNATURE_SUFFIX = ".sig"
SCHEMA_VERSION = 1

INDEX_SCHEMA_PATH = Path(__file__).parent / "registry-index.schema.json"
"""The committed JSON Schema of the registry's index, which the registry's CI validates against."""

RegistryBadge = Literal["official", "verified", "community"]
"""A publisher's trust badge in the registry."""


class RegistryModel(BaseModel):
    """The base class of the index's models, which ignore fields they do not know."""

    model_config = ConfigDict(extra="ignore")


class RegistryPublisher(RegistryModel):
    """A publisher of extensions, and how far the Smarter team trusts them."""

    id: str = Field(..., description="The publisher's id, e.g. smarter-sh.")
    name: str = Field(..., description="The publisher's name.")
    url: Optional[str] = Field(None, description="The publisher's website.")
    badge: RegistryBadge = Field("community", description="The publisher's trust badge.")


class RegistryVersion(RegistryModel):
    """One released version of an extension."""

    version: str = Field(..., description="The version, e.g. 1.2.0.")
    archive_url: str = Field(..., description="Where to download the archive.")
    sha256: str = Field(..., pattern=r"^[0-9a-f]{64}$", description="The hex sha256 of the archive.")
    requires_smarter: Optional[str] = Field(None, description="The Smarter versions it works with.")
    released_at: Optional[datetime] = Field(None, description="When it was released.")

    def is_compatible(self, platform_version: Optional[str] = None) -> bool:
        """Return whether this version works with a Smarter version; this platform's if None."""
        platform_version = platform_version or smarter_version
        if not self.requires_smarter or is_development_version(platform_version):
            return True
        try:
            return SpecifierSet(self.requires_smarter).contains(platform_version, prereleases=True)
        except InvalidSpecifier:
            return False

    def sort_key(self) -> Version:
        """The version, for sorting; an invalid version sorts first."""
        try:
            return Version(self.version)
        except InvalidVersion:
            return Version("0")


class RegistryExtension(RegistryModel):
    """An extension in the registry, with every released version."""

    slug: str = Field(..., description="The extension's slug.")
    display_name: str = Field(..., description="The extension's name.")
    description: str = Field("", description="A one-line description.")
    publisher: str = Field(..., description="The publisher's id.")
    homepage: Optional[str] = Field(None, description="The extension's website or repository.")
    license: Optional[str] = Field(None, description="The extension's license.")
    docs_rst: str = Field("", description="The extension's documentation, its package's docstring.")
    versions: list[RegistryVersion] = Field(default_factory=list)

    def latest_compatible(self, platform_version: Optional[str] = None) -> Optional[RegistryVersion]:
        """Return the newest version that works with a Smarter version, this platform's if None, or None."""
        compatible = [version for version in self.versions if version.is_compatible(platform_version)]
        return max(compatible, key=RegistryVersion.sort_key) if compatible else None

    def find_version(self, version: str) -> Optional[RegistryVersion]:
        """Return one of the extension's versions, or None."""
        return next((item for item in self.versions if item.version == version), None)


class RegistryIndex(RegistryModel):
    """The registry's index: every publisher, and every extension."""

    schema_version: int = Field(..., description="The index format's version.")
    generated_at: Optional[datetime] = Field(None, description="When the index was built.")
    publishers: list[RegistryPublisher] = Field(default_factory=list)
    extensions: list[RegistryExtension] = Field(default_factory=list)

    def publisher(self, publisher_id: str) -> Optional[RegistryPublisher]:
        """Return a publisher by id, or None."""
        return next((publisher for publisher in self.publishers if publisher.id == publisher_id), None)

    def extension(self, slug: str) -> Optional[RegistryExtension]:
        """Return an extension by slug, or None."""
        return next((extension for extension in self.extensions if extension.slug == slug), None)

    def badge_of(self, extension: RegistryExtension) -> str:
        """Return the trust badge of an extension's publisher; ``community`` if the publisher is unknown."""
        publisher = self.publisher(extension.publisher)
        return publisher.badge if publisher else ExtensionTrustBadge.COMMUNITY


def index_json_schema() -> dict:
    """Return the JSON Schema of the registry's index."""
    schema = RegistryIndex.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["title"] = "Smarter Extension Registry Index"
    return schema


def is_enabled() -> bool:
    """Return whether the registry is configured: it is disabled until its public key is set."""
    return bool(smarter_settings.extension_registry_public_key.strip())


@cache_results(ONE_HOUR)
def fetch_index_files(url: str) -> tuple[bytes, bytes]:
    """
    Download the registry's index and its signature.

    Cached for an hour. A failure raises, so that it is not cached.

    :param url: The index's url.
    :returns: The index's bytes, and its signature's bytes.
    :raises SafeHttpError: If either cannot be downloaded.
    """
    logger.info("%s.fetch_index_files() downloading %s", logger_prefix, url)
    index = fetch(url, max_bytes=MAX_INDEX_BYTES).content
    signature = fetch(url + SIGNATURE_SUFFIX, max_bytes=1024).content
    return index, signature


def verify(index: bytes, signature: bytes, public_key: str) -> None:
    """
    Verify the index's Ed25519 signature.

    :param index: The index's bytes.
    :param signature: The signature, base64.
    :param public_key: The registry's public key, base64.
    :raises SmarterExtensionRegistryError: If the key or signature is malformed, or the signature does not match.
    """
    try:
        VerifyKey(base64.b64decode(public_key.strip(), validate=True)).verify(
            index, base64.b64decode(signature.strip(), validate=True)
        )
    except BadSignatureError as e:
        raise SmarterExtensionRegistryError("the registry's index does not match its signature") from e
    except (ValueError, TypeError) as e:
        raise SmarterExtensionRegistryError(f"the registry's public key or signature is malformed: {e}") from e


def get_index() -> RegistryIndex:
    """
    Return the registry's verified index.

    :returns: The index.
    :raises SmarterExtensionRegistryError: If the registry is disabled, cannot be reached, or its index is not authentic or not valid.
    """
    if not is_enabled():
        raise SmarterExtensionRegistryError(
            "the extension registry is disabled until SMARTER_EXTENSION_REGISTRY_PUBLIC_KEY is set"
        )
    url = smarter_settings.extension_registry_url
    try:
        index, signature = fetch_index_files(url)
    except SafeHttpError as e:
        raise SmarterExtensionRegistryError(f"the extension registry cannot be reached: {e}") from e
    try:
        verify(index, signature, smarter_settings.extension_registry_public_key)
    except SmarterExtensionRegistryError:
        # don't keep an index that is not authentic for an hour: the next read downloads it again.
        fetch_index_files.invalidate(url)
        raise
    try:
        parsed = RegistryIndex.model_validate_json(index)
    except ValidationError as e:
        raise SmarterExtensionRegistryError(f"the registry's index is not valid: {e.errors()[0]['msg']}") from e
    if parsed.schema_version != SCHEMA_VERSION:
        raise SmarterExtensionRegistryError(
            f"the registry's index is format {parsed.schema_version}; this platform reads format {SCHEMA_VERSION}"
        )
    return parsed


def refresh_index() -> RegistryIndex:
    """Download the index again, rather than reading the cached copy, and return it."""
    fetch_index_files.invalidate(smarter_settings.extension_registry_url)
    return get_index()


def download(version: RegistryVersion) -> bytes:
    """
    Download an extension archive, and check it against the signed index's sha256.

    :param version: The version to download.
    :returns: The archive's bytes.
    :raises SmarterExtensionRegistryError: If it cannot be downloaded, or does not match its sha256.
    """
    try:
        data = fetch(version.archive_url, max_bytes=MAX_ARCHIVE_BYTES, timeout=60).content
    except SafeHttpError as e:
        raise SmarterExtensionRegistryError(f"the archive cannot be downloaded: {e}") from e
    digest = hashlib.sha256(data).hexdigest()
    if digest != version.sha256:
        raise SmarterExtensionRegistryError(
            f"the archive's sha256 is {digest}, but the registry says {version.sha256}: it was not installed"
        )
    return data


def install_from_registry(slug: str, version: Optional[str] = None, user: Optional[User] = None) -> Extension:
    """
    Install an extension from the registry, or update an installed one.

    :param slug: The extension's slug.
    :param version: The version to install; the newest compatible version if None.
    :param user: The superuser who installs it.
    :returns: The extension, installed but disabled if it is new.
    :raises SmarterExtensionRegistryError: If the registry, the extension or the version cannot be found or downloaded.
    """
    index = get_index()
    entry = index.extension(slug)
    if entry is None:
        raise SmarterExtensionRegistryError(f"the registry has no extension {slug}")
    chosen = entry.find_version(version) if version else entry.latest_compatible()
    if chosen is None:
        raise SmarterExtensionRegistryError(
            f"the registry has no version {version} of {slug}"
            if version
            else f"no version of {slug} is compatible with Smarter {smarter_version}"
        )
    existing = Extension.objects.filter(slug=slug).first()
    if existing is not None and existing.source != ExtensionSource.REGISTRY:
        raise SmarterExtensionRegistryError(
            f"{slug} was installed from an uploaded archive; uninstall it before installing it from the registry"
        )
    extension = ExtensionInstaller(user=user).install(
        download(chosen),
        source=ExtensionSource.REGISTRY,
        trust_badge=index.badge_of(entry),
        publisher=entry.publisher,
        source_url=chosen.archive_url,
    )
    record_latest(extension, entry)
    return extension


def record_latest(extension: Extension, entry: Optional[RegistryExtension]) -> None:
    """Record an extension's newest compatible version in the registry, and when it was checked."""
    latest = entry.latest_compatible() if entry else None
    extension.latest_version = latest.version if latest else ""
    extension.latest_checked_at = timezone.now()
    extension.save(update_fields=["latest_version", "latest_checked_at", "updated_at"])


def check_for_updates(refresh: bool = False) -> list[Extension]:
    """
    Record the newest compatible version of every extension installed from the registry.

    Extensions installed from uploaded archives are not checked, so that an upload is never
    offered a registry package that happens to have the same slug.

    :param refresh: Whether to download the index again, rather than reading the cached copy.
    :returns: The extensions for which an update is available.
    :raises SmarterExtensionRegistryError: If the registry cannot be read.
    """
    index = refresh_index() if refresh else get_index()
    updates = []
    for extension in Extension.objects.filter(source=ExtensionSource.REGISTRY).select_related("installed_version"):
        record_latest(extension, index.extension(extension.slug))
        if extension.update_available:
            updates.append(extension)
    logger.info(
        "%s.check_for_updates() updates are available for: %s", logger_prefix, [extension.slug for extension in updates]
    )
    return updates


__all__ = [
    "RegistryExtension",
    "RegistryIndex",
    "RegistryPublisher",
    "RegistryVersion",
    "check_for_updates",
    "index_json_schema",
    "download",
    "get_index",
    "install_from_registry",
    "is_enabled",
    "refresh_index",
    "verify",
]
