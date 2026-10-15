"""Build a Smarter Extension's archive from its source directory."""

from pathlib import Path

from smarter.apps.llmtool.extension.archive import ExtensionArchive, build_archive
from smarter.apps.llmtool.extension.exceptions import SmarterExtensionException
from smarter.lib.django.management.base import SmarterCommand


class Command(SmarterCommand):
    """Django manage.py package_extension command."""

    help = (
        "Build a Smarter Extension's .zip archive, <slug>-<version>.zip, from its source directory, and print "
        "its sha256 for the registry. The same source always builds the same archive."
    )

    def add_arguments(self, parser):
        parser.add_argument("path", type=str, help="The extension's source directory, which holds its pyproject.toml.")
        parser.add_argument("--output", type=str, default=".", help="The directory to write the archive to.")

    def handle(self, *args, **options):
        self.handle_begin()
        source, output = Path(options["path"]), Path(options["output"])
        try:
            archive = ExtensionArchive(build_archive(source))
            output.mkdir(parents=True, exist_ok=True)
            target = output / f"{archive.manifest.slug}-{archive.manifest.version}.zip"
            target.write_bytes(archive.data)
        except (OSError, SmarterExtensionException) as e:
            self.handle_completed_failure(e, f"{source} could not be packaged: {e}")
            return
        self.stdout.write(f"{target}\nsha256: {archive.sha256}")
        self.handle_completed_success()
