"""Test the get_llmclients management command."""

from contextlib import redirect_stdout
from io import StringIO

from django.core.management import call_command

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.llmclient.models import LLMClient
from smarter.common.exceptions import SmarterValueError


class TestGetLLMClients(TestAccountMixin):
    """Test that get_llmclients prints the hostname of each of an account's LLMClients."""

    def setUp(self):
        super().setUp()
        self.llmclient = LLMClient.objects.create(
            name=f"test_get_llmclients_{self.hash_suffix}", user_profile=self.user_profile
        )
        self.addCleanup(self.llmclient.delete)

    def run_command(self, **options) -> str:
        out = StringIO()
        with redirect_stdout(out):
            call_command("get_llmclients", stdout=out, stderr=out, **options)
        return out.getvalue()

    def test_by_account_number(self):
        self.assertIn(self.llmclient.hostname, self.run_command(account_number=self.account.account_number))

    def test_by_company_name(self):
        self.assertIn(self.llmclient.hostname, self.run_command(company_name=self.account.company_name))

    def test_unknown_account(self):
        self.assertNotIn(self.llmclient.hostname, self.run_command(account_number="0000-0000-0000"))
        self.assertNotIn(self.llmclient.hostname, self.run_command(company_name="no such company"))

    def test_no_account(self):
        with self.assertRaises(SmarterValueError):
            self.run_command()
