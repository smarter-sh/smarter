"""
This module is used to deploy a collection of customer API's from a GitHub repository containing plugin YAML files
organized in directories by customer API name.
"""

import os
import re
import subprocess

import yaml
from django.core.management.base import BaseCommand

from smarter.apps.account.models import Account, UserProfile
from smarter.apps.account.utils import account_admin_user
from smarter.apps.chatbot.models import ChatBot, ChatBotPlugin
from smarter.apps.chatbot.tasks import deploy_default_api
from smarter.apps.plugin.plugin.static import PluginStatic
from smarter.common.conf import settings as smarter_settings
from smarter.common.exceptions import SmarterValueError
from smarter.lib.django.user import User, UserType
from smarter.lib.django.validators import SmarterValidator


# pylint: disable=E1101,too-many-instance-attributes
class Command(BaseCommand):
    """Deploy customer APIs from a GitHub repository of plugin YAML files organized by customer API name."""

    _url: str = None
    _user: UserType = None
    _account: Account = None
    _user_profile: UserProfile = None

    @property
    def user(self) -> UserType:
        if self._user:
            return self._user
        if self._user_profile:
            return self._user_profile.user
        return None

    @user.setter
    def user(self, value):
        if not isinstance(value, User):
            raise SmarterValueError("User must be a User object.")
        if not value.is_staff:
            raise SmarterValueError(f"User {value.username} is not an account admin.")
        if self._account:
            try:
                self._user_profile = UserProfile.objects.get(account=self._account, user=value)
            except UserProfile.DoesNotExist as e:
                raise SmarterValueError(
                    f"User {value.username} is not associated with account {self._account.account_number}."
                ) from e
        else:
            self._user_profile = UserProfile.objects.filter(user=value).first()
            self._account = self._user_profile.account
        self._user = value

    @property
    def account(self) -> Account:
        if self._account:
            return self._account
        if self._user_profile:
            return self._user_profile.account
        return None

    @account.setter
    def account(self, value):
        if not isinstance(value, Account):
            raise SmarterValueError("Account must be an Account object.")
        if self._user:
            # ensure that we have integrity between user and account
            UserProfile.objects.get(account=value, user=self._user)
        self._account = value

    @property
    def user_profile(self) -> UserProfile:
        if self._user_profile:
            return self._user_profile
        if self._user and self._account:
            try:
                self._user_profile = UserProfile.objects.get(user=self._user, account=self._account)
            except UserProfile.DoesNotExist as e:
                raise SmarterValueError(
                    f"User {self._user.username} is not associated with account {self._account.account_number}."
                ) from e
        return self._user_profile

    @user_profile.setter
    def user_profile(self, value):
        if not isinstance(value, UserProfile):
            raise SmarterValueError("User profile must be a UserProfile object.")
        self._user_profile = value
        self._user = value.user
        self._account = value.account

    @property
    def url(self) -> str:
        if not self._url:
            raise SmarterValueError("URL is required.")
        return self._url

    @url.setter
    def url(self, value):
        SmarterValidator.validate_url(value)
        self._url = value

    @property
    def local_path(self):
        return os.path.join(smarter_settings.data_directory, self.get_url_filename(self.url))

    def get_url_filename(self, url) -> str:
        """
        Get the filename from a URL.
        example: https://github.com/QueriumCorp/smarter_demo/blob/main/hr/shrm_fmla.yaml
        returns "shrm_fmla.yaml"
        """
        return url.split("/")[-1]

    def clone_repo(self):
        """Synchronously clone a GitHub repository to the local file system."""
        self.delete_repo()
        result = subprocess.call(["git", "clone", self.url, self.local_path])
        if result != 0:
            raise subprocess.CalledProcessError(
                returncode=result, cmd=f"git clone {self.url} {self.local_path}", output="Failed to clone repository"
            )

    def delete_repo(self):
        """Delete a cloned GitHub repository from the local file system."""
        if os.path.exists(self.local_path):
            result = subprocess.call(["rm", "-rf", self.local_path])
            if result != 0:
                raise subprocess.CalledProcessError(
                    returncode=result, cmd=f"rm -rf {self.local_path}", output="Failed to delete repository"
                )

    def load_plugin(self, filespec: str):
        """Load a plugin from a file on the local file system."""
        if not self.user_profile:
            raise SmarterValueError("User profile is required.")

        with open(filespec, encoding="utf-8") as file:
            data = file.read()

        if data:
            try:
                data = yaml.safe_load(data)
            except yaml.YAMLError as exc:
                print("Error in configuration file:", exc)
        else:
            raise SmarterValueError("Could not read the file.")

        plugin = PluginStatic(data=data, user_profile=self.user_profile)
        return plugin

    def process_repo(self):
        """
        Process a GitHub repository containing yaml plugin files organized into folders,
        where each folder name is the subdomain for a customer API.
        """

        def is_demo_folder(directory) -> bool:
            """returns true if the folder contains yaml or yml files"""
            VALID_HOST_PATTERN = r"(?!-)[A-Z\d-]{1,63}(?<!-)$"

            folder_name = os.path.basename(directory_path)
            if not re.fullmatch(VALID_HOST_PATTERN, folder_name, re.IGNORECASE):
                print(f"Skipping folder: {folder_name}")
                return False

            for _, _, files in os.walk(directory):
                for file in files:
                    if file.endswith(".yaml") or file.endswith(".yml"):
                        return True
            return False

        if not self.user_profile:
            raise SmarterValueError("User profile is required.")
        self.clone_repo()

        # pylint: disable=too-many-nested-blocks
        for root, directory_names, _ in os.walk(self.local_path):
            for directory in [d for d in directory_names if not d.startswith(".")]:
                # yaml plugins are separated by directories
                # representing different kinds of demo plugins
                # (e.g. "hr", "sales-support", "government", "university-admissions", etc.)
                # and each directory contains a collection of yaml files.
                #
                # We're not currently doing anything with the directory names,
                # but we could use them to create a customer api of the same name.
                directory_path = os.path.join(root, directory)
                api_name = os.path.basename(directory_path)
                if is_demo_folder(directory=directory_path):
                    print(f"Processing API: {api_name}")
                    chatbot, _ = ChatBot.objects.get_or_create(name=api_name, account=self.account)
                    for _, _, files in os.walk(directory_path):
                        for file in files:
                            if file.endswith(".yaml") or file.endswith(".yml"):
                                filespec = os.path.join(directory_path, file)
                                filename = os.path.basename(filespec)
                                print(f"Loading plugin: {filename}")
                                plugin = self.load_plugin(filespec=filespec)
                                ChatBotPlugin.objects.get_or_create(chatbot=chatbot, plugin_meta=plugin.plugin_meta)

                    deploy_default_api(chatbot_id=chatbot.id, with_domain_verification=False)

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("-u", "--url", type=str, help="A url for a public GitHub repository.")
        parser.add_argument(
            "-a",
            "--account_number",
            type=str,
            nargs="?",
            default=None,
            help="Account number that will own the new plugin.",
        )
        parser.add_argument("--username", type=str, nargs="?", default=None, help="A user associated with the account.")

    def handle(self, *args, **options):
        """Process the GitHub repository"""
        self.url = options["url"]
        account_number = options["account_number"]
        username = options["username"]

        if not account_number and not username:
            raise SmarterValueError("username and/or account_number is required.")

        if username:
            self.user = User.objects.get(username=username)

        if account_number:
            self.account = Account.objects.get(account_number=account_number)

        if not self.user_profile:
            admin_user = account_admin_user(self.account)
            print(f"No user profile found. Defaulting to {admin_user}.")
            self.user_profile = UserProfile.objects.get(account=self.account, user=admin_user)

        self.process_repo()
