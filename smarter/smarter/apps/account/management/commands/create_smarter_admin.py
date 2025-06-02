"""This module is used to create a superuser account."""

import secrets
import string

from django.core.management.base import BaseCommand

from smarter.apps.account.models import Account, AccountContact, UserProfile
from smarter.common.const import (
    SMARTER_ACCOUNT_NUMBER,
    SMARTER_COMPANY_NAME,
    SMARTER_CUSTOMER_SUPPORT_EMAIL,
    SMARTER_CUSTOMER_SUPPORT_PHONE,
)
from smarter.lib.django.user import User
from smarter.lib.drf.models import SmarterAuthToken


# pylint: disable=E1101
class Command(BaseCommand):
    """Create a new Smarter superuser."""

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("-u", "--username", type=str, help="The username for the new superuser")
        parser.add_argument("-e", "--email", type=str, help="The email address for the new superuser")
        parser.add_argument("-p", "--password", type=str, help="The password for the new superuser")

    def handle(self, *args, **options):
        """create the superuser account."""
        username = options["username"]
        email = options["email"]
        password = options["password"]

        account, created = Account.objects.get_or_create(
            account_number=SMARTER_ACCOUNT_NUMBER,
            company_name=SMARTER_COMPANY_NAME,
        )
        account.is_default_account = True
        account.phone_number = "+1 (512) 833-6955"
        account.address1 = "1700 South Lamar Blvd"
        account.address2 = "Suite 338"
        account.city = "Austin"
        account.state = "TX"
        account.postal_code = "78704"
        account.country = "USA"
        account.timezone = "America/Chicago"
        account.currency = "USD"
        account.save()

        if created:
            self.stdout.write(self.style.SUCCESS(f"Created account: {account.account_number} {account.company_name}"))

        user, created = User.objects.get_or_create(
            username=username, email=email, is_superuser=True, is_staff=True, is_active=True
        )
        if created:
            if not password:
                password_length = 16
                alphabet = string.ascii_letters + string.digits + string.punctuation
                password = "".join(secrets.choice(alphabet) for _ in range(password_length))

            user.set_password(password)
            user.save()

            self.stdout.write(self.style.SUCCESS(f"Created superuser {username} {email} has been created."))
            self.stdout.write(self.style.SUCCESS(f"Password: {password}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"User {username} updated."))

        user_profile, created = UserProfile.objects.get_or_create(user=user, account=account)
        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created user profile for {user_profile.user.username} {user_profile.user.email}, account {user_profile.account.account_number} {user_profile.account.company_name}"
                )
            )

        account_contact: AccountContact = None
        try:
            account_contact = AccountContact.objects.get(
                account=account,
                is_primary=True,
            )
        except AccountContact.DoesNotExist:
            account_contact = AccountContact(
                account=account,
                first_name="Smarter",
                last_name="Admin",
                email=SMARTER_CUSTOMER_SUPPORT_EMAIL,
                phone=SMARTER_CUSTOMER_SUPPORT_PHONE,
                is_primary=True,
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created account contact for {account_contact.first_name} {account_contact.last_name}, account {account_contact.account.account_number} {account_contact.account.company_name}"
                )
            )

        # ensure that the Smarter admin user has at least one auth token (api key)
        if not SmarterAuthToken.objects.filter(user=user).exists():
            _, token_key = SmarterAuthToken.objects.create(
                name="smarter-admin-key", user=user, description="created by manage.py"
            )
            self.stdout.write(self.style.SUCCESS(f"created API key: {token_key}"))
