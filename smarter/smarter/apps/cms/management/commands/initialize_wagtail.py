"""This module is used to initialize the Wagtail CMS. It is used to create the root page and the home page."""

from django.core.management.base import BaseCommand
from wagtail.models import Site

from smarter.apps.cms.models import DocsPage


# pylint: disable=E1101
class Command(BaseCommand):
    """Django manage.py initialize_wagtail command. This module is used to initialize the Wagtail CMS. It is used to create the root page and the home page."""

    def handle(self, *args, **options):

        root_page_title = "Root"
        root_page_slug = "root"
        root_page, created = DocsPage.objects.get_or_create(
            title=root_page_title, slug=root_page_slug, defaults={"depth": 1, "path": "0001", "numchild": 0}
        )
        if created:
            self.stdout.write(self.style.SUCCESS("Successfully created root DocsPage."))
        else:
            self.stdout.write("Root DocsPage already exists.")

        # Set up the default site with the new root page
        site, site_created = Site.objects.update_or_create(
            is_default_site=True, defaults={"hostname": "localhost", "root_page": root_page}
        )
        if site_created:
            self.stdout.write(self.style.SUCCESS("Successfully created the default site."))
        else:
            self.stdout.write("Default site already exists and is updated.")

        if site.root_page != root_page:
            self.stdout.write("Updating the default site root page.")
            site.root_page = root_page
            site.save()
