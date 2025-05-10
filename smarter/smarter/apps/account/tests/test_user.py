# pylint: disable=wrong-import-position
"""Test User."""

# our stuff
from smarter.apps.account.tests.mixins import TestAccountMixin

from ..models import Account, UserProfile


class TestAccount(TestAccountMixin):
    """Test Account model"""

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

        profile = UserProfile.objects.create(
            user=self.non_admin_user,
            account=account,
            is_test=True,
        )

        self.assertEqual(profile.account, account)
        self.assertEqual(profile.user, self.non_admin_user)

        profile.delete()
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
