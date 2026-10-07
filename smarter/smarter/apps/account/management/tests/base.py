"""Base class for testing the account app's management commands."""

from io import StringIO

from django.core.management import call_command
from django.utils.crypto import get_random_string

from smarter.apps.account.tests.mixins import TestAccountMixin


class CommandTestBase(TestAccountMixin):
    """Run a management command, and return its output."""

    def run_command(self, command_name: str, *args, **options) -> str:
        out = StringIO()
        call_command(command_name, *args, stdout=out, stderr=out, **options)
        return out.getvalue()

    def unique(self, prefix: str = "test_cmd") -> str:
        return f"{prefix}_{get_random_string(8).lower()}"
