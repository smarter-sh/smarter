"""Test the dump_django_settings management command."""

from contextlib import redirect_stdout
from io import StringIO

from django.core.management import call_command

from smarter.lib.unittest.base_classes import SmarterTestBase


class TestDumpDjangoSettings(SmarterTestBase):
    """Test that dump_django_settings prints each Django setting."""

    def test_dump_django_settings(self):
        out = StringIO()
        with redirect_stdout(out):
            call_command("dump_django_settings", stdout=StringIO(), stderr=StringIO())
        self.assertIn("INSTALLED_APPS:", out.getvalue())
