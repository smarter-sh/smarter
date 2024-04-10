# -*- coding: utf-8 -*-
# pylint: disable=wrong-import-position
"""Test Account."""

# python stuff
import os
import unittest

from django.contrib.auth import get_user_model

# our stuff
from ..models import Account, UserProfile


User = get_user_model()


class TestAccount(unittest.TestCase):
    """Test Account model"""

    def setUp(self):
        """Set up test fixtures."""
        username = "testuser_" + os.urandom(4).hex()
        self.user = User.objects.create(username=username, password="12345")

    def tearDown(self):
        """Clean up test fixtures."""
        self.user.delete()

    def test_create(self):
        """Test that we can create an account."""
        account = Account.objects.create(
            company_name="Test Company",
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
            company_name="Test Company",
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
            company_name="Test Company",
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
