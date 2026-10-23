"""
This module provides a Django management command to create or update a superuser ("Smarter admin") account, user profile, and a corresponding API key for the platform.

Classes
=======
Command
    Implements the logic for the ``manage.py create_smarter_admin`` command.

Command-line Arguments
=======================
-u, --username : str, optional
    The username for the new superuser (defaults to value from settings).
-e, --email : str, optional
    The email address for the new superuser (defaults to username@domain).
-p, --password : str, optional
    The password for the new superuser. If not specified, a random password is generated.

Functionality
=============
- Ensures there is a platform admin account in the system, fully populated.
- Creates or updates User and UserProfile for the superuser.
- Creates a default AccountContact if absent.
- Creates a new API key (auth token) for the superuser if one does not exist, and emails its value
  to the superuser's email address. The value is never printed or logged, and can't be recovered,
  so if the email can't be sent, create another key with ``manage.py create_api_key``.
- Most account and contact attributes are populated from configuration settings.

Usage Example
=============
    python manage.py create_smarter_admin --username=admin --email=admin@example.com --password=s3cret
"""

import secrets
import string
from urllib.parse import urljoin

from smarter.apps.account.models import Account, AccountContact, User, UserProfile
from smarter.apps.infrastructure.services import infrastructure
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

    def email_api_key(self, user: User, auth_token: SmarterAuthToken, token_key: str) -> bool:
        """
        Email a new api key's value to its owner.

        The value is shown only in this email: it is never printed or logged, and Smarter keeps only
        its hash. The platform's admin gets no blind copy, because the email carries a secret.

        :param user: the api key's owner, the recipient.
        :param auth_token: the new api key.
        :param token_key: the api key's value.
        :returns: True if the email was sent.
        """
        body = (
            "An API key has been created for your Smarter admin user. It is shown only in this email, and "
            "can't be recovered, so store it in a password manager or a secret store, and delete this email.\n"
            "\n"
            f"Url: {urljoin(smarter_settings.environment_url, 'login')}\n"
            f"Username: {user.username}\n"
            f"API key name: {auth_token.name}\n"
            f"API key id: {auth_token.key_id}\n"
            f"API key: {token_key}\n"
        )
        return infrastructure.email.send_email(
            subject="Your Smarter admin API key",
            to=user.email,
            body=body,
            html=False,
            bcc_admin=False,
        )

    def handle(self, *args, **options):
        """Create the superuser account."""
        self.handle_begin()

        username = options["username"] or SMARTER_ADMIN_USERNAME
        email = options["email"] or f"{username}@{smarter_settings.root_api_domain}"
        password = options["password"]

        account, created = Account.objects.get_or_create(
            account_number=SMARTER_ACCOUNT_NUMBER,
        )
        account.name = f"{smarter_settings.platform_name} Admin Account"
        account.description = f"automatically-generated {smarter_settings.platform_name} Admin account"
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
            self.stdout.write(f"Created account: {account.account_number} {account.company_name}")

        # Create the user as a superuser: the User post_save receiver looks up the admin user,
        # which must be a superuser, as soon as the row is inserted.
        user, created = User.objects.get_or_create(
            username=username, defaults={"is_superuser": True, "is_staff": True, "is_active": True}
        )
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

            self.stdout.write(f"Created superuser {username} {email}.")
        else:
            self.stdout.write(f"User {username} updated.")
        user_profile, created = UserProfile.objects.get_or_create(user=user, account=account)
        if created:
            self.stdout.write(
                f"Created user profile for {user_profile.user.username} {user_profile.user.email}, account {user_profile.account}"
            )
        else:
            self.stdout.write(f"User profile already exists for {user_profile.user}, account {user_profile.account}")
        UserProfile.get_cached_object(invalidate=True, pk=user_profile.pk)  # prime the cache

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
            self.stdout.write(
                f"Created account contact for {account_contact.first_name} {account_contact.last_name}, account {account_contact.account.account_number} {account_contact.account.company_name}"
            )

        # ensure that the Smarter admin user has at least one auth token (api key)
        # not cached: a cached result from before this command created a key would still be empty.
        if not SmarterAuthToken.objects.filter(user=user).exists():
            auth_token, token_key = SmarterAuthToken.objects.create(
                user_profile=user_profile, name="smarter_admin_key", user=user, description="created by manage.py"
            )  # type: ignore[assignment]
            if self.email_api_key(user=user, auth_token=auth_token, token_key=token_key):
                self.stdout.write(f"Created API key {auth_token.name}, and emailed it to {user.email}.")
            else:
                self.stderr.write(
                    self.style.WARNING(
                        f"Created API key {auth_token.name}, but could not email it to {user.email}. Its value can't "
                        f"be recovered. Once email works, run: manage.py create_api_key --username {user.username}"
                    )
                )
        self.handle_completed_success()
