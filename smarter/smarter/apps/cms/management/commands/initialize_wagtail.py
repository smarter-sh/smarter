"""This module is used to initialize the Wagtail CMS. It is used to create the root page and the home page."""

from django.core.management.base import BaseCommand
from wagtail.models import Page, Site


# pylint: disable=E1101
class Command(BaseCommand):
    """Django manage.py initialize_wagailt command. This module is used to initialize the Wagtail CMS. It is used to create the root page and the home page."""

    def handle(self, *args, **options):

        root_page = Page.objects.filter(depth=1).first()
        if not root_page:
            # Create a new root page
            root_page = Page(title="Root", slug="root", depth=1, path="0001")
            root_page.save()
            print("Root page created.")
        else:
            print("Root page already exists.")

        # Create or update the site record
        site = Site.objects.first()
        if site:
            site.root_page = root_page
            site.save()
            print("Default site already exists.")
        else:
            Site.objects.create(hostname="localhost", root_page=root_page, is_default_site=True)
            print("Default site created.")
