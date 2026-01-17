"""
Command to create the Stackademy AI resources.
"""

import io
import logging

from django.core.management import call_command

from smarter.apps.account.utils import (
    get_cached_account,
    get_cached_admin_user_for_account,
)
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.django.management.base import SmarterCommand


logger = logging.getLogger(__name__)
logger_prefix = formatted_text(f"{__name__}.create_stackademy")


class Command(SmarterCommand):
    """
    Django manage.py create_stackademy command.
    This command is used to create the Stackademy AI resources
    used for training and testing. It creates the following:

    Sql-based chatbot
    -----------------
    - Secret for SqlConnection
    - SqlConnection
    - Stackademy SqlPlugin
    - Chatbot using the Stackademy SqlPlugin

    Api-based chatbot
    -----------------
    - Secret for ApiConnection
    - ApiConnection
    - Stackademy ApiPlugin
    - Chatbot using the Stackademy ApiPlugin
    """

    def add_arguments(self, parser):
        """Add arguments to the command."""

        parser.add_argument(
            "--account_number",
            type=str,
            help="The account number that will own the remote Api connection. Defaults to smarter_test_api",
        )

    def handle(self, *args, **options):
        """Create the Stackademy ApiPlugin."""
        self.handle_begin()

        output = io.StringIO()
        error_output = io.StringIO()
        account_number = options.get("account_number")
        if not account_number:
            self.stdout.write(self.style.ERROR("account number is required."))
            self.handle_completed_failure(msg="account number is required.")
            return
        account = get_cached_account(account_number=account_number)
        if not account:
            self.stdout.write(self.style.ERROR(f"Account with account number {account_number} does not exist."))
            self.handle_completed_failure(msg=f"Account with account number {account_number} does not exist.")
            return
        admin_user = get_cached_admin_user_for_account(account)
        if not admin_user:
            self.stdout.write(self.style.ERROR(f"No admin user found for account {account_number}."))
            self.handle_completed_failure(msg=f"No admin user found for account {account_number}.")
            return
        username = admin_user.username

        self.stdout.write(
            self.style.NOTICE(
                f"{logger_prefix} Setting up Stackademy AI resources for account number: {account_number}, username: {username}"
            )
        )

        def apply(file_path):

            self.stdout.write(self.style.NOTICE(f"{logger_prefix} Applying manifest from file: {file_path}"))
            call_command(
                "apply_manifest",
                filespec=file_path,
                username=username,
                verbose=True,
                stdout=output,
                stderr=error_output,
            )
            if not error_output.getvalue():
                self.stdout.write(
                    self.style.SUCCESS(f"{logger_prefix} Successfully applied manifest from file: {file_path}")
                )
                output.truncate(0)
                output.seek(0)
            else:
                error_msg = error_output.getvalue()
                self.stdout.write(
                    self.style.ERROR(f"{logger_prefix} Error applying manifest from file: {file_path}: {error_msg}")
                )
                error_output.truncate(0)
                error_output.seek(0)
                raise Exception(f"Error applying manifest from file: {file_path}: {error_msg}")

        try:
            self.stdout.write(self.style.NOTICE(f"{logger_prefix} Creating Stackademy Sql Chatbot..."))
            sql_file_paths = [
                "smarter/apps/account/data/example-manifests/secret-smarter-test-db.yaml",
                "smarter/apps/plugin/data/sample-connections/smarter-test-db.yaml",
                "smarter/apps/plugin/data/stackademy/stackademy-plugin-sql.yaml",
                "smarter/apps/plugin/data/stackademy/stackademy-chatbot-sql.yaml",
            ]
            for file_path in sql_file_paths:
                apply(file_path)

            self.stdout.write(self.style.SUCCESS(f"{logger_prefix} Successfully created Stackademy Sql Chatbot."))

            self.stdout.write(self.style.NOTICE(f"{logger_prefix} Creating Stackademy Api Chatbot..."))
            api_file_paths = [
                "smarter/apps/account/data/example-manifests/secret-smarter-test-api.yaml",
                "smarter/apps/plugin/data/sample-connections/smarter-test-api.yaml",
                "smarter/apps/plugin/data/stackademy/stackademy-plugin-api.yaml",
                "smarter/apps/plugin/data/stackademy/stackademy-chatbot-api.yaml",
            ]
            for file_path in api_file_paths:
                apply(file_path)

            self.stdout.write(self.style.SUCCESS(f"{logger_prefix} Successfully created Stackademy Api Chatbot."))

        # pylint: disable=W0718
        except Exception as e:
            self.handle_completed_failure(e)
            return

        self.handle_completed_success()
