# pylint: disable=wrong-import-position
"""Test SmarterAuthToken."""

import hashlib
import random
import unittest

from smarter.apps.account.models import Account, SmarterAuthToken
from smarter.common.exceptions import SmarterBusinessRuleViolation
from smarter.lib.django.user import User


class TestSmarterAuthToken(unittest.TestCase):
    """Test SmarterAuthToken."""

    def setUp(self):
        self.hash_suffix = "_" + hashlib.sha256(str(random.getrandbits(256)).encode("utf-8")).hexdigest()

        non_admin_username = "non_admin_testuser" + self.hash_suffix
        self.non_admin_user = User.objects.create_user(username=non_admin_username, password="12345")

        admin_username = "admin_testuser" + self.hash_suffix
        self.admin_user = User.objects.create_user(
            username=admin_username, password="12345", is_staff=True, is_superuser=True
        )

        self.account = Account.objects.create(
            company_name="TestCompany" + self.hash_suffix,
            phone_number="1234567890",
            address1="123 Test St",
            address2="Apt 1",
            city="Test City",
            state="TX",
            postal_code="12345",
        )

    def tearDown(self):
        try:
            self.user.delete()
        except User.DoesNotExist:
            pass
        try:
            self.account.delete()
        except Account.DoesNotExist:
            pass
        try:
            self.token_record.delete()
        except SmarterAuthToken.DoesNotExist:
            pass

    def test_create_auth_token(self):
        """Test create auth token."""

        token_record, token_key = SmarterAuthToken.objects.create(
            account=self.account,
            user=self.admin_user,
            description="testToken" + self.hash_suffix,
        )

        # validate that token_key is not None
        self.assertIsNotNone(token_key)
        token_record.delete()

    def test_create_auth_token_non_admin_user(self):
        """Test create auth token."""

        with self.assertRaises(SmarterBusinessRuleViolation):
            SmarterAuthToken.objects.create(
                account=self.account,
                user=self.admin_user,
                description="testToken" + self.hash_suffix,
            )
