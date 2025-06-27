"""
This module is used to load Wagtail CMS page content.

mcdaniel jun-2024: it's unclear whether we actually
need this module, since we're simultaneously
installing https://wagtail.github.io/wagtail-transfer/
which is a more comprehensive tool for transferring
Wagtail content between environments.
"""

import json

from django.core.management import call_command
from django.core.management.base import BaseCommand
from wagtail.documents.models import Document
from wagtail.images.models import Image
from wagtail.models import Page, Revision

from smarter.apps.account.models import Account
from smarter.apps.account.models import UserClass as User
from smarter.apps.account.models import UserProfile
from smarter.apps.cms.const import WAGTAIL_DUMP
from smarter.common.const import SMARTER_ACCOUNT_NUMBER


# pylint: disable=E1101
class Command(BaseCommand):
    """
    Django manage.py load_wagtail_data command. This module is used to load
    Wagtail CMS page and snippet content.
    It loads from a JSON file using Django's loaddata command.
    """

    help = "Load Wagtail CMS page and snippet content to a JSON file."
    _account: Account
    _user: User

    @property
    def account(self) -> Account:
        if self._account is None:
            self._account = Account.objects.get(account_number=SMARTER_ACCOUNT_NUMBER)
        return self._account

    @property
    def admin_user(self) -> User:
        if self._user is None:
            user_profile = UserProfile.objects.filter(user__is_superuser=True, user__is_active=True).first()
            if user_profile:
                self._user = user_profile.user
        return self._user

    def add_missing_users(self, file_path):
        with open(file_path, encoding="utf-8") as file:
            data = json.load(file)

        # Modify user_id if necessary
        for obj in data:
            if "fields" in obj and "user" in obj["fields"]:
                user_id = obj["fields"]["user"]
                if not User.objects.filter(id=user_id).exists():
                    username = "wagtail_" + str(user_id)
                    user = User.objects.create_user(
                        id=user_id,
                        username=username,
                        first_name=username,
                        last_name=username,
                        email=username + "@smarter.sh",
                        is_active=True,
                        is_staff=True,
                        is_superuser=False,
                    )
                    self.stdout.write(self.style.SUCCESS(f"Added user {user.get_username()}"))

    def handle(self, *args, **options):
        """Load Wagtail CMS page and snippet content from a JSON file."""

        # Delete existing revisions and pages except for the root page
        Revision.objects.all().delete()
        self.stdout.write(self.style.SUCCESS("Deleted all existing Wagtail revisions."))

        # Delete existing pages except for the root page
        Page.objects.exclude(depth=1).delete()
        self.stdout.write(self.style.SUCCESS("Deleted all existing Wagtail pages except for the root page."))

        Image.objects.all().delete()
        self.stdout.write(self.style.SUCCESS("Deleted all existing Wagtail images."))

        # Delete existing documents (if applicable)
        Document.objects.all().delete()
        self.stdout.write(self.style.SUCCESS("Deleted all existing Wagtail documents."))

        self.add_missing_users(WAGTAIL_DUMP)

        call_command("loaddata", WAGTAIL_DUMP)
        self.stdout.write(self.style.SUCCESS(f"Loaded wagtail data from {WAGTAIL_DUMP}"))
