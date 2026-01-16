"""Django manage.py initialize_platform command."""

from django.core.cache import cache
from django.core.management import call_command

from smarter.common.conf import smarter_settings
from smarter.lib.django.management.base import SmarterCommand
from smarter.lib.django.validators import SmarterValidator


class Command(SmarterCommand):
    """
    Django manage.py initialize_platform command. Initialize the Smarter
    platform. Creates the minimal resources necessary to start using Smarter.

    1. Create the Account.
    2. Create an admin user for the Account.
    3. Apply example manifests from GitHub.
    4. Add plugin examples.
    5. Deploy builtin example chatbots.
    6. Create StackAcademy AI resources.
    """

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

        cache.clear()
        self.stdout.write(self.style.NOTICE("Cleared the Django cache."))

        account_number = options.get("account_number")
        if not account_number:
            self.stdout.write(self.style.ERROR("account number is required."))
            self.handle_completed_failure(msg="account number is required.")
            return
        if not SmarterValidator.is_valid_account_number(account_number):
            self.stdout.write(self.style.ERROR(f"account number {account_number} is not valid."))
            self.handle_completed_failure(msg=f"account number {account_number} is not valid.")
            return
        username = options.get("username")
        if not username:
            self.stdout.write(self.style.ERROR("username is required."))
            self.handle_completed_failure(msg="username is required.")
            return
        if not SmarterValidator.is_valid_username(username):
            self.stdout.write(self.style.ERROR(f"username {username} is not valid."))
            self.handle_completed_failure(msg=f"username {username} is not valid.")
            return

        email = options.get("email")
        if not email:
            email = f"{username}@{smarter_settings.root_domain}"
            self.stdout.write(self.style.WARNING(f"No email provided, using the default value: {email}"))
        if not SmarterValidator.is_valid_email(email):
            self.stdout.write(self.style.ERROR(f"email {email} is not valid."))
            self.handle_completed_failure(msg=f"email {email} is not valid.")
            return

        password = options.get("password")

        company_name = options.get("company_name")
        if not company_name:
            self.stdout.write(self.style.ERROR("company name is required."))
            self.handle_completed_failure(msg="company name is required.")
            return

        # 1. Create the Account.
        call_command("create_account", account_number=account_number, company_name=company_name)

        # 2. Create an admin user for the Account.
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

        self.handle_completed_success()
