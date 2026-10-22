"""
Management command to initialize the Smarter platform or accounts.

This module defines the Django management command ``initialize_account`` for the Smarter platform.
It provides functionality to:

* Initialize the entire Smarter platform with minimal required resources.
* Initialize a single account, including:

  1. Creating an Account object.
  2. Creating, updating, or validating an admin user for the Account.
  3. Loading the example plugins and LLMClients from GitHub, and deploying the LLMClients.
  4. Loading the Stackademy project from GitHub, and deploying its LLMClients.

It also supports initializing all existing accounts to update their shared AI resources.

Command-line Arguments
-----------------------
* ``--account_number``: The account number that will own the remote API connection.
* ``--username``: Username for the admin account for this Account.
* ``--email``: Email address of the account admin user (fallback is ``<username>@<root_domain>``).
* ``--password``: Password for the account admin user (prompted if not supplied).
* ``--company_name``: Name of the company for the Account.
* ``--all``: If provided, initializes resources for all existing accounts.

Typical usage is for system administrators to initialize platform resources or bootstrap new accounts on the Smarter platform.
"""

from typing import Optional

from django.core.management import call_command
from django.core.management.base import CommandError

from smarter.apps.account.models import Account, User
from smarter.apps.account.utils import get_cached_smarter_admin_user_profile
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.llmclient.const import (
    EXAMPLE_MANIFESTS_REPOSITORY_URL,
    STACKADEMY_REPOSITORY_URL,
)
from smarter.common.conf import smarter_settings
from smarter.lib import logging
from smarter.lib.django.management.base import SmarterCommand
from smarter.lib.django.validators import SmarterValidator

logger = logging.getLogger(__name__)
logger_prefix = logging.formatted_text(__name__)

EXAMPLE_KINDS_PER_ACCOUNT = [
    SAMKinds.STATIC_PLUGIN.value,
    SAMKinds.SQL_PLUGIN.value,
    SAMKinds.API_PLUGIN.value,
    SAMKinds.SKILL_PLUGIN.value,
    SAMKinds.WEBSEARCH_PLUGIN.value,
    SAMKinds.IMAGE_SEARCH_PLUGIN.value,
    SAMKinds.LLM_CLIENT.value,
]
"""The kinds of the example manifests of which each account gets its own copy: the plugins, and the LLMClients that use them."""


