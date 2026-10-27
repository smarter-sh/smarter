"""
Install, update, configure, enable, disable, roll back and uninstall extensions.

:class:`ExtensionInstaller` is the one place where an extension's state changes. The admin
console, the management commands and the registry client all go through it, so every
action validates the archive, checks compatibility, runs the lifecycle hooks, and manages
the extension's switches and SAM resources the same way.

An install or update proceeds in this order:

1. Validate the archive and its manifest, and check that the extension is compatible with
   this platform (Python, Smarter and dependency versions).
2. Import its code in this process, which proves that it loads and that its tools are valid,
   before anything is saved.
3. In a database transaction: save the version, run ``pre_install`` or ``pre_upgrade``, and
   make the version the installed one. A hook that raises rolls all of it back.
4. Create its waffle switches, apply its manifests (and on an upgrade, delete the resources
   that the new version no longer ships), and run ``post_install`` or ``post_upgrade``. A
   failure here leaves the extension installed but disabled, with the error recorded.

A new extension is installed disabled, as a WordPress plugin is installed inactive: an
administrator configures its settings, then enables it.
"""

from typing import Optional, Union

from django.db import transaction

from smarter.apps.account.models import User, UserProfile
from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.llmtool.models import (
    Extension,
    ExtensionResource,
    ExtensionSetting,
    ExtensionSource,
    ExtensionTrustBadge,
    ExtensionVersion,
)
from smarter.apps.llmtool.signals import (
    extension_disabled,
    extension_enabled,
    extension_installed,
    extension_uninstalled,
    extension_upgraded,
)
from smarter.apps.secret.models import Secret
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .archive import MANIFESTS_DIRECTORY, ExtensionArchive
from .docs import render_rst
from .exceptions import SmarterExtensionInstallError, SmarterExtensionLoadError
from .lifecycle import LifecycleContext, SmarterExtensionLifecycle
from .loader import LoadedExtension, load_archive, load_version, unload
from .manifest import ExtensionManifest, ExtensionSettingType, SettingValue
from .resources import (
    apply_extension_manifest,
    create_switches,
    delete_extension_resource,
    delete_switches,
)
from .settings import missing_required_settings, resolve_settings

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.EXTENSION_LOGGING])

MANIFEST_SUFFIXES = (".yaml", ".yml", ".json")

SettingInput = Union[SettingValue, Secret, None]
"""A value to configure: text or a typed value, a Secret for a secret setting, or None to clear it."""


