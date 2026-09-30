"""This module is used to deploy a customer API."""

import glob
import io
import os
from typing import Optional

from django.core.management import CommandError, call_command

from smarter.apps.account.models import Account, User, UserProfile
from smarter.apps.account.utils import (
    get_cached_admin_user_for_account,
    smarter_cached_objects,
)
from smarter.apps.llmclient.manifest.models.llmclient.model import SAMLLMClient
from smarter.apps.llmclient.models import LLMClient
from smarter.common.conf import smarter_settings
from smarter.common.const import SMARTER_ADMIN_USERNAME
from smarter.common.exceptions import SmarterValueError
from smarter.lib.django.management.base import SmarterCommand
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.manifest.loader import SAMLoader


# pylint: disable=E1101
class Command(SmarterCommand):
    """
    Deploy built-in llmclients and plugins for a Smarter account.

    This management command automates the deployment of default llmclients and plugins for a given account.
    The account can be specified by its account number. The deployment process reads YAML manifest files
    from predefined directories, applies each manifest to create plugins and llmclients, and then deploys
    each llmclient as a Celery task.

    The deployed llmclients are accessible at URLs of the form:
    ``[llmclient-name].[account-number].api.example.com/llm-client/``

    **Deployment Steps:**
      - Retrieve the account and its admin user using the provided account number.
      - Iterate through all plugin manifest files and create each plugin.
      - Iterate through all llmclient manifest files, create each llmclient, and deploy it asynchronously.
      - Output progress and status messages for each operation.

    This command is intended for administrators to quickly provision standard llmclients and plugins
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
        parser.add_argument(
            "--account_number",
            type=str,
            help="The Smarter account number to which the user belongs",
            default=smarter_cached_objects.smarter_account.account_number,
        )

    def delete_llmclient(self, name: str):
        """Delete an llmclient by name."""
        if not self.user_profile:
            raise SmarterValueError("UserProfile is required to delete an llmclient.")

        try:
            llmclient = LLMClient.objects.get(user_profile=self.user_profile, name=name)
        except LLMClient.DoesNotExist:
            return

        llmclient.delete()
        self.stdout.write(
            self.style.NOTICE(f"Found and deleted existing llmclient {name} for user_profile {self.user_profile}.")
        )

    def create_plugin(self, filespec: str) -> bool:
        """
        Create a plugin by name.

        Apply the Smarter yaml manifest:
        - Read and Parse the YAML file
        - load in the body of the POST request
        - get a response
        - check the response
        """
        if not self.user_profile:
            raise SmarterValueError("UserProfile is required to create a plugin.")
        self.stdout.write(f"Creating plugin from manifest {filespec} for user_profile {self.user_profile}.")
        manifest = SAMLoader(file_path=filespec)
        output = io.StringIO()
        try:
            call_command("apply_manifest", manifest=manifest.yaml_data, username=SMARTER_ADMIN_USERNAME, stdout=output)
            return True
        except CommandError as e:
            self.stderr.write(self.style.ERROR(f"apply_manifest raised CommandError: {e}"))
            return False

    def create_and_deploy_llmclient(self, filespec: str) -> bool:
        """
        Create and deploy an llmclient by name.

        Apply the Smarter yaml manifest:
        - Read and Parse the YAML file
        - load in the body of the POST request
        - get a response
        - check the response
        - get the llmclient by name
        - deploy the llmclient as a Celery task
        """
        if not self.user_profile:
            raise SmarterValueError("UserProfile is required to create and deploy an llmclient.")

        self.stdout.write(
            f"Creating and deploying llmclient from manifest {filespec} for user_profile {self.user_profile}."
        )

        manifest = SAMLoader(file_path=filespec)
        output = io.StringIO()
        try:
            call_command("apply_manifest", manifest=manifest.yaml_data, username=SMARTER_ADMIN_USERNAME, stdout=output)
        except CommandError as e:
            self.stderr.write(self.style.ERROR(f"apply_manifest raised CommandError: {e}"))
            return False

        try:
            sam_llmclient = SAMLLMClient(**manifest.pydantic_model_dump())
            llmclient = LLMClient.objects.get(user_profile=self.user_profile, name=sam_llmclient.metadata.name)
            llmclient.deployed = True
            llmclient.save()
            return True
        # pylint: disable=W0718
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error occurred while deploying llmclient: {e}"))
            return False

    def handle(self, *args, **options):
        """Deploy built-in llmclients for an account."""
        self.handle_begin()

        if not options["account_number"]:
            self.handle_completed_failure(msg="You must provide an account number.")
            raise SmarterValueError("You must provide an account number.")

        account_number = options["account_number"]
        self.account = Account.get_cached_object(invalidate=False, account_number=account_number)  # type: ignore[assignment]
        admin = get_cached_admin_user_for_account(account=self.account)  # type: ignore[assignment]
        admin_user_profile = UserProfile.get_cached_object(user=admin, account=self.account)  # type: ignore[assignment]
        self.user_profile = admin_user_profile  # type: ignore[arg-type]
        self.stdout.write(self.style.NOTICE("=" * 80))
        self.stdout.write(self.style.NOTICE(f"{__file__}"))
        self.stdout.write(self.style.NOTICE(f"Deploying built-in plugins and llmclients for account {account_number}."))
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

        llmclients_path = os.path.join(smarter_settings.data_directory, "manifests/llm-clients/*.yaml")
        llmclient_files = glob.glob(llmclients_path)
        i = 0
        for filespec in llmclient_files:
            i += 1
            self.stdout.write(self.style.NOTICE(f"Creating LLMClient {i} of {len(llmclient_files)}"))
            self.stdout.write(self.style.NOTICE("-" * 80))
            self.create_and_deploy_llmclient(filespec=filespec)
            self.stdout.write(self.style.NOTICE("\n"))

        self.handle_completed_success()
