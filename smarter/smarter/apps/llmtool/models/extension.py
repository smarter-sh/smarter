"""
Smarter Extension models.

An :class:`Extension` is an installable Python package that adds LLM tools to the platform.
Only superusers install, update, configure and uninstall extensions, from the Django admin
console. The code of an extension is stored in the database, as the archive of each
:class:`ExtensionVersion`, so that every process of every pod loads the same code without
a redeploy. See :mod:`smarter.apps.llmtool.extension`.
"""

from typing import Optional

from django.db import models
from pydantic import ValidationError

from smarter.apps.account.models import Account, User, UserProfile
from smarter.apps.secret.models import Secret
from smarter.lib import logging
from smarter.lib.django.models import TimestampedModel
from smarter.lib.django.waffle import SmarterWaffleSwitches

from ..extension.manifest import ExtensionManifest

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.EXTENSION_LOGGING])


class ExtensionSource(models.TextChoices):
    """Where an extension was installed from."""

    REGISTRY = "registry", "Registry"
    UPLOAD = "upload", "Upload"


class ExtensionTrustBadge(models.TextChoices):
    """
    How far an extension's publisher is trusted, as shown in the admin console and the registry.

    The registry assigns ``official``, ``verified`` and ``community``. An uploaded archive,
    which did not come from the registry, is ``unverified``.
    """

    OFFICIAL = "official", "Official Smarter Extension"
    VERIFIED = "verified", "Verified Publisher"
    COMMUNITY = "community", "Community"
    UNVERIFIED = "unverified", "Unverified"


class Extension(TimestampedModel):
    """
    An installed Smarter Extension.

    There is one row per extension, whatever its version. :attr:`installed_version` is the
    version that runs, and :attr:`latest_version` is the newest compatible version that the
    registry offers, so that the admin console can say an update is available.

    An extension runs only while it is :attr:`enabled`, and only for the LLMClients of the
    accounts it is available to: every account if :attr:`all_accounts`, otherwise the
    :attr:`accounts` listed.
    """

    # pylint: disable=missing-class-docstring
    class Meta:
        verbose_name = "Extension"
        verbose_name_plural = "Extensions"
        ordering = ("slug",)

    slug = models.CharField(max_length=32, unique=True, help_text="The extension's permanent identifier, e.g. weather.")
    display_name = models.CharField(max_length=255, help_text="The extension's name, as shown to people.")
    description = models.TextField(blank=True, default="", help_text="A one-line description.")
    publisher = models.CharField(
        max_length=255, blank=True, default="", help_text="The publisher's registry id, or the archive's authors."
    )
    source = models.CharField(max_length=16, choices=ExtensionSource.choices, default=ExtensionSource.UPLOAD)
    trust_badge = models.CharField(
        max_length=16, choices=ExtensionTrustBadge.choices, default=ExtensionTrustBadge.UNVERIFIED
    )
    enabled = models.BooleanField(default=False, help_text="Whether the extension's tools are offered to LLMs.")
    installed_version = models.ForeignKey(
        "ExtensionVersion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="The version that runs.",
    )
    latest_version = models.CharField(
        max_length=64, blank=True, default="", help_text="The newest compatible version in the registry."
    )
    latest_checked_at = models.DateTimeField(
        null=True, blank=True, help_text="When the registry was last checked for updates."
    )
    all_accounts = models.BooleanField(default=True, help_text="Whether every account may use the extension.")
    accounts = models.ManyToManyField(
        Account,
        blank=True,
        related_name="extensions",
        help_text="The accounts that may use the extension, when it is not available to all accounts.",
    )
    error = models.TextField(
        blank=True, default="", help_text="The last error from loading the extension or running its lifecycle hooks."
    )

    def __str__(self) -> str:
        version = self.installed_version.version if self.installed_version else "not installed"
        return f"{self.display_name} ({self.slug} {version})"

    @property
    def update_available(self) -> bool:
        """Whether the registry offers a newer version than the installed one."""
        # pylint: disable=import-outside-toplevel
        from packaging.version import InvalidVersion, Version

        if not self.latest_version or not self.installed_version:
            return False
        try:
            return Version(self.latest_version) > Version(self.installed_version.version)
        except InvalidVersion:
            return False

    def is_available_to(self, account: Optional[Account]) -> bool:
        """
        Return whether an account may use this extension.

        :param account: The account, e.g. the owner of an LLMClient.
        :returns: True if the extension is available to all accounts, or to this one.
        """
        if self.all_accounts:
            return True
        if account is None:
            return False
        return self.accounts.filter(pk=account.pk).exists()


