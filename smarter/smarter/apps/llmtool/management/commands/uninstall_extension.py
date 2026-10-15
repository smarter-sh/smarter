"""Uninstall a Smarter Extension."""

from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.llmtool.extension.exceptions import SmarterExtensionException
from smarter.apps.llmtool.extension.installer import ExtensionInstaller
from smarter.apps.llmtool.models import Extension
from smarter.lib.django.management.base import SmarterCommand


class Command(SmarterCommand):
    """Django manage.py uninstall_extension command."""

    help = "Uninstall a Smarter Extension: its SAM resources, waffle switches, settings, versions and LLMClient links."

    def add_arguments(self, parser):
        parser.add_argument("slug", type=str, help="The extension's slug.")

    def handle(self, *args, **options):
        self.handle_begin()
        slug = options["slug"]
        extension = Extension.objects.filter(slug=slug).first()
        if extension is None:
            self.handle_completed_failure(ValueError(slug), f"No extension {slug} is installed.")
            return
        try:
            ExtensionInstaller(user=smarter_cached_objects.smarter_admin).uninstall(extension)
        except SmarterExtensionException as e:
            self.handle_completed_failure(e, f"{slug} was not uninstalled: {e}")
            return
        self.stdout.write(f"Uninstalled {slug}.")
        self.handle_completed_success()