class Command(SmarterCommand):
    """
    Django manage.py initialize_platform command.

    Initialize the Smarter
    platform. Creates the minimal resources necessary to start using Smarter.
    """

    def initialize_account(
        self, account_number: str, username: str, email: str, password: Optional[str], company_name: Optional[str]
    ) -> bool:
        """
        Initialize a single account with the provided information.

        Optionally
        creates or updates an account admin user with the provided username, email, and password.
        Creates a collection of shared AI resources that are owned by the account admin user.

        1. Create the Account.
        2. Create an admin user for the Account.
        3. Load the example plugins and LLMClients from GitHub, and deploy the LLMClients.
        4. Load the Stackademy project from GitHub, and deploy its LLMClients.

        .. note::

            The typical use case is to pass the Smarter admin username (and no password) such
            that the shared AI resources are owned by the Smarter admin user. This
            removes some of the AI resource dependencies on the account, such as
            Connections and Secrets for some of the shared AI resources.
        """
        msg = f"Initializing account {account_number} {company_name} with admin user {username}..."
        self.stdout.write(self.style.NOTICE(msg))
        logger.info(msg)

        # 1. Create the Account.
        call_command("create_account", account_number=account_number, company_name=company_name)

        # 2. Create an admin user for the Account.
        try:
            user = User.objects.get(username=username)

            if password:
                user.set_password(password)
                user.email = email
                user.is_superuser = True
                user.is_staff = True
                user.save()
                msg = f"Updated the existing User '{username}' for account {account_number}."
                self.stdout.write(self.style.NOTICE(msg))
                logger.info(msg)
            else:
                msg = f"User '{username}' already exists for account {account_number}. No password provided, so the existing password will be left unchanged."
                self.stdout.write(self.style.WARNING(msg))
                logger.warning(msg)

        except User.DoesNotExist:
            if not password:
                msg = f"There is no user {username}, and no password to create it with. Add --password."
                self.stdout.write(self.style.ERROR(msg))
                logger.error(msg)
                self.handle_completed_failure(msg=msg)
                return False
            call_command(
                "create_user",
                account_number=account_number,
                username=username,
                email=email,
                password=password,
                first_name="Account",
                last_name="Admin",
                admin=True,
            )
        # pylint: disable=broad-except
        except Exception as e:
            msg = f"Failed to create or update the admin user for account {account_number}: {str(e)}"
            self.stdout.write(self.style.ERROR(msg))
            logger.error(msg)
            self.handle_completed_failure(msg=msg)
            return False

        # 3. The account's own copies of the example plugins and LLMClients, deployed. The other examples,
        # e.g. the Guardrails, MCPClients and Proxies, belong to the Smarter admin, which initialize_platform
        # applies, and every account may use them.

        try:
            call_command(
                "load_from_github",
                url=EXAMPLE_MANIFESTS_REPOSITORY_URL,
                account_number=account_number,
                username=username,
                include_kind=EXAMPLE_KINDS_PER_ACCOUNT,
                skip_missing_references=True,
                deploy=True,
            )
        except (CommandError, SystemExit) as e:
            # one example that fails, e.g. for a Secret that this platform has not set, must not prevent
            # the rest of the account's initialization.
            logger.error(
                "%s.initialize_account() load_from_github %s failed for account %s: %s",
                logger_prefix,
                EXAMPLE_MANIFESTS_REPOSITORY_URL,
                account_number,
                e,
            )

        # 4. The account's own copy of the Stackademy project, deployed. Without its Budget, which only a
        # superuser may apply, and which initialize_platform applies once, to the Smarter account's
        # LLMClient: a Budget's resources are declarative, so applying it here would move it to this
        # account's. Its LLMClients are verified by initialize_platform, rather than with billable
        # prompts each time that an account is created.

        try:
            call_command(
                "load_from_github",
                url=STACKADEMY_REPOSITORY_URL,
                account_number=account_number,
                username=username,
                exclude_kind=[SAMKinds.BUDGET.value],
                deploy=True,
            )
        except (CommandError, SystemExit) as e:
            # a Stackademy resource that fails must not prevent the rest of the account's initialization.
            logger.error(
                "%s.initialize_account() load_from_github %s failed for account %s: %s",
                logger_prefix,
                STACKADEMY_REPOSITORY_URL,
                account_number,
                e,
            )

        logger.info("Account %s initialized successfully.", account_number)
        return True

    def initialize_all_accounts(self) -> bool:
        """
        Initialize all EXISTING accounts.

        This is useful for ensuring that all accounts
        have the the most recent versions of shared AI resources.
        """
        retval = True
        accounts = Account.objects.all()
        smarter_admin_user_profile = get_cached_smarter_admin_user_profile()
        for account in accounts:
            try:
                self.initialize_account(
                    account_number=account.account_number,
                    username=smarter_admin_user_profile.user.username,
                    email=f"{account.account_number}_admin@{smarter_settings.root_domain}",
                    password=None,
                    company_name=account.company_name,
                )
            # pylint: disable=broad-except
            except Exception as e:
                msg = f"Failed to initialize account {account.account_number}: {str(e)}"
                self.stdout.write(self.style.ERROR(msg))
                logger.error(msg)
                retval = False
                continue
        return retval

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument(
            "--account_number",
            type=str,
            help="The account number that will own the remote Api connection. Defaults to smarter_test_api",
        )
        parser.add_argument(
            "--username",
            type=str,
            help="The username for the admin account for this Account.",
        )
        parser.add_argument("--email", type=str, help="The email address of the user to associate with this Secret.")
        parser.add_argument(
            "--password", type=str, help="The value to encrypt and persist. If not provided, you will be prompted."
        )
        parser.add_argument(
            "--company_name",
            type=str,
            help="The company name for the Account.",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Initialize all accounts.",
        )

    def handle(self, *args, **options):
        """
        Initialize the Smarter platform.

        Creates the minimal resources necessary to start using Smarter.

        1. Create the Account.
        2. Create an admin user for the Account.
        3. Load the example plugins and LLMClients from GitHub, and deploy the LLMClients.
        4. Load the Stackademy project from GitHub, and deploy its LLMClients.
        """
        self.handle_begin()

        all_accounts = options.get("all")
        if all_accounts:
            if not self.initialize_all_accounts():
                raise CommandError("Some accounts could not be initialized. See the errors above.")
            self.handle_completed_success()
            return

        # ----------------------------------------------------------------------
        # we're only initializing a single account.
        # ----------------------------------------------------------------------

        account_number = options.get("account_number")
        if not account_number:
            msg = "account number is required."
            raise CommandError(msg)
        if not SmarterValidator.is_valid_account_number(account_number):
            msg = f"account number {account_number} is not valid."
            raise CommandError(msg)
        username = options.get("username")
        if not username:
            msg = "username is required."
            raise CommandError(msg)
        if not SmarterValidator.is_valid_username(username):
            msg = f"username {username} is not valid."
            raise CommandError(msg)
        email = options.get("email")
        if not email:
            email = f"{username}@{smarter_settings.root_domain}"
            msg = f"No email provided, using the default value: {email}"
            self.stdout.write(self.style.WARNING(msg))
            logger.warning(msg)
        if not SmarterValidator.is_valid_email(email):
            email = f"{username}@{smarter_settings.root_domain}"
            msg = f"No email provided, using the default value: {email}"
            self.stdout.write(self.style.WARNING(msg))
            logger.warning(msg)

        password = options.get("password")
        if not password:
            msg = "password is required."
            raise CommandError(msg)

        company_name = options.get("company_name")
        if not company_name:
            msg = "company name is required."
            raise CommandError(msg)

        self.initialize_account(
            account_number=account_number,
            username=username,
            email=email,
            password=password,
            company_name=company_name,
        )

        self.handle_completed_success()
