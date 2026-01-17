"""Django manage.py initialize_platform command."""

from django.core.management import call_command

from smarter.common.conf import smarter_settings
from smarter.common.const import (
    SMARTER_ACCOUNT_NUMBER,
    SMARTER_BETA_ACCOUNT_NUMBER,
    SMARTER_UBC_ACCOUNT_NUMBER,
    SmarterEnvironments,
)
from smarter.lib.cache import lazy_cache
from smarter.lib.django.management.base import SmarterCommand


class Command(SmarterCommand):
    """Django manage.py initialize_platform command."""

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument(
            "--username",
            type=str,
            help="The username for the superuser associated with this platform. If not provided, the default 'admin' will be used.",
        )
        parser.add_argument(
            "--email",
            type=str,
            help="The email address of the user to associate with this Secret. If not provided, a default email will be assigned.",
        )
        parser.add_argument(
            "--password",
            type=str,
            help="The value to encrypt and persist. If not provided and you are running locally, the default 'smarter' will be used.",
        )

    def handle(self, *args, **options):
        """
        Initialize the Smarter platform. Creates the minimal resources necessary to start using Smarter.

        1. Create an admin user with the provided username, email, and password.
        2. Create example accounts and users.
        3. Initialize Waffle and Wagtail.
        4. Verify DNS configuration.
        5. Load example projects from GitHub.
        6. Add plugin examples.
        7. Deploy example chatbots.
        8. Initialize providers.
        9. Create StackAcademy SQL and API chatbots.
        10. Apply manifests and update secrets for database connections.
        """
        self.handle_begin()

        username = options.get("username")
        if not username:
            username = "admin"
            self.stdout.write(self.style.WARNING(f"No username provided, using the default value: {username}"))

        email = options.get("email")
        if not email:
            email = f"{username}@{smarter_settings.root_domain}"
            self.stdout.write(
                self.style.WARNING(f"No email provided, assigning a default email for this Secret: {email}")
            )

        password = options.get("password")
        if not password:
            if smarter_settings.environment == SmarterEnvironments.LOCAL:
                password = "smarter"
                self.stdout.write(self.style.WARNING(f"No password provided, using the default value: {password}"))
            else:
                self.stdout.write(
                    self.style.ERROR("An administrator password is required when not running in LOCAL environment.")
                )
                return

        # create Smarter Account and admin User.
        # ---------------------------------------------------------------------
        call_command("create_smarter_admin", username=username, password=password, email=email)

        # Initialize Smarter platform components.
        # ---------------------------------------------------------------------
        call_command("initialize_waffle")  # Initialize builtin Waffle switches for feature flagging
        call_command("initialize_wagtail")  # Initialize prebuilt Wagtail static page content for Docs area
        call_command("initialize_providers")  # Initialize builtin LLM providers: openai, metaai, googleia
        call_command(
            "verify_dns_configuration"
        )  # if AWS is configured then Verify Route53 Hosted Zones and DNS records

        # Initialize Accounts. Creates a collection of example AI resources
        # for the Account.
        # ---------------------------------------------------------------------
        call_command(
            "initialize_account",
            account_number=SMARTER_ACCOUNT_NUMBER,
            username="admin",
            company_name="The Smarter Project",
        )
        if smarter_settings.configure_beta_account:
            call_command(
                "initialize_account",
                account_number=SMARTER_BETA_ACCOUNT_NUMBER,
                username="admin_beta",
                company_name="Smarter Beta Users",
            )
        if smarter_settings.configure_ubc_account:
            call_command(
                "initialize_account",
                account_number=SMARTER_UBC_ACCOUNT_NUMBER,
                username="admin_ubc",
                company_name="University of British Columbia",
            )

        # Create a Smarter staff and customer user for testing purposes.
        call_command(
            "create_user",
            account_number=SMARTER_ACCOUNT_NUMBER,
            username="staff_user",
            email=f"staff@{smarter_settings.root_domain}",
            password=password,
            first_name="Staff",
            last_name="User",
            admin=True,
        )
        call_command(
            "create_user",
            account_number=SMARTER_ACCOUNT_NUMBER,
            username="customer_user",
            email=f"customer@{smarter_settings.root_domain}",
            password=password,
            first_name="Customer",
            last_name="User",
        )

        self.handle_completed_success()
