"""Base class for testing the api app's management commands."""

from io import StringIO

from django.core.management import call_command

from smarter.apps.account.tests.mixins import TestAccountMixin


class CommandTestBase(TestAccountMixin):
    """Run a management command, and return its output."""

    def run_command(self, command_name: str, *args, **options) -> str:
        out = StringIO()
        call_command(command_name, *args, stdout=out, stderr=out, **options)
        return out.getvalue()
