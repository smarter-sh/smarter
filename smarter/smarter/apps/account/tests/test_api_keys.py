# pylint: disable=wrong-import-position
"""Test SmarterAuthToken."""

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.common.exceptions import SmarterBusinessRuleViolation
from smarter.lib.drf.models import SmarterAuthToken


class TestSmarterAuthToken(TestAccountMixin):
    """Test SmarterAuthToken."""

    def test_create_auth_token(self):
        """Test create auth token."""

        token_record, token_key = SmarterAuthToken.objects.create(
            user=self.admin_user,
            name="testToken" + self.hash_suffix,
            description="testToken" + self.hash_suffix,
        )

        # validate that token_key is not None
        self.assertIsNotNone(token_key)
        token_record.delete()

    def test_create_auth_token_non_admin_user(self):
        """Test create auth token."""

        with self.assertRaises(SmarterBusinessRuleViolation):
            SmarterAuthToken.objects.create(
                name="testToken",
                user=self.non_admin_user,
                description="testToken" + self.hash_suffix,
            )