class ExtensionInstaller:
    """
    Carry out administrators' actions on extensions.

    :param user: The superuser who carries out the actions. Resources that extensions create
        are owned by the platform's admin user profile, not by this user, so that they outlive
        the user's account.

    **Example usage**::

        installer = ExtensionInstaller(user=request.user)
        extension = installer.install(uploaded_file.read())
        installer.configure(extension, {"google_maps_api_key": secret})
        installer.enable(extension)
    """

    def __init__(self, user: Optional[User] = None):
        self.user = user
        self.owner: UserProfile = smarter_cached_objects.smarter_admin_user_profile

    @property
    def formatted_class_name(self) -> str:
        """The class name, for logging."""
        return f"{logging.SmarterFormattedText.text(__name__)}.{self.__class__.__name__}"

    def context(
        self, extension: Extension, manifest: ExtensionManifest, previous_version: Optional[str] = None
    ) -> LifecycleContext:
        """Return the context of a lifecycle hook."""
        return LifecycleContext(
            extension=extension,
            version=manifest.version,
            previous_version=previous_version,
            settings=resolve_settings(extension, manifest),
            user_profile=self.owner,
        )

    # -------------------------------------------------------------------------
    # install, update and roll back
    # -------------------------------------------------------------------------
    def install(
        self,
        data: bytes,
        source: str = ExtensionSource.UPLOAD,
        trust_badge: str = ExtensionTrustBadge.UNVERIFIED,
        publisher: Optional[str] = None,
        source_url: str = "",
    ) -> Extension:
        """
        Install an extension archive, or update an installed extension to the archive's version.

        Installing the version that is already installed, from the same archive, does nothing.

        :param data: The archive's bytes.
        :param source: Where the archive came from.
        :param trust_badge: The publisher's trust badge, from the registry, or ``unverified`` for an upload.
        :param publisher: The publisher's registry id; defaults to the manifest's authors.
        :param source_url: Where the archive was downloaded from, if anywhere.
        :returns: The extension.
        :raises SmarterExtensionArchiveError: If the archive is not valid.
        :raises SmarterExtensionManifestError: If its manifest is not valid.
        :raises SmarterExtensionInstallError: If it is not compatible, conflicts with an installed version, or a pre hook refuses it.
        :raises SmarterExtensionLoadError: If its code does not load.
        """
        archive = ExtensionArchive(data)
        manifest = archive.manifest
        problems = manifest.compatibility_problems()
        if problems:
            raise SmarterExtensionInstallError(
                f"{manifest.slug} {manifest.version} is not compatible with this platform: {'; '.join(problems)}"
            )
        extension = Extension.objects.filter(slug=manifest.slug).select_related("installed_version").first()
        existing = ExtensionVersion.objects.filter(extension=extension, version=manifest.version).first()
        if existing is not None and existing.sha256 != archive.sha256:
            raise SmarterExtensionInstallError(
                f"{manifest.slug} {manifest.version} is already installed from a different archive. "
                "Publish a new version rather than changing a released one."
            )
        if extension is not None and extension.installed_version_id == getattr(existing, "pk", None):  # type: ignore[attr-defined]
            logger.info(
                "%s.install() %s %s is already installed", self.formatted_class_name, manifest.slug, manifest.version
            )
            return extension

        loaded = load_archive(archive)
        publisher = publisher or ", ".join(str(author) for author in manifest.project.authors if str(author))
        previous_version = extension.installed_version.version if extension and extension.installed_version else None
        lifecycle = loaded.lifecycle() if loaded.lifecycle else None

        with transaction.atomic():
            if extension is None:
                extension = Extension.objects.create(slug=manifest.slug, display_name=manifest.display_name)
            extension.display_name = manifest.display_name
            extension.description = manifest.project.description
            extension.publisher = publisher
            extension.source = source
            extension.trust_badge = trust_badge
            version = existing or ExtensionVersion.objects.create(
                extension=extension,
                version=manifest.version,
                archive=archive.data,
                sha256=archive.sha256,
                manifest=manifest.model_dump(mode="json"),
                docstring=archive.docstring,
                docs_html=render_rst(archive.docstring),
                source_url=source_url,
                installed_by=self.user,
            )
            if lifecycle is not None:
                context = self.context(extension, manifest, previous_version)
                if previous_version is None:
                    lifecycle.pre_install(context)
                else:
                    lifecycle.pre_upgrade(context)
            extension.installed_version = version
            extension.error = ""
            extension.save()

        self.finish_install(extension, version, loaded, lifecycle, previous_version)
        return extension

    def finish_install(
        self,
        extension: Extension,
        version: ExtensionVersion,
        loaded: LoadedExtension,
        lifecycle: Optional[SmarterExtensionLifecycle],
        previous_version: Optional[str],
    ) -> None:
        """
        Create the switches, apply the manifests and run the post hook of a version that was just installed.

        A failure leaves the extension installed but disabled, with the error recorded.
        """
        manifest = loaded.manifest
        try:
            if previous_version is not None:
                previous = ExtensionVersion.objects.filter(extension=extension, version=previous_version).first()
                if previous is not None:
                    delete_switches(
                        previous.parsed_manifest, keep=frozenset(spec.name for spec in manifest.smarter.switches)
                    )
            create_switches(manifest)
            self.apply_manifests(extension, loaded)
            if lifecycle is not None:
                context = self.context(extension, manifest, previous_version)
                if previous_version is None:
                    lifecycle.post_install(context)
                else:
                    lifecycle.post_upgrade(context)
        # a post hook is the extension's code, which can fail in any way at all.
        # pylint: disable=broad-exception-caught
        except Exception as e:
            self.record_failure(extension, f"{manifest.slug} {manifest.version} was installed, but: {e}")
            return
        if extension.enabled and missing_required_settings(extension, manifest):
            self.record_failure(
                extension,
                f"{manifest.slug} {manifest.version} needs settings that are not configured: "
                f"{', '.join(missing_required_settings(extension, manifest))}",
            )
        if previous_version is None:
            extension_installed.send(sender=self.__class__, extension=extension, version=version)
        else:
            extension_upgraded.send(
                sender=self.__class__, extension=extension, version=version, previous_version=previous_version
            )
        logger.info(
            "%s.finish_install() installed %s %s (was %s)",
            self.formatted_class_name,
            manifest.slug,
            manifest.version,
            previous_version,
        )

    def apply_manifests(self, extension: Extension, loaded: LoadedExtension) -> None:
        """
        Apply the SAM manifests in a version's ``manifests/`` directory, in filename order.

        Resources that an earlier version applied from its manifests, and that this version
        no longer ships, are deleted.
        """
        manifests_dir = loaded.path / loaded.manifest.smarter.package / MANIFESTS_DIRECTORY
        applied: set[tuple[str, str]] = set()
        if manifests_dir.is_dir():
            for path in sorted(manifests_dir.iterdir()):
                if path.suffix.lower() in MANIFEST_SUFFIXES and path.is_file():
                    applied.add(
                        apply_extension_manifest(
                            extension, path.read_text(encoding="utf-8"), self.owner, loaded.version, managed=True
                        )
                    )
        for resource in ExtensionResource.objects.filter(extension=extension, managed=True):
            if (resource.kind, resource.name) not in applied:
                delete_extension_resource(extension, resource.kind, resource.name, resource.user_profile)

    def rollback(self, extension: Extension, version: ExtensionVersion) -> Extension:
        """
        Make an earlier installed version the one that runs, as an update to it would.

        :param extension: The extension.
        :param version: One of its versions.
        :returns: The extension.
        """
        if version.extension_id != extension.pk:  # type: ignore[attr-defined]
            raise SmarterExtensionInstallError(f"{version} is not a version of {extension.slug}")
        data = bytes(ExtensionVersion.objects.values_list("archive", flat=True).get(pk=version.pk))
        return self.install(
            data, source=extension.source, trust_badge=extension.trust_badge, publisher=extension.publisher
        )

    # -------------------------------------------------------------------------
    # configure, enable and disable
    # -------------------------------------------------------------------------
    def configure(self, extension: Extension, values: dict[str, SettingInput]) -> None:
        """
        Set some of an extension's settings.

        :param extension: The extension.
        :param values: The values, by setting name. A secret setting takes a Secret; None clears a setting.
        :raises SmarterExtensionInstallError: If a setting is not declared, or a value is not valid.
        """
        manifest = self.installed_manifest(extension)
        for name, value in values.items():
            spec = manifest.setting(name)
            if spec is None:
                raise SmarterExtensionInstallError(f"{extension.slug} has no setting {name}")
            if value is None:
                ExtensionSetting.objects.filter(extension=extension, name=name).delete()
                continue
            if spec.type == ExtensionSettingType.SECRET:
                if not isinstance(value, Secret):
                    raise SmarterExtensionInstallError(
                        f"{extension.slug}.{name} is a secret setting: its value must be a Secret"
                    )
                defaults = {"value": "", "secret": value}
            else:
                if isinstance(value, Secret):
                    raise SmarterExtensionInstallError(f"{extension.slug}.{name} is not a secret setting")
                try:
                    coerced = spec.coerce(value)
                except ValueError as e:
                    raise SmarterExtensionInstallError(str(e)) from e
                defaults = {
                    "value": str(coerced).lower() if isinstance(coerced, bool) else str(coerced),
                    "secret": None,
                }
            ExtensionSetting.objects.update_or_create(extension=extension, name=name, defaults=defaults)
        logger.info("%s.configure() configured %s: %s", self.formatted_class_name, extension.slug, sorted(values))

    def enable(self, extension: Extension) -> Extension:
        """
        Enable an extension, so that LLMClients that list it offer its tools.

        :param extension: The extension.
        :returns: The extension.
        :raises SmarterExtensionInstallError: If it is not installed, is incompatible, or has required settings that are not configured.
        :raises SmarterExtensionLoadError: If its code does not load.
        """
        manifest = self.installed_manifest(extension)
        problems = manifest.compatibility_problems()
        if problems:
            raise SmarterExtensionInstallError(
                f"{extension.slug} is not compatible with this platform: {'; '.join(problems)}"
            )
        missing = missing_required_settings(extension, manifest)
        if missing:
            raise SmarterExtensionInstallError(f"{extension.slug} needs these settings first: {', '.join(missing)}")
        loaded = load_version(extension.installed_version)  # type: ignore[arg-type]
        if loaded.lifecycle is not None:
            loaded.lifecycle().on_enable(self.context(extension, manifest))
        extension.enabled = True
        extension.error = ""
        extension.save(update_fields=["enabled", "error", "updated_at"])
        extension_enabled.send(sender=self.__class__, extension=extension)
        logger.info("%s.enable() enabled %s", self.formatted_class_name, extension.slug)
        return extension

    def disable(self, extension: Extension, reason: str = "disabled by an administrator") -> Extension:
        """
        Disable an extension, so that no LLM is offered its tools.

        Takes effect on the next prompt in every pod.

        An ``on_disable`` hook that fails is logged, and the extension is disabled anyway.

        :param extension: The extension.
        :param reason: Why it is disabled.
        :returns: The extension.
        """
        if extension.installed_version is not None:
            try:
                loaded = load_version(extension.installed_version)
                if loaded.lifecycle is not None:
                    loaded.lifecycle().on_disable(self.context(extension, loaded.manifest))
            # a hook is the extension's code, which can fail in any way at all.
            # pylint: disable=broad-exception-caught
            except Exception as e:
                logger.warning("%s.disable() %s on_disable failed: %s", self.formatted_class_name, extension.slug, e)
        extension.enabled = False
        extension.save(update_fields=["enabled", "updated_at"])
        extension_disabled.send(sender=self.__class__, extension=extension, reason=reason)
        logger.info("%s.disable() disabled %s: %s", self.formatted_class_name, extension.slug, reason)
        return extension

    # -------------------------------------------------------------------------
    # uninstall
    # -------------------------------------------------------------------------
    def uninstall(self, extension: Extension) -> None:
        """
        Uninstall an extension: its resources, switches, settings, versions, and LLMClients' links to it.

        :param extension: The extension.
        :raises SmarterExtensionInstallError: If its ``pre_uninstall`` hook refuses.
        """
        slug = extension.slug
        loaded: Optional[LoadedExtension] = None
        lifecycle: Optional[SmarterExtensionLifecycle] = None
        if extension.installed_version is not None:
            try:
                loaded = load_version(extension.installed_version)
                lifecycle = loaded.lifecycle() if loaded.lifecycle else None
            except SmarterExtensionLoadError as e:
                # an extension whose code no longer loads can still be uninstalled, without its hooks.
                logger.warning(
                    "%s.uninstall() %s does not load, so its hooks will not run: %s", self.formatted_class_name, slug, e
                )
        if lifecycle is not None and loaded is not None:
            try:
                lifecycle.pre_uninstall(self.context(extension, loaded.manifest))
            # pylint: disable=broad-exception-caught
            except Exception as e:
                raise SmarterExtensionInstallError(f"{slug} refused to uninstall: {e}") from e
        for resource in ExtensionResource.objects.filter(extension=extension).select_related("user_profile__user"):
            delete_extension_resource(extension, resource.kind, resource.name, resource.user_profile)
        for version in ExtensionVersion.objects.filter(extension=extension):
            delete_switches(version.parsed_manifest)
        if lifecycle is not None and loaded is not None:
            try:
                lifecycle.post_uninstall(self.context(extension, loaded.manifest))
            # pylint: disable=broad-exception-caught
            except Exception as e:
                logger.warning("%s.uninstall() %s post_uninstall failed: %s", self.formatted_class_name, slug, e)
        extension.delete()
        unload(slug)
        extension_uninstalled.send(sender=self.__class__, slug=slug)
        logger.info("%s.uninstall() uninstalled %s", self.formatted_class_name, slug)

    # -------------------------------------------------------------------------
    # helpers
    # -------------------------------------------------------------------------
    def installed_manifest(self, extension: Extension) -> ExtensionManifest:
        """Return the manifest of an extension's installed version."""
        if extension.installed_version is None:
            raise SmarterExtensionInstallError(f"{extension.slug} has no installed version")
        return extension.installed_version.parsed_manifest

    def record_failure(self, extension: Extension, message: str) -> None:
        """Disable an extension, and record why."""
        logger.error("%s %s", self.formatted_class_name, message)
        extension.enabled = False
        extension.error = message
        extension.save(update_fields=["enabled", "error", "updated_at"])
        extension_disabled.send(sender=self.__class__, extension=extension, reason=message)


__all__ = ["ExtensionInstaller", "SettingInput"]
