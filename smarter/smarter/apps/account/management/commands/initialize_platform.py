"""Django manage.py initialize_platform command."""

import getpass

from django.core.management import call_command

from smarter.common.conf import smarter_settings
from smarter.lib.django.management.base import SmarterCommand


class Command(SmarterCommand):
    """Django manage.py initialize_platform command."""

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument(
            "--username",
            type=str,
            help="The user to associate with this Secret. If not provided, the current user will be used.",
        )
        parser.add_argument("--email", type=str, help="The email address of the user to associate with this Secret.")
        parser.add_argument(
            "--password", type=str, help="The value to encrypt and persist. If not provided, you will be prompted."
        )
        parser.add_argument(
            "--smarter_test_db_host",
            type=str,
            help="The hostname for the remote MySql database used for SqlConnection tests. Defaults to sql.lawrencemcdaniel.com",
        )
        parser.add_argument(
            "--smarter_test_db",
            type=str,
            help="The database to use for the remote MySql database used for SqlConnection tests. Defaults to smarter_test_db",
        )
        parser.add_argument(
            "--smarter_test_db_username",
            type=str,
            help="The username to use for the remote MySql database used for SqlConnection tests. Defaults to smarter_test_user",
        )
        parser.add_argument(
            "--smarter_test_db_password",
            type=str,
            help="The password to use for the remote MySql database used for SqlConnection tests",
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
            password = "smarter"
            self.stdout.write(self.style.WARNING(f"No password provided, using the default value: {password}"))

        test_db_host = options.get("smarter_test_db_host")
        if not test_db_host:
            test_db_host = "sql.lawrencemcdaniel.com"

        test_db_name = options.get("smarter_test_db")
        if not test_db_name:
            test_db_name = "smarter_test_db"

        test_db_username = options.get("smarter_test_db_username")
        if not test_db_username:
            test_db_username = "smarter_test_user"

        test_db_password = options.get("smarter_test_db_password")
        if not test_db_password:
            test_db_password = "smarter_test_user"
            self.stdout.write(self.style.WARNING(f"No password provided, using the default value: {test_db_password}"))

        # Create one user for each role: admin, staff, customer.
        call_command("create_smarter_admin", username=username, password=password, email=email)
        call_command(
            "create_user",
            account_number="3141-5926-5359",
            username="staff_user",
            email="staff@smarter.sh",
            password=password,
            first_name="Staff",
            last_name="User",
            admin=True,
        )
        call_command(
            "create_user",
            account_number="3141-5926-5359",
            username="customer_user",
            email="customer@smarter.sh",
            password=password,
            first_name="Customer",
            last_name="User",
        )

        # Setup University of British Columbia account
        call_command("create_account", account_number="5680-6558-6577", company_name="University of British Columbia")
        call_command(
            "create_user",
            account_number="5680-6558-6577",
            username="admin_ubc",
            email="admin_ubc@smarter.sh",
            password=password,
            first_name="UBC",
            last_name="Admin",
            admin=True,
        )

        # Setup Beta Users account
        call_command("create_account", account_number="4386-2072-3294", company_name="Beta Users")
        call_command(
            "create_user",
            account_number="4386-2072-3294",
            username="admin_beta",
            email="admin_beta@smarter.sh",
            password=password,
            first_name="Beta",
            last_name="Admin",
            admin=True,
        )

        # Initialize platform components.
        call_command("initialize_waffle")
        call_command("initialize_wagtail")
        call_command("initialize_providers")
        call_command("verify_dns_configuration")

        # Load example plugins and chatbots from GitHub.
        call_command(
            "load_from_github", account_number="3141-5926-5359", url="https://github.com/QueriumCorp/smarter-demo"
        )
        call_command(
            "load_from_github",
            account_number="3141-5926-5359",
            url="https://github.com/smarter-sh/examples",
            repo_version=2,
        )
        call_command(
            "load_from_github",
            account_number="5680-6558-6577",
            url="https://github.com/smarter-sh/examples",
            repo_version=2,
        )
        call_command(
            "load_from_github",
            account_number="4386-2072-3294",
            url="https://github.com/smarter-sh/examples",
            repo_version=2,
        )

        # Add builtin plugin examples and deploy chatbots.
        call_command("add_plugin_examples", username=username)
        call_command("deploy_example_chatbot")
        call_command("deploy_builtin_chatbots", account_number="3141-5926-5359")
        call_command("deploy_builtin_chatbots", account_number="4386-2072-3294")
        call_command("deploy_builtin_chatbots", account_number="5680-6558-6577")

        # Setup Stackademy AI resources, used for training and testing.
        call_command("create_stackademy", account_number="3141-5926-5359")
        call_command("create_stackademy", account_number="4386-2072-3294")
        call_command("create_stackademy", account_number="5680-6558-6577")

        self.handle_completed_success()
