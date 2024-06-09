"""This module is used to generate a JSON list of all accounts, printed to the command line, using manage.py"""

import re

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand

from smarter.apps.account.models import Account
from smarter.apps.account.serializers import AccountSerializer


# pylint: disable=E1101
class Command(BaseCommand):
    """Django manage.py get_plugins command. This command is used to generate a JSON list of all accounts."""

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument(
            "name_spec", type=str, nargs="?", default=None, help="A regular expression to filter account names."
        )

    def validate_regex(self, regex):
        try:
            re.compile(regex)
            return True
        except re.error:
            return False

    def handle(self, *args, **options):
        name_spec = options["name_spec"]

        if name_spec:
            if self.validate_regex(regex=name_spec):
                accounts = Account.objects.filter(name__regex=name_spec)
            else:
                raise ValidationError("Invalid regular expression provided for name_spec")
        else:
            accounts = Account.objects.all()

        serializer = AccountSerializer(accounts, many=True)
        print(serializer.data)
