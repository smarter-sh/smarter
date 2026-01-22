# pylint: disable=wrong-import-position
"""Test Account."""

# our stuff
import logging

from smarter.apps.account.models import Account, User, UserProfile
from smarter.common.helpers.console_helpers import formatted_text
from smarter.common.utils import hash_factory
from smarter.lib.unittest.base_classes import SmarterTestBase

logger = logging.getLogger(__name__)


class TestAccount(SmarterTestBase):
    """Test Account model"""

    test_account_logger_prefix = formatted_text(f"{__name__}.TestAccount()")

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        super().setUpClass()
        logger.debug("%s.setUpClass()", cls.test_account_logger_prefix)
        hashed_slug = hash_factory()
        username = cls.name
        email = f"test-{hashed_slug}@mail.com"
        first_name = f"TestAdminFirstName_{hashed_slug}"
        last_name = f"TestAdminLastName_{hashed_slug}"
        cls.user = User.objects.create_user(
            email=email, first_name=first_name, last_name=last_name, username=username, password="12345"
        )
        cls.company_name = "Test Company"

    @classmethod
    def tearDownClass(cls):
        """Clean up test fixtures."""
        logger.debug("%s.tearDownClass()", cls.test_account_logger_prefix)
        cls.user.delete()
        super().tearDownClass()

    def test_create(self):
        """Test that we can create an account."""
        account = Account.objects.create(
            name=self.hash_suffix + self.company_name.lower().replace(" ", "_").replace("-", "_")
            or "default_account_name",
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
            name=self.hash_suffix + self.company_name.lower().replace(" ", "_").replace("-", "_")
            or "default_account_name",
            company_name=self.company_name,
            phone_number="1234567890",
            address1="123 Test St",
            address2="Apt 1",
            city="Test City",
            state="TX",
            postal_code="12345",
        )

        account_to_update = Account.objects.get(id=account.id)  # type: ignore[assignment]
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
            name=self.hash_suffix + self.company_name.lower().replace(" ", "_").replace("-", "_")
            or "default_account_name",
            company_name=self.company_name,
            phone_number="1234567890",
            address1="123 Test St",
            address2="Apt 1",
            city="Test City",
            state="TX",
            postal_code="12345",
        )

        profile = UserProfile.objects.create(
            name=self.user.username,
            user=self.user,
            account=account,
            is_test=True,
        )

        self.assertEqual(profile.account, account)
        self.assertEqual(profile.user, self.user)

        profile.delete()
        account.delete()
