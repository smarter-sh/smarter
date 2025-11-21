"""
This module is used to dump Wagtail CMS page content.

mcdaniel jun-2024: it's unclear whether we actually
need this module, since we're simultaneously
installing https://wagtail.github.io/wagtail-transfer/
which is a more comprehensive tool for transferring
Wagtail content between environments.
"""

from django.core.management import call_command

from smarter.apps.cms.const import WAGTAIL_DUMP
from smarter.lib.django.management.base import SmarterCommand


WAGTAIL_APPS = [
    "cms.RawHtmlSnippet",
    "cms.RawHtmlPage",
    "wagtailforms",
    "wagtailredirects",
    "wagtailembeds",
    "wagtailsites",
    "wagtailusers",
    "wagtailsnippets",
    "wagtaildocs",
    "wagtailimages",
    "wagtailsearch",
    "wagtailadmin",
    "wagtailcore",
]


# pylint: disable=E1101SmarterCommand
class Command(SmarterCommand):
    """Dumps Wagtail CMS page and snippet content to separate JSON files."""

    help = "Dump Wagtail CMS page and snippet content to separate JSON files."

    def handle(self, *args, **options):
        """Dump Wagtail CMS page and snippet content to separate JSON files."""
        self.handle_begin()

        call_command("dumpdata", *WAGTAIL_APPS, indent=2, output=WAGTAIL_DUMP)
        self.handle_completed_success(msg=f"Wagtail data dumped to {WAGTAIL_DUMP}")
