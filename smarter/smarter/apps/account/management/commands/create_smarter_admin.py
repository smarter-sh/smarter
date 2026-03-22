"""This module is used to create a superuser account."""

import secrets
import string

from smarter.apps.account.models import Account, AccountContact, User, UserProfile
from smarter.common.conf import smarter_settings
from smarter.common.const import (
    SMARTER_ACCOUNT_NUMBER,
    SMARTER_ADMIN_USERNAME,
    SMARTER_CUSTOMER_SUPPORT_EMAIL,
    SMARTER_CUSTOMER_SUPPORT_PHONE,
)
from smarter.lib.django.management.base import SmarterCommand
from smarter.lib.drf.models import SmarterAuthToken


# pylint: disable=E1101
class Command(SmarterCommand):
    """Create a new Smarter superuser."""

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("-u", "--username", type=str, help="The username for the new superuser")
        parser.add_argument("-e", "--email", type=str, help="The email address for the new superuser")
        parser.add_argument("-p", "--password", type=str, help="The password for the new superuser")

    def handle(self, *args, **options):
        """create the superuser account."""
        self.handle_begin()

        username = options["username"] or SMARTER_ADMIN_USERNAME
        email = options["email"] or f"{username}@{smarter_settings.root_api_domain}"
        password = options["password"]

        account, created = Account.objects.get_or_create(
            account_number=SMARTER_ACCOUNT_NUMBER,
        )
        account.company_name = smarter_settings.branding_corporate_name
        account.is_default_account = True
        account.phone_number = smarter_settings.branding_support_phone_number
        account.address1 = smarter_settings.branding_address1
        account.address2 = smarter_settings.branding_address2
        account.city = smarter_settings.branding_city
        account.state = smarter_settings.branding_state
        account.postal_code = smarter_settings.branding_postal_code
        account.country = smarter_settings.branding_country
        account.timezone = smarter_settings.branding_timezone
        account.currency = smarter_settings.branding_currency
        account.save()

        if created:
            self.handle_completed_success(msg=f"Created account: {account.account_number} {account.company_name}")

        user, created = User.objects.get_or_create(username=username)
        user.email = email
        user.is_superuser = True
        user.is_staff = True
        user.is_active = True
        user.save()
        if created:
            if not password:
                password_length = 16
                alphabet = string.ascii_letters + string.digits + string.punctuation
                password = "".join(secrets.choice(alphabet) for _ in range(password_length))

            user.set_password(password)
            user.save()

            self.handle_completed_success(msg=f"Created superuser {username} {email} has been created.")
        else:
            self.handle_completed_success(msg=f"User {username} updated.")
        user_profile, created = UserProfile.objects.get_or_create(user=user, account=account)
        if created:
            self.handle_completed_success(
                msg=f"Created user profile for {user_profile.user.username} {user_profile.user.email}, account {user_profile.account.account_number} {user_profile.account.company_name}"
            )

        account_contact, created = AccountContact.objects.get_or_create(
            account=account,
            is_primary=True,
        )
        if created:
            account_contact.first_name = "Smarter"
            account_contact.last_name = "Admin"
            account_contact.email = SMARTER_CUSTOMER_SUPPORT_EMAIL
            account_contact.phone = SMARTER_CUSTOMER_SUPPORT_PHONE
            account_contact.save()
            self.handle_completed_success(
                msg=f"Created account contact for {account_contact.first_name} {account_contact.last_name}, account {account_contact.account.account_number} {account_contact.account.company_name}"
            )

        # ensure that the Smarter admin user has at least one auth token (api key)
        smarterauthtoken = SmarterAuthToken.get_cached_objects(user=user)
        if not smarterauthtoken.exists():
            _, token_key = SmarterAuthToken.objects.create(
                user_profile=user_profile, name="smarter-admin-key", user=user, description="created by manage.py"
            )  # type: ignore[assignment]
            self.handle_completed_success(msg=f"created API key: {token_key}")
            return
        self.handle_completed_success()
