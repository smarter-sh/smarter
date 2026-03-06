"""Django manage.py initialize_account command."""

import logging
from typing import Optional

from django.core.management import call_command

from smarter.apps.account.models import Account, User
from smarter.apps.account.utils import get_cached_smarter_admin_user_profile
from smarter.common.conf import smarter_settings
from smarter.lib.django.management.base import SmarterCommand
from smarter.lib.django.validators import SmarterValidator

logger = logging.getLogger(__name__)


class Command(SmarterCommand):
    """
    Django manage.py initialize_platform command. Initialize the Smarter
    platform. Creates the minimal resources necessary to start using Smarter.

    """

    def initialize_account(
        self, account_number: str, username: str, email: str, password: Optional[str], company_name: str
    ) -> bool:
        """
        Initialize a single account with the provided information. Optionally
        creates or updates an account admin user with the provided username, email, and password.
        Creates a collection of shared AI resources that are owned by the account admin user.

        1. Create the Account.
        2. Create an admin user for the Account.
        3. Apply example manifests from GitHub.
        4. Add plugin examples.
        5. Deploy builtin example chatbots.
        6. Create StackAcademy AI resources.

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
                msg = (
                    "No password was provided. Using a random value. You will need to reset the password for this user."
                )
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

        # 3. Apply example manifests from GitHub.

        call_command(
            "load_from_github", account_number=account_number, url="https://github.com/QueriumCorp/smarter-demo"
        )
        call_command(
            "load_from_github",
            account_number=account_number,
            url="https://github.com/smarter-sh/examples",
            repo_version=2,
        )

        # 4. Add builtin plugin examples and deploy chatbots.

        call_command("add_plugin_examples", username=username)
        call_command("deploy_example_chatbot", account_number=account_number)
        call_command("deploy_builtin_chatbots", account_number=account_number)

        # 5. Setup Stackademy AI resources, used for training and testing.

        call_command("create_stackademy", account_number=account_number)

        logger.info("Account %s initialized successfully.", account_number)
        return True

    def initialize_all_accounts(self) -> bool:
        """
        Initialize all EXISTING accounts. This is useful for ensuring that all accounts
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
        Initialize the Smarter platform. Creates the minimal resources necessary to start using Smarter.

        1. Create the Account.
        2. Create an admin user for the Account.
        3. Apply example manifests from GitHub.
        4. Add plugin examples.
        5. Deploy builtin example chatbots.
        6. Create StackAcademy AI resources.
        """
        self.handle_begin()

        all_accounts = options.get("all")
        if all_accounts:
            if self.initialize_all_accounts():
                self.handle_completed_success()
            else:
                self.handle_completed_failure(msg="Failed to initialize all accounts.")
            return

        # ----------------------------------------------------------------------
        # we're only initializing a single account.
        # ----------------------------------------------------------------------

        account_number = options.get("account_number")
        if not account_number:
            msg = "account number is required."
            self.stdout.write(self.style.ERROR(msg))
            logger.error(msg)
            self.handle_completed_failure(msg=msg)
            return
        if not SmarterValidator.is_valid_account_number(account_number):
            msg = f"account number {account_number} is not valid."
            self.stdout.write(self.style.ERROR(msg))
            logger.error(msg)
            self.handle_completed_failure(msg=msg)
            return
        username = options.get("username")
        if not username:
            msg = "username is required."
            self.stdout.write(self.style.ERROR(msg))
            logger.error(msg)
            self.handle_completed_failure(msg=msg)
            return
        if not SmarterValidator.is_valid_username(username):
            msg = f"username {username} is not valid."
            self.stdout.write(self.style.ERROR(msg))
            logger.error(msg)
            self.handle_completed_failure(msg=msg)
            return
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
            self.stdout.write(self.style.ERROR(msg))
            logger.error(msg)
            self.handle_completed_failure(msg=msg)
            return

        company_name = options.get("company_name")
        if not company_name:
            msg = "company name is required."
            self.stdout.write(self.style.ERROR(msg))
            logger.error(msg)
            self.handle_completed_failure(msg=msg)
            return

        self.initialize_account(
            account_number=account_number,
            username=username,
            email=email,
            password=password,
            company_name=company_name,
        )

        self.handle_completed_success()
