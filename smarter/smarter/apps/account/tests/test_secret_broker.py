# pylint: disable=wrong-import-position
"""Test Secret."""

import hashlib
import random
import unittest

from smarter.apps.account.models import Account, UserProfile
from smarter.common.conf import settings as smarter_settings
from smarter.common.exceptions import SmarterConfigurationError, SmarterValueError
from smarter.lib.django.user import User


class TestSmarterSecretBroker(unittest.TestCase):
    """Test Secret."""

    def setUp(self):
        self.hash_suffix = "_" + hashlib.sha256(str(random.getrandbits(256)).encode("utf-8")).hexdigest()

        self.account = Account.objects.create(
            company_name="TestCompany" + self.hash_suffix,
            phone_number="1234567890",
            address1="123 Test St",
            address2="Apt 1",
            city="Test City",
            state="TX",
            postal_code="12345",
        )
        non_admin_username = "non_admin_testuser" + self.hash_suffix
        self.non_admin_user = User.objects.create_user(username=non_admin_username, password="12345")
        self.non_admin_user_profile = UserProfile.objects.create(user=self.non_admin_user, account=self.account)

        admin_username = "admin_testuser" + self.hash_suffix
        self.admin_user = User.objects.create_user(
            username=admin_username, password="12345", is_staff=True, is_superuser=True
        )
        self.user_profile = UserProfile.objects.create(user=self.admin_user, account=self.account)

    def tearDown(self):
        try:
            self.non_admin_user_profile.delete()
        except UserProfile.DoesNotExist:
            pass
        try:
            self.non_admin_user.delete()
        except User.DoesNotExist:
            pass
        try:
            self.admin_user.delete()
        except User.DoesNotExist:
            pass
        try:
            self.account.delete()
        except Account.DoesNotExist:
            pass

    def test_create_secret(self):
        pass
