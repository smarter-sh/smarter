"""
This module provides a Django management command to create or update a user for a given account.

It handles user creation, setting password, sending notification emails, creating UserProfile, and
updating or creating AccountContact as needed.

Classes
=======
Command
    Implements the logic for the ``manage.py create_user`` command.

Command-line Arguments
=======================
--account_number : str, required
    The Smarter account number the user should belong to.
--username : str, required
    The username for the new user.
--email : str, required
    The email address for the new user.
--first_name : str, required
    The first name of the new user.
--last_name : str, required
    The last name of the new user.
--password : str, optional
    The password for the new user. If not provided, a random password is generated.
--admin : bool (flag), optional
    Set to true to mark the new user as an admin.
--language : str, optional
    The user's preferred language, one of ``settings.LANGUAGES``, e.g. ``es``, which is stored as
    ``UserProfile.language``. The password email and the welcome email are written in it.
    Defaults to English for a new user, and leaves an existing user's preference unchanged.

Functionality
=============
- Creates or updates a ``User`` for the provided account.
- Validates the provided email address.
- Sets password (either provided or randomly generated for new users).
- Optionally emails credentials if the `ENABLE_NEW_USER_PASSWORD_EMAIL` Waffle switch is enabled.
- Creates or updates corresponding ``UserProfile`` and ``AccountContact`` records as needed.
- All creation is wrapped in an atomic transaction for integrity.

Usage Example
=============
    python manage.py create_user --account_number=<number> --username=<name> --email=<email> --first_name=<first> --last_name=<last> [--password=<pwd>] [--admin] [--language=<code>]
"""

import secrets
import string
from urllib.parse import urljoin

from django.conf import settings
from django.core.management.base import CommandError
from django.db import transaction
from django.utils import translation
from django.utils.translation import gettext as _

from smarter.apps.account.models import (
    Account,
    AccountContact,
    User,
    UserProfile,
    welcome_email_languages,
)
from smarter.apps.infrastructure.services import infrastructure
from smarter.common.conf import smarter_settings
from smarter.lib.django import waffle
from smarter.lib.django.management.base import SmarterCommand
from smarter.lib.django.validators import SmarterValidator


