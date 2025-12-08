"""This module is used to deploy a customer API."""

import glob
import io
import os
from typing import Optional

from django.core.management import CommandError, call_command

from smarter.apps.account.models import Account, User, UserProfile
from smarter.apps.account.utils import (
    get_cached_account,
    get_cached_admin_user_for_account,
)
from smarter.apps.chatbot.manifest.models.chatbot.model import SAMChatbot
from smarter.apps.chatbot.models import ChatBot
from smarter.apps.chatbot.tasks import deploy_default_api
from smarter.common.conf import settings as smarter_settings
from smarter.common.exceptions import SmarterValueError
from smarter.lib.django.management.base import SmarterCommand
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.manifest.loader import SAMLoader


# pylint: disable=E1101
class Command(SmarterCommand):
    """
    Deploy built-in chatbots and plugins for a Smarter account.

    This management command automates the deployment of default chatbots and plugins for a given account.
    The account can be specified by its account number. The deployment process reads YAML manifest files
    from predefined directories, applies each manifest to create plugins and chatbots, and then deploys
    each chatbot as a Celery task.

    The deployed chatbots are accessible at URLs of the form:
    ``[chatbot-name].[account-number].api.example.com/chatbot/``

    **Deployment Steps:**
      - Retrieve the account and its admin user using the provided account number.
      - Iterate through all plugin manifest files and create each plugin.
      - Iterate through all chatbot manifest files, create each chatbot, and deploy it asynchronously.
      - Output progress and status messages for each operation.

    This command is intended for administrators to quickly provision standard chatbots and plugins
    for new or existing accounts, ensuring consistent setup and deployment across environments.
    """

    _url: Optional[str] = None
    user: User
    account: Optional[Account] = None
    user_profile: Optional[UserProfile] = None

    def __init__(self, stdout=None, stderr=None, no_color=False, force_color=False):
        super().__init__(stdout, stderr, no_color, force_color)
        self._url = None

    @property
    def url(self) -> str:
        if not self._url:
            raise SmarterValueError("URL is required.")
        return self._url

    @url.setter
    def url(self, value):
        SmarterValidator.validate_url(value)
        self._url = value

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("--account_number", type=str, help="The Smarter account number to which the user belongs")

    def delete_chatbot(self, name: str):
        """Delete a chatbot by name."""
        if not self.account:
            raise SmarterValueError("Account is required to delete a chatbot.")

        try:
            chatbot = ChatBot.objects.get(account=self.account, name=name)
        except ChatBot.DoesNotExist:
            return

        chatbot.delete()
        self.stdout.write(
            self.style.NOTICE(
                f"Found and deleted existing chatbot {name} for account {self.account.account_number} {self.account.company_name}."
            )
        )

    def create_plugin(self, filespec: str) -> bool:
        """
        Create a plugin by name. Apply the Smarter yaml manifest:
        - Read and Parse the YAML file
        - load in the body of the POST request
        - get a response
        - check the response
        """
        if not self.account:
            raise SmarterValueError("Account is required to create a plugin.")
        self.stdout.write(
            f"Creating plugin from manifest {filespec} for account {self.account.account_number} {self.account.company_name}."
        )
        manifest = SAMLoader(file_path=filespec)
        output = io.StringIO()
        try:
            call_command("apply_manifest", manifest=manifest.yaml_data, username="admin", stdout=output)
            return True
        except CommandError as e:
            self.stderr.write(self.style.ERROR(f"apply_manifest raised CommandError: {e}"))
            return False

    def create_and_deploy_chatbot(self, filespec: str) -> bool:
        """
        Create and deploy a chatbot by name. Apply the Smarter yaml manifest:
        - Read and Parse the YAML file
        - load in the body of the POST request
        - get a response
        - check the response
        - get the chatbot by name
        - deploy the chatbot as a Celery task
        """
        if not self.account:
            raise SmarterValueError("Account is required to create and deploy a chatbot.")

        self.stdout.write(
            f"Creating and deploying chatbot from manifest {filespec} for account {self.account.account_number} {self.account.company_name}."
        )

        manifest = SAMLoader(file_path=filespec)
        output = io.StringIO()
        try:
            call_command("apply_manifest", manifest=manifest.yaml_data, username="admin", stdout=output)
        except CommandError as e:
            self.stderr.write(self.style.ERROR(f"apply_manifest raised CommandError: {e}"))
            return False

        try:
            sam_chatbot = SAMChatbot(**manifest.pydantic_model_dump())
            chatbot = ChatBot.objects.get(account=self.account, name=sam_chatbot.metadata.name)

            # deploy the chatbot as a Celery task because this could take a while.
            self.stdout.write(self.style.NOTICE(f"Deploying {chatbot.name} as a Celery task."))
            deploy_default_api.delay(chatbot_id=chatbot.id)  # type: ignore[arg-type]
            return True
        # pylint: disable=W0718
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error occurred while deploying chatbot: {e}"))
            return False

    def handle(self, *args, **options):
        """Deploy built-in chatbots for an account."""
        self.handle_begin()

        if not options["account_number"]:
            self.handle_completed_failure(msg="You must provide an account number.")
            raise SmarterValueError("You must provide an account number.")

        account_number = options["account_number"]
        self.account = get_cached_account(account_number=account_number)
        self.user = get_cached_admin_user_for_account(account=self.account)  # type: ignore[arg-type]
        self.stdout.write(self.style.NOTICE("=" * 80))
        self.stdout.write(self.style.NOTICE(f"{__file__}"))
        self.stdout.write(self.style.NOTICE(f"Deploying built-in plugins and chatbots for account {account_number}."))
        self.stdout.write(self.style.NOTICE("=" * 80))

        plugins_path = os.path.join(smarter_settings.data_directory, "manifests/plugins/*.yaml")
        plugin_files = glob.glob(plugins_path)
        i = 0
        for filespec in plugin_files:
            i += 1
            self.stdout.write(self.style.NOTICE(f"Creating Plugin {i} of {len(plugin_files)}"))
            self.stdout.write(self.style.NOTICE("-" * 80))
            self.create_plugin(filespec=filespec)
            self.stdout.write(self.style.NOTICE("\n"))

        chatbots_path = os.path.join(smarter_settings.data_directory, "manifests/chatbots/*.yaml")
        chatbot_files = glob.glob(chatbots_path)
        i = 0
        for filespec in chatbot_files:
            i += 1
            self.stdout.write(self.style.NOTICE(f"Creating ChatBot {i} of {len(chatbot_files)}"))
            self.stdout.write(self.style.NOTICE("-" * 80))
            self.create_and_deploy_chatbot(filespec=filespec)
            self.stdout.write(self.style.NOTICE("\n"))

        self.handle_completed_success()
