"""Install, or update, a Smarter Extension from an archive, a source directory, or the registry."""

from pathlib import Path

from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.llmtool.extension import registry
from smarter.apps.llmtool.extension.archive import build_archive
from smarter.apps.llmtool.extension.exceptions import SmarterExtensionException
from smarter.apps.llmtool.extension.installer import ExtensionInstaller
from smarter.lib.django.management.base import SmarterCommand


class Command(SmarterCommand):
    """Django manage.py install_extension command."""

    help = (
        "Install, or update, a Smarter Extension, from a .zip archive, a source directory, or the registry with "
        "--registry <slug>. A new extension is installed disabled, unless --enable is given and its required "
        "settings have defaults."
    )

    def add_arguments(self, parser):
        parser.add_argument("path", type=str, nargs="?", help="The extension's .zip archive or source directory.")
        parser.add_argument("--registry", type=str, help="Install this slug from the extension registry instead.")
        parser.add_argument(
            "--extension-version",
            type=str,
            help="With --registry: the version to install; the newest compatible one if omitted.",
        )
        parser.add_argument("--enable", action="store_true", help="Enable the extension after installing it.")

    def handle(self, *args, **options):
        self.handle_begin()
        user = smarter_cached_objects.smarter_admin
        try:
            if options["registry"]:
                extension = registry.install_from_registry(options["registry"], options["extension_version"], user=user)
            elif options["path"]:
                path = Path(options["path"])
                data = path.read_bytes() if path.is_file() else build_archive(path)
                extension = ExtensionInstaller(user=user).install(data)
            else:
                raise SmarterExtensionException("give an archive or source directory, or --registry <slug>")
            if options["enable"]:
                ExtensionInstaller(user=user).enable(extension)
        except (OSError, SmarterExtensionException) as e:
            self.handle_completed_failure(e, f"The extension was not installed: {e}")
            return
        state = "enabled" if extension.enabled else "disabled"
        self.stdout.write(f"Installed {extension.slug} {extension.installed_version.version}, {state}.")  # type: ignore[union-attr]
        self.handle_completed_success()
