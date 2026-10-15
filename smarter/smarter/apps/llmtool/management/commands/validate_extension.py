"""Validate a Smarter Extension's source directory or archive, as the registry and the installer will."""

import json
from pathlib import Path

from smarter.apps.llmtool.extension.archive import ExtensionArchive, build_archive
from smarter.apps.llmtool.extension.exceptions import SmarterExtensionException
from smarter.apps.llmtool.extension.loader import load_archive, unload
from smarter.lib.django.management.base import SmarterCommand


class Command(SmarterCommand):
    """Django manage.py validate_extension command."""

    help = (
        "Validate a Smarter Extension: its pyproject.toml, its compatibility with this platform, that its code "
        "imports, and its tools. Prints each tool's definition, as the LLM will see it."
    )

    def add_arguments(self, parser):
        parser.add_argument("path", type=str, help="The extension's source directory, or its .zip archive.")

    def handle(self, *args, **options):
        self.handle_begin()
        path = Path(options["path"])
        try:
            data = path.read_bytes() if path.is_file() else build_archive(path)
            archive = ExtensionArchive(data)
            manifest = archive.manifest
            self.stdout.write(f"{manifest.display_name} ({manifest.slug} {manifest.version}), sha256 {archive.sha256}")
            problems = manifest.compatibility_problems()
            if problems:
                raise SmarterExtensionException("not compatible with this platform: " + "; ".join(problems))
            loaded = load_archive(archive)
            for tool in loaded.tools.values():
                definition = {
                    "name": tool.name,
                    "description": tool.tool_description(),
                    "parameters": tool.parameters(),
                }
                self.stdout.write(json.dumps(definition, indent=2))
            unload(manifest.slug)
        except (OSError, SmarterExtensionException) as e:
            self.handle_completed_failure(e, f"{path} is not a valid extension: {e}")
            return
        self.stdout.write(self.style.SUCCESS(f"{path} is a valid extension."))
        self.handle_completed_success()
