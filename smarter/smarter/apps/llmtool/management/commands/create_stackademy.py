"""Command to create the Stackademy AI resources."""

from typing import Optional

from django.core.management import CommandError

from smarter.apps.account.models import Account
from smarter.apps.account.utils import (
    get_cached_admin_user_for_account,
)
from smarter.apps.api.utils import apply_manifest_v2
from smarter.common.const import SMARTER_ACCOUNT_NUMBER
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib import logging
from smarter.lib.django.management.base import SmarterCommand
from smarter.lib.manifest.template import TEMPLATE_EXTENSION, render_manifest_template

logger = logging.getLogger(__name__)
logger_prefix = formatted_text(f"{__name__}")

API_CONNECTION_FILE_PATH = "smarter/apps/connection/data/sample-connections/smarter-test-api.yaml.tpl"
"""The Stackademy ApiConnection, a manifest template whose ``baseUrl`` is the api of this platform."""


class Command(SmarterCommand):
    """
    Django manage.py create_stackademy command.

    This command is used to create the Stackademy AI resources
    used for training and testing. It creates the following:

    Sql-based llmclient
    --------------------
    - Secret for SqlConnection
    - SqlConnection
    - Stackademy SqlPlugin
    - LLMClient using the Stackademy SqlPlugin

    Api-based llmclient
    --------------------
    - Secret for ApiConnection
    - ApiConnection, to this platform's Stackademy test api
    - Stackademy ApiPlugin
    - LLMClient using the Stackademy ApiPlugin
    """

    def add_arguments(self, parser):
        """Add arguments to the command."""

        parser.add_argument(
            "--account_number",
            type=str,
            help="The account number that will own the remote Api connection. Defaults to smarter_test_api",
            default=SMARTER_ACCOUNT_NUMBER,
        )

    def handle(self, *args, **options):
        """Create the Stackademy ApiPlugin."""
        self.handle_begin()

        account_number = options.get("account_number")
        if not account_number:
            logger.error("%s - account number is required.", logger_prefix)
            self.handle_completed_failure(msg="account number is required.")
            return
        try:
            account = Account.get_cached_object(invalidate=False, account_number=account_number)
        except Account.DoesNotExist:
            account = None
        if not account:
            logger.error("%s - Account with account number %s does not exist.", logger_prefix, account_number)
            self.handle_completed_failure(msg=f"Account with account number {account_number} does not exist.")
            return
        admin_user = get_cached_admin_user_for_account(account=account)
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

        def apply(file_path: str):

            # a manifest template, *.yaml.tpl, is filled in with the scheme and domain of this platform.
            manifest: Optional[str] = None
            if file_path.endswith(TEMPLATE_EXTENSION):
                with open(file_path, encoding="utf-8") as f:
                    manifest = render_manifest_template(f.read())
            try:
                applied = apply_manifest_v2(filespec=file_path, manifest=manifest, username=username, verbose=True)
            except Exception as e:
                raise CommandError(f"Failed to apply manifest {file_path}: {str(e)}") from e
            if not applied:
                raise CommandError(f"Failed to apply manifest {file_path}.")

        try:
            logger.debug("%s - Creating Stackademy SQL Prompt Integration...", logger_prefix)
            sql_file_paths = [
                "smarter/apps/account/data/example-manifests/secret-smarter-test-db.yaml",
                "smarter/apps/connection/data/sample-connections/smarter-test-db.yaml",
                "smarter/apps/llmtool/data/stackademy/stackademy-plugin-sql.yaml",
                "smarter/apps/llmtool/data/stackademy/stackademy-llmclient-sql.yaml",
            ]
            for file_path in sql_file_paths:
                apply(file_path)

            logger.debug("%s - Successfully created Stackademy SQL Prompt Integration.", logger_prefix)

            logger.debug("%s - Creating Stackademy Api LLMClient...", logger_prefix)
            api_file_paths = [
                "smarter/apps/account/data/example-manifests/secret-smarter-test-api.yaml",
                API_CONNECTION_FILE_PATH,
                "smarter/apps/llmtool/data/stackademy/stackademy-plugin-api.yaml",
                "smarter/apps/llmtool/data/stackademy/stackademy-llmclient-api.yaml",
            ]
            for file_path in api_file_paths:
                apply(file_path)

            logger.debug("%s - Successfully created Stackademy Api LLMClient.", logger_prefix)

        # pylint: disable=W0718
        except Exception as e:
            self.handle_completed_failure(e)
            return

        self.handle_completed_success()