# pylint: disable=E1101
class Command(SmarterCommand):
    """Django manage.py create_user command.

    This command is used to create a new user for an account.
    """

    def create_user(
        self,
        account_number,
        username,
        email,
        first_name,
        last_name,
        password=None,
        is_admin=False,
        language=None,
        show_password=False,
    ) -> bool:
        """
        Create a new user for the specified account.

        If the user already exists,
        update the user's information. The basic workflow is as follows:

          1. Get the account based on the provided account number. If the account does
              not exist, log a failure and return False.
          2. Attempt to get or create the user based on the provided username. If there
              is an error during user creation, log a failure and return False.
          3. If the user already exists, log a notice that the existing user will be
              updated. Set the user's staff status based on the is_admin flag. Validate
              the provided email address and if it is invalid, log a failure and return
              False. Update the user's email, first name, last name, and active status.
              If a password is provided, set the user's password to the provided
              password. If no password is provided and the user was created, generate a
              random password and set it for the user. The generated password is printed
              only when show_password is True, because this command's output ends up in
              deployment job logs.
              Attempt to save the user and if there is an error during saving, log a
              failure and return False. Log a success message that the user has been
              created or updated.
          4. If the user was created and the Waffle switch
              ENABLE_NEW_USER_PASSWORD_EMAIL is active, attempt to send an email to the
              user with their account credentials. If there is an error during email
              sending, log a failure but do not return False since the user account has
              been created successfully.
          5. Attempt to get or create a UserProfile for the user and account. If there
              is an error during this process, log a failure and return False. The
              profile's language is set to the given language. A new UserProfile adds
              the user to the account's contacts, which sends the welcome email in its
              language. If the UserProfile was created, log a success message.
          6. Attempt to get an AccountContact for the account and email. If it exists,
              update the first name and last name and save it. If it does not exist,
              create a new AccountContact, which sends it the welcome email in the
              user's language. If there is an error during this process, log a failure
              and return False.
          7. If all steps are successful, log a success message that the create_user
              command completed successfully and return True.

        :param str account_number: The account number of the account to which the user belongs.
        :param str username: The username for the new user.
        :param str email: The email address for the new user.
        :param str first_name: The first name of the new user.
        :param str last_name: The last name of the new user.
        :param str password: The password for the new user. If not provided, a random password will be generated. Defaults to None.
        :param bool is_admin: Whether the new user should be an admin. Defaults to False.
        :param bool show_password: Whether to print a generated password. Defaults to False, because the
            command's output usually ends up in logs.
        :param str language: The user's preferred language, one of ``settings.LANGUAGES``, e.g. ``es``,
            in which the password and welcome emails are written. Defaults to None: English for a new
            user, and an existing user's preference is kept.
        :returns: True if the user was created or updated successfully.
        :rtype: bool
        :raises CommandError: if the account doesn't exist, the email address is invalid, or the user,
            its profile or its account contact can't be saved. The transaction is rolled back.
        """
        account: Account
        user: User
        created: bool

        try:
            account = Account.objects.get(account_number=account_number)
        except Account.DoesNotExist:
            raise CommandError(f"Account with account number {account_number} does not exist.")

        try:
            user, created = User.objects.get_or_create(username=username)
        # pylint: disable=broad-except
        except Exception as e:
            raise CommandError(f"Error creating user {username}: {str(e)}")

        if not created:
            self.stdout.write(self.style.NOTICE(f"User {username} already exists, updating the existing user."))
        if is_admin:
            user.is_staff = True
        else:
            user.is_staff = False

        if not SmarterValidator.is_valid_email(email):
            raise CommandError(f"Invalid email address: {email}")

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
            # the password is printed only on request: this command's output usually ends up in
            # deployment job logs.
            if show_password:
                self.stdout.write(self.style.SUCCESS(f"Password for user {username} has been set to {password}"))
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Generated a random password for user {username}. It is sent in the new user email, "
                        "when that is enabled. To see it, run this command with --show_password, or set "
                        f"another with: manage.py changepassword {username}"
                    )
                )
        try:
            user.save()
        # pylint: disable=broad-except
        except Exception as e:
            raise CommandError(f"Error saving user {username}: {str(e)}")

        self.stdout.write(f"User {username} {email} has been {'created' if created else 'updated'}.")

        if created and waffle.switch_is_active(waffle.SmarterWaffleSwitches.ENABLE_NEW_USER_PASSWORD_EMAIL):
            # Send email to user, in the language of the welcome email.
            login_url = urljoin(smarter_settings.environment_url, "login")
            with translation.override(language or settings.LANGUAGE_CODE):
                subject = _("Your Smarter user account has been created")
                # Translators: a plain-text email. Keep the line breaks, and the values after each colon.
                body = _(
                    "Your Smarter user account has been created. Do not share your account credentials with anyone.\n"
                    "\n"
                    "Url: %(login_url)s\n"
                    "Username: %(username)s\n"
                    "Email: %(email)s\n"
                    "Password: %(password)s\n"
                ) % {"login_url": login_url, "username": username, "email": email, "password": password}
            try:
                # the email has the user's password, so the admin gets no blind copy.
                infrastructure.email.send_email(
                    subject=subject,
                    to=email,
                    body=body,
                    html=False,
                    quiet=False,
                    bcc_admin=False,
                )
            # pylint: disable=broad-except
            except Exception as e:
                self.stderr.write(
                    self.style.WARNING(
                        f"Could not send the password email to user {username} at {email}: {e}. "
                        "The user account has been created, but the user may not have received their password."
                    )
                )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"Skipping sending password email to user {username} as the Waffle switch ENABLE_NEW_USER_PASSWORD_EMAIL is not active."
                )
            )

        try:
            # a new profile adds the user to the account's contacts, which sends the welcome email
            # in the profile's language.
            user_profile, created = UserProfile.objects.get_or_create(
                user=user, account=account, defaults={"language": language or settings.LANGUAGE_CODE}
            )
            if language and user_profile.language != language:
                user_profile.language = language
                user_profile.save()
        # pylint: disable=broad-except
        except Exception as e:
            raise CommandError(f"Error creating user profile for user {username}: {str(e)}")

        if created:
            self.stdout.write(
                f"User profile created for {user_profile.user.username} {user_profile.user.email}, account {user_profile.account.account_number} {user_profile.account.company_name}."
            )

        try:
            account_contact = AccountContact.objects.get(account=account, email=email)
            account_contact.first_name = first_name
            account_contact.last_name = last_name
            account_contact.save()
        except AccountContact.DoesNotExist:
            try:
                AccountContact(account=account, first_name=first_name, last_name=last_name, email=email).save(
                    language=language
                )
                self.stdout.write(
                    f"Account contact created for {first_name} {last_name}, account {account.account_number} {account.company_name}."
                )
            # pylint: disable=broad-except
            except Exception as e:
                raise CommandError(f"Error creating account contact for user {username}: {str(e)}")
        # pylint: disable=broad-except
        except Exception as e:
            raise CommandError(f"Error creating account contact for user {username}: {str(e)}")

        self.handle_completed_success()
        return True

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
        parser.add_argument(
            "--language",
            type=str,
            choices=welcome_email_languages(),
            help="The user's preferred language, for the password and welcome emails. Default: English",
        )
        parser.add_argument(
            "--show_password",
            action="store_true",
            default=False,
            help="Print the generated password of a new user. Off by default, since the output may be logged.",
        )

    def handle(self, *args, **options):
        """Create the user."""
        self.handle_begin()

        account_number = options["account_number"]
        username = options["username"]
        email = options["email"]
        first_name = options["first_name"]
        last_name = options["last_name"]
        password = options["password"]
        is_admin = options["admin"]
        language = options.get("language")
        show_password = options.get("show_password", False)
        retval = False

        with transaction.atomic():
            retval = self.create_user(
                account_number=account_number,
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                password=password,
                is_admin=is_admin,
                language=language,
                show_password=show_password,
            )

        if not retval:
            raise CommandError(f"Could not create the user {username}.")
