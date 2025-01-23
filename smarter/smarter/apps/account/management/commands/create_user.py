"""This module is used to manage the superuser account."""

import secrets
import string
from urllib.parse import urljoin

from django.core.management.base import BaseCommand

from smarter.apps.account.models import Account, AccountContact, UserProfile
from smarter.common.conf import settings as smarter_settings
from smarter.common.helpers.email_helpers import email_helper
from smarter.lib.django.user import User


# pylint: disable=E1101
class Command(BaseCommand):
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

    def change_password(self, username, new_password):
        """Change the password for a user."""
        try:
            user = User.objects.get(username=username)
            user.set_password(new_password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Password for user {username} has been changed to {new_password}."))
            return user
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"User {username} does not exist."))
        return None

    def handle(self, *args, **options):
        """create the superuser account."""
        account_number = options["account_number"]
        username = options["username"]
        email = options["email"]
        first_name = options["first_name"]
        last_name = options["last_name"]
        password = options["password"]
        is_admin = options["admin"]

        account = Account.objects.get(account_number=account_number)

        if not password:
            password_length = 16
            alphabet = string.ascii_letters + string.digits + string.punctuation
            password = "".join(secrets.choice(alphabet) for _ in range(password_length))

        if not User.objects.filter(username=username).exists():
            user = User.objects.create_user(username=username, email=email)
            if is_admin:
                user.is_staff = True
            user.is_active = True
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS("User" + f" {username} {email} has been created."))
            self.stdout.write(self.style.SUCCESS(f"Password: {password}"))

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

        else:
            if password:
                self.change_password(username, password)
                self.stdout.write(self.style.SUCCESS("Updated password."))

        user = User.objects.get(username=username)
        user_profile, created = UserProfile.objects.get_or_create(user=user, account=account)
        if created:
            self.stdout.write(
                self.style.SUCCESS(f"User profile created for {user_profile.user} {user_profile.account.company_name}.")
            )

        try:
            account_contact = AccountContact.objects.get(account=account, email=email)
            account_contact.first_name = first_name
            account_contact.last_name = last_name
            account_contact.save()
        except AccountContact.DoesNotExist:
            AccountContact.objects.create(account=account, first_name=first_name, last_name=last_name, email=email)
