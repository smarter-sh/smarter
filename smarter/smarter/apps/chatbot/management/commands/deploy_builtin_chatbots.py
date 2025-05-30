"""This module is used to deploy a customer API."""

import glob
import os
from http import HTTPStatus
from urllib.parse import urljoin

import yaml
from django.core.handlers.wsgi import WSGIRequest
from django.core.management.base import BaseCommand
from django.http import HttpResponse
from django.test import RequestFactory
from rest_framework.test import force_authenticate

from smarter.apps.account.utils import get_cached_admin_user_for_account
from smarter.apps.api.v1.cli.views.apply import ApiV1CliApplyApiView
from smarter.apps.chatbot.models import ChatBot
from smarter.apps.chatbot.tasks import deploy_default_api
from smarter.common.conf import settings as smarter_settings
from smarter.common.exceptions import SmarterValueError
from smarter.lib.django.validators import SmarterValidator


# pylint: disable=E1101
class Command(BaseCommand):
    """
    Deploy a customer API. Provide either an account number or a company name.
    Deploys to a URL of the form [chatbot-name].####-####-####.api.smarter.sh/chatbot/
    """

    _url: str = None

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

    def read_file(self, file_path: str) -> str:
        """
        Read the data from a file.
        file_path: The path to the file.
        """
        self.stdout.write(f"Reading file {file_path}.")
        with open(file_path, encoding="utf-8") as file:
            data = file.read()
            return data

    def parse_yaml(self, data: str) -> dict:
        """
        Parse a yaml file.
        data: a string representing the yaml file.
        """
        self.stdout.write("Parsing yaml file.")
        try:
            manifest_data: dict = yaml.safe_load(data)
            return manifest_data
        except yaml.YAMLError as exc:
            self.stderr.write(self.style.ERROR(f"Error in yaml manifest file: {exc}"))
            self.stdout.write(data)

    def apply_manifest(self, manifest_data: dict) -> HttpResponse:
        """
        Apply a Smarter manifest.
        Account: The account to which the manifest applies.
        manifest_data: a string representation of a yaml manifest file
        """
        self.stdout.write(f"Applying manifest for account {self.account.account_number} {self.account.company_name}.")
        request_factory = RequestFactory()
        response: HttpResponse = None
        self.url = urljoin(smarter_settings.environment_url, "/api/v1/cli/apply")

        try:
            request: WSGIRequest = request_factory.post(self.url, data=manifest_data, content_type="application/json")
            request.user = self.user
            force_authenticate(request, user=self.user)
            self.stdout.write(f"Sending POST request to {self.url} with authenticated user {request.user}.")
            api_v1_cli_apply_view = ApiV1CliApplyApiView.as_view()
            response: HttpResponse = api_v1_cli_apply_view(request=request)

            if response.status_code == HTTPStatus.OK:
                self.stdout.write(self.style.SUCCESS(f"Response: {str(response)}"))
            else:
                self.stderr.write(self.style.ERROR(f"Error in API response: {str(response)}"))
        except yaml.YAMLError as exc:
            self.stderr.write(self.style.ERROR(f"Error in yaml manifest file: {exc}"))
            self.stdout.write(manifest_data)

        return response

    def delete_chatbot(self, name: str):
        """Delete a chatbot by name."""

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

    def create_plugin(self, yaml_file: str) -> bool:
        """
        Create a plugin by name. Apply the Smarter yaml manifest:
        - Read and Parse the YAML file
        - load in the body of the POST request
        - get a response
        - check the response
        """
        self.stdout.write(
            f"Creating plugin from manifest {yaml_file} for account {self.account.account_number} {self.account.company_name}."
        )
        file_data = self.read_file(file_path=yaml_file)
        parsed_manifest_data = self.parse_yaml(file_data)
        if not parsed_manifest_data:
            self.stderr.write(self.style.ERROR(f"Error parsing yaml file {yaml_file}."))
            return False
        response = self.apply_manifest(manifest_data=file_data)
        return response.status_code == HTTPStatus.OK

    def create_and_deploy_chatbot(self, yaml_file: str) -> bool:
        """
        Create and deploy a chatbot by name. Apply the Smarter yaml manifest:
        - Read and Parse the YAML file
        - load in the body of the POST request
        - get a response
        - check the response
        - get the chatbot by name
        - deploy the chatbot as a Celery task
        """
        self.stdout.write(
            f"Creating and deploying chatbot from manifest {yaml_file} for account {self.account.account_number} {self.account.company_name}."
        )
        chatbot: ChatBot = None

        file_data = self.read_file(file_path=yaml_file)
        parsed_manifest_data = self.parse_yaml(file_data)
        if not parsed_manifest_data:
            self.stderr.write(self.style.ERROR(f"Error parsing yaml file {yaml_file}."))
            return False
        chatbot_name = parsed_manifest_data.get("metadata", {}).get("name")
        try:
            chatbot = ChatBot.objects.get(account=self.account, name=chatbot_name)
            if chatbot.deployed:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"You're all set! {chatbot.hostname} is already deployed for {self.account.account_number} {self.account.company_name}."
                    )
                )
                return False
        except ChatBot.DoesNotExist:
            pass

        response = self.apply_manifest(manifest_data=file_data)
        if response.status_code != HTTPStatus.OK:
            self.stderr.write(self.style.ERROR(f"Error in API response: {str(response)}"))
            return False

        # the Smarter Chatbot should exist now as a Django model, but it is not yet deployed
        try:
            chatbot = ChatBot.objects.get(account=self.account, name=chatbot_name)
        except ChatBot.DoesNotExist:
            self.stderr.write(
                self.style.ERROR(
                    f"Internal error. ChatBot {chatbot_name} not found for account {self.account.account_number} {self.account.company_name}."
                )
            )
            return False

        # deploy the chatbot as a Celery task because this could take a while.
        self.stdout.write(self.style.NOTICE(f"Deploying {chatbot_name} as a Celery task."))
        deploy_default_api.delay(chatbot_id=chatbot.id)
        return True

    def handle(self, *args, **options):

        if not options["account_number"]:
            raise SmarterValueError("You must provide an account number.")

        self.account_number = options["account_number"]
        self.user = get_cached_admin_user_for_account(account=self.account)
        self.stdout.write(self.style.NOTICE("=" * 80))
        self.stdout.write(self.style.NOTICE(f"{__file__}"))
        self.stdout.write(
            self.style.NOTICE(f"Deploying built-in plugins and chatbots for account {self.account_number}.")
        )
        self.stdout.write(self.style.NOTICE("=" * 80))

        plugins_path = os.path.join(smarter_settings.data_directory, "manifests/plugins/*.yaml")
        plugin_files = glob.glob(plugins_path)
        i = 0
        for yaml_file in plugin_files:
            i += 1
            self.stdout.write(self.style.NOTICE(f"Creating Plugin {i} of {len(plugin_files)}"))
            self.stdout.write(self.style.NOTICE("-" * 80))
            self.create_plugin(yaml_file=yaml_file)
            self.stdout.write(self.style.NOTICE("\n"))

        chatbots_path = os.path.join(smarter_settings.data_directory, "manifests/chatbots/*.yaml")
        chatbot_files = glob.glob(chatbots_path)
        i = 0
        for yaml_file in chatbot_files:
            i += 1
            self.stdout.write(self.style.NOTICE(f"Creating ChatBot {i} of {len(chatbot_files)}"))
            self.stdout.write(self.style.NOTICE("-" * 80))
            self.create_and_deploy_chatbot(yaml_file=yaml_file)
            self.stdout.write(self.style.NOTICE("\n"))
