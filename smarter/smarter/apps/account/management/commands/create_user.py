"""This module is used to manage the superuser account."""

import secrets
import string
from urllib.parse import urljoin

from smarter.apps.account.models import Account, AccountContact, User, UserProfile
from smarter.common.conf import smarter_settings
from smarter.common.helpers.email_helpers import email_helper
from smarter.lib.django.management.base import SmarterCommand


# pylint: disable=E1101
class Command(SmarterCommand):
    """Django manage.py create_user command. This command is used to create a new user for an account."""

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument(
            "--account_number", type=str, required=True, help="The Smarter account number to which the user belongs"
        )
        parser.add_argument("--username", type=str, required=True, help="The username for the new user")
        parser.add_argument("--email", type=str, required=True, help="The email address for the new user")
        parser.add_argument("--first_name", type=str, required=True, help="The first name of the new user")
        parser.add_argument("--last_name", type=str, required=True, help="The last name of the new user")
        parser.add_argument("--password", type=str, help="The password for the new user")
        parser.add_argument(
            "--admin", action="store_true", default=False, help="True if the new user is an admin, False otherwise."
        )

    def handle(self, *args, **options):
        """create the superuser account."""
        self.handle_begin()

        account_number = options["account_number"]
        username = options["username"]
        email = options["email"]
        first_name = options["first_name"]
        last_name = options["last_name"]
        password = options["password"]
        is_admin = options["admin"]

        account = Account.objects.get(account_number=account_number)

        user, created = User.objects.get_or_create(username=username)
        if not created:
            self.stdout.write(self.style.NOTICE(f"User {username} already exists, updating the existing user."))
        if is_admin:
            user.is_staff = True
        user.email = email
        user.first_name = first_name
        user.last_name = last_name
        user.is_active = True
        if password:
            user.set_password(password)
        elif created:
            # Generate a random password
            alphabet = string.ascii_letters + string.digits + string.punctuation
            generated_password = "".join(secrets.choice(alphabet) for _ in range(12))
            user.set_password(generated_password)
            password = generated_password  # Set password to generated password for email
            self.stdout.write(self.style.SUCCESS(f"Password for user {username} has been set to {password}."))
        user.save()
        self.handle_completed_success(msg=f"User {username} {email} has been created.")

        if created:
            # Send email to user
            login_url = urljoin(smarter_settings.environment_url, "login")
            body = f"""Your Smarter user account has been created. Do not share your account credentials with anyone.

            Url: {login_url}
            Username: {username}
            Email: {email}
            Password: {password}
            """
            email_helper.send_email(
                subject="Your Smarter user account has been created", to=email, body=body, html=False, quiet=False
            )

        user_profile, created = UserProfile.objects.get_or_create(user=user, account=account)
        if created:
            self.handle_completed_success(
                msg=f"User profile created for {user_profile.user} {user_profile.account.company_name}."
            )

        try:
            account_contact = AccountContact.objects.get(account=account, email=email)
            account_contact.first_name = first_name
            account_contact.last_name = last_name
            account_contact.save()
            self.handle_completed_success(msg="smarter.apps.account.management.commands.create_user completed.")
        except AccountContact.DoesNotExist:
            AccountContact.objects.create(account=account, first_name=first_name, last_name=last_name, email=email)
            self.handle_completed_success(
                msg=f"Account contact created for {first_name} {last_name}, account {account.account_number} {account.company_name}."
            )
