"""
Command to create the Stackademy AI resources.
"""

import io
import logging

from django.core.management import CommandError

from smarter.apps.account.utils import (
    get_cached_account,
    get_cached_admin_user_for_account,
)
from smarter.apps.api.utils import apply_manifest_v2
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.django.management.base import SmarterCommand


logger = logging.getLogger(__name__)
logger_prefix = formatted_text(f"{__name__}")


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
            logger.error("%s - account number is required.", logger_prefix)
            self.handle_completed_failure(msg="account number is required.")
            return
        account = get_cached_account(account_number=account_number)
        if not account:
            logger.error("%s - Account with account number %s does not exist.", logger_prefix, account_number)
            self.handle_completed_failure(msg=f"Account with account number {account_number} does not exist.")
            return
        admin_user = get_cached_admin_user_for_account(account)
        if not admin_user:
            logger.error("%s - No admin user found for account %s.", logger_prefix, account_number)
            self.handle_completed_failure(msg=f"No admin user found for account {account_number}.")
            return
        username = admin_user.username

        logger.debug(
            "%s - Setting up Stackademy AI resources for account number: %s, username: %s",
            logger_prefix,
            account_number,
            username,
        )

        def apply(file_path):

            try:
                apply_manifest_v2(filespec=file_path, username=username, verbose=True)
            except Exception as e:
                raise CommandError(f"Failed to apply manifest {file_path}: {str(e)}") from e

        try:
            logger.debug("%s - Creating Stackademy Sql Chatbot...", logger_prefix)
            sql_file_paths = [
                "smarter/apps/account/data/example-manifests/secret-smarter-test-db.yaml",
                "smarter/apps/plugin/data/sample-connections/smarter-test-db.yaml",
                "smarter/apps/plugin/data/stackademy/stackademy-plugin-sql.yaml",
                "smarter/apps/plugin/data/stackademy/stackademy-chatbot-sql.yaml",
            ]
            for file_path in sql_file_paths:
                apply(file_path)

            logger.debug("%s - Successfully created Stackademy Sql Chatbot.", logger_prefix)

            logger.debug("%s - Creating Stackademy Api Chatbot...", logger_prefix)
            api_file_paths = [
                "smarter/apps/account/data/example-manifests/secret-smarter-test-api.yaml",
                "smarter/apps/plugin/data/sample-connections/smarter-test-api.yaml",
                "smarter/apps/plugin/data/stackademy/stackademy-plugin-api.yaml",
                "smarter/apps/plugin/data/stackademy/stackademy-chatbot-api.yaml",
            ]
            for file_path in api_file_paths:
                apply(file_path)

            logger.debug("%s - Successfully created Stackademy Api Chatbot.", logger_prefix)

        # pylint: disable=W0718
        except Exception as e:
            self.handle_completed_failure(e)
            return

        self.handle_completed_success()
