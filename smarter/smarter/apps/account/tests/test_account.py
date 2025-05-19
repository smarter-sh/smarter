# pylint: disable=wrong-import-position
"""Test Account."""

import hashlib
import random

# our stuff
from smarter.lib.django.user import User
from smarter.lib.unittest.base_classes import SmarterTestBase

from ..models import Account, UserProfile


class TestAccount(SmarterTestBase):
    """Test Account model"""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        hashed_slug = hashlib.sha256(str(random.getrandbits(256)).encode("utf-8")).hexdigest()[:16]
        username = self.name
        email = f"test-{hashed_slug}@mail.com"
        first_name = f"TestAdminFirstName_{hashed_slug}"
        last_name = f"TestAdminLastName_{hashed_slug}"
        self.user = User.objects.create_user(
            email=email, first_name=first_name, last_name=last_name, username=username, password="12345"
        )
        self.company_name = "Test Company"

    def tearDown(self):
        """Clean up test fixtures."""
        self.user.delete()
        Account.objects.filter(company_name=self.company_name).delete()
        super().tearDown()

    def test_create(self):
        """Test that we can create an account."""
        account = Account.objects.create(
            company_name=self.company_name,
            phone_number="1234567890",
            address1="123 Test St",
            address2="Apt 1",
            city="Test City",
            state="TX",
            postal_code="12345",
        )

        account.delete()

    def test_update(self):
        """Test that we can update an account."""
        account = Account.objects.create(
            company_name=self.company_name,
            phone_number="1234567890",
            address1="123 Test St",
            address2="Apt 1",
            city="Test City",
            state="TX",
            postal_code="12345",
        )

        account_to_update = Account.objects.get(id=account.id)
        account_to_update.company_name = "New Company"
        account_to_update.save()

        self.assertEqual(account_to_update.company_name, "New Company")
        self.assertEqual(account_to_update.phone_number, "1234567890")
        self.assertEqual(account_to_update.address1, "123 Test St")
        self.assertEqual(account_to_update.account_number, account.account_number)

        account.delete()

    def test_account_with_profile(self):
        """Test that we can create an account and associate a user_profile."""
        account = Account.objects.create(
            company_name=self.company_name,
            phone_number="1234567890",
            address1="123 Test St",
            address2="Apt 1",
            city="Test City",
            state="TX",
            postal_code="12345",
        )

        profile = UserProfile.objects.create(
            user=self.user,
            account=account,
            is_test=True,
        )

        self.assertEqual(profile.account, account)
        self.assertEqual(profile.user, self.user)

        profile.delete()
        account.delete()
