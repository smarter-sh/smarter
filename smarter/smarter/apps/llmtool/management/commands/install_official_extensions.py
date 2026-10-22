"""Install the official Smarter Extensions from the registry."""

from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.llmtool.const import OFFICIAL_EXTENSIONS
from smarter.apps.llmtool.extension import registry
from smarter.apps.llmtool.extension.exceptions import SmarterExtensionInstallError
from smarter.apps.llmtool.extension.installer import ExtensionInstaller
from smarter.apps.llmtool.extension.manifest import ExtensionSettingType
from smarter.apps.llmtool.models import Extension
from smarter.apps.secret.models import Secret
from smarter.lib.django.management.base import SmarterCommand


class Command(SmarterCommand):
    """
    Django manage.py install_official_extensions command.

    ``manage.py initialize_platform`` runs it before it loads the example manifests, whose LLMClients
    list the official extensions: an LLMClient that needs an extension that is not installed is
    skipped.
    """

    help = (
        "Install, or update, the official Smarter Extensions from the registry, and enable those whose required "
        "settings can be configured. Does nothing while the registry is disabled. Exits with code 1 if an official "
        "extension could not be installed and enabled, e.g. because it is not compatible with this platform."
    )

    def configure(self, installer: ExtensionInstaller, extension: Extension) -> None:
        """
        Configure each unset secret setting whose name is the name of one of the platform admin's Secrets.

        ``initialize_providers`` creates the platform's Secrets, e.g. ``google_maps_api_key``, which
        the weather extension's setting of the same name then uses.
        """
        manifest = extension.installed_version.parsed_manifest  # type: ignore[union-attr]
        owner = smarter_cached_objects.smarter_admin_user_profile
        values = {}
        for spec in manifest.smarter.settings:
            secret = Secret.objects.filter(user_profile=owner, name=spec.name).first()
            if spec.type == ExtensionSettingType.SECRET and secret is not None and not extension.settings.filter(name=spec.name).exists():  # type: ignore[attr-defined]
                values[spec.name] = secret
        if values:
            installer.configure(extension, values)

    def install(self) -> None:
        """
        Install, or update, and enable each official extension, as the Smarter admin.

        :raises SmarterExtensionInstallError: If any official extension was not installed and enabled,
            after every one was attempted: the example LLMClients that use a missing official extension
            are skipped, so a deployment without one is broken, and the init job must fail.
        """
        if not registry.is_enabled():
            self.stdout.write(self.style.WARNING("The extension registry is disabled: no extensions were installed."))
            return
        installer = ExtensionInstaller(user=smarter_cached_objects.smarter_admin)
        failed = []
        for slug in OFFICIAL_EXTENSIONS:
            try:
                existing = Extension.objects.filter(slug=slug).first()
                if existing is not None and existing.source != "registry":
                    self.stdout.write(self.style.WARNING(f"Skipped {slug}: it was installed from an uploaded archive."))
                    continue
                extension = registry.install_from_registry(slug, user=smarter_cached_objects.smarter_admin)
                self.configure(installer, extension)
                if not extension.enabled:
                    installer.enable(extension)
                self.stdout.write(f"Installed and enabled {slug} {extension.installed_version.version}.")  # type: ignore[union-attr]
            # pylint: disable=broad-except
            except Exception as e:
                failed.append(f"{slug}: {e}")
        if failed:
            message = "Official extensions that were not installed and enabled:\n" + "\n".join(failed)
            self.stdout.write(self.style.ERROR(message))
            raise SmarterExtensionInstallError(message)

    def handle(self, *args, **options):
        """Install, or update, and enable the official extensions."""
        self.handle_begin()
        try:
            self.install()
        # pylint: disable=broad-except
        except Exception as exc:
            # exits with code 1.
            self.handle_completed_failure(exc, f"Failed to install the official extensions: {exc}")
            raise
        self.handle_completed_success()