class ExtensionVersion(TimestampedModel):
    """
    One installed version of an extension: its archive, manifest and documentation.

    Versions are kept after an update, so that an administrator can roll back to one.
    """

    # pylint: disable=missing-class-docstring
    class Meta:
        verbose_name = "Extension Version"
        verbose_name_plural = "Extension Versions"
        unique_together = ("extension", "version")
        ordering = ("extension", "-created_at")

    extension = models.ForeignKey(Extension, on_delete=models.CASCADE, related_name="versions")
    version = models.CharField(max_length=64, help_text="The version, from the manifest, e.g. 1.2.0.")
    archive = models.BinaryField(help_text="The extension's zip archive.")
    sha256 = models.CharField(max_length=64, help_text="The hex sha256 of the archive.")
    manifest = models.JSONField(help_text="The archive's pyproject.toml, as an ExtensionManifest.")
    docstring = models.TextField(blank=True, default="", help_text="The package's module docstring (reStructuredText).")
    docs_html = models.TextField(blank=True, default="", help_text="The docstring, rendered as HTML.")
    source_url = models.URLField(max_length=1024, blank=True, default="", help_text="Where the archive was downloaded.")
    installed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")

    def __str__(self) -> str:
        return f"{self.extension.slug} {self.version}"

    @property
    def parsed_manifest(self) -> ExtensionManifest:
        """The version's manifest, as an :class:`~smarter.apps.llmtool.extension.manifest.ExtensionManifest`."""
        try:
            return ExtensionManifest.model_validate(self.manifest)
        except ValidationError as e:
            logger.error(
                "%s.parsed_manifest() %s has an invalid stored manifest: %s", self.formatted_class_name, self, e
            )
            raise


class ExtensionSetting(TimestampedModel):
    """
    The configured value of one of an extension's settings.

    A ``secret`` setting refers to a :class:`~smarter.apps.secret.models.Secret` rather
    than storing a value, so that it is encrypted at rest.
    """

    # pylint: disable=missing-class-docstring
    class Meta:
        verbose_name = "Extension Setting"
        verbose_name_plural = "Extension Settings"
        unique_together = ("extension", "name")

    extension = models.ForeignKey(Extension, on_delete=models.CASCADE, related_name="settings")
    name = models.CharField(max_length=255, help_text="The setting's name, as declared in the manifest.")
    value = models.TextField(blank=True, default="", help_text="The value, as text. Empty for a secret setting.")
    secret = models.ForeignKey(
        Secret,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="The Secret that holds a secret setting's value.",
    )

    def __str__(self) -> str:
        return f"{self.extension.slug}.{self.name}"


class ExtensionResource(TimestampedModel):
    """
    A SAM resource that an extension created, so that uninstalling it deletes exactly what it created.

    Resources are created from the manifests in the package's ``manifests/`` directory, and
    by lifecycle hooks with
    :meth:`~smarter.apps.llmtool.extension.lifecycle.LifecycleContext.apply_manifest`.
    """

    # pylint: disable=missing-class-docstring
    class Meta:
        verbose_name = "Extension Resource"
        verbose_name_plural = "Extension Resources"
        unique_together = ("extension", "kind", "name", "user_profile")

    extension = models.ForeignKey(Extension, on_delete=models.CASCADE, related_name="resources")
    kind = models.CharField(max_length=64, help_text="The resource's SAM kind, e.g. Secret.")
    name = models.CharField(max_length=255, help_text="The resource's name.")
    user_profile = models.ForeignKey(
        UserProfile, on_delete=models.CASCADE, related_name="+", help_text="The resource's owner."
    )
    version = models.CharField(max_length=64, help_text="The extension version that created or last applied it.")
    managed = models.BooleanField(
        default=True,
        help_text="Whether it came from the package's manifests/ directory, rather than a lifecycle hook.",
    )

    def __str__(self) -> str:
        return f"{self.extension.slug}: {self.kind} {self.name}"


__all__ = [
    "Extension",
    "ExtensionResource",
    "ExtensionSetting",
    "ExtensionSource",
    "ExtensionTrustBadge",
    "ExtensionVersion",
]
