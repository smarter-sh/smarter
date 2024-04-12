# -*- coding: utf-8 -*-
"""
This module is used to deploy a collection of customer API's from a GitHub repository containing plugin YAML files
organized in directories by customer API name.
"""
import os
import subprocess

import yaml
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from smarter.apps.account.models import Account, UserProfile
from smarter.apps.chatbot.models import ChatBot, ChatBotPlugin
from smarter.apps.chatbot.tasks import deploy_default_api
from smarter.apps.plugin.plugin import Plugin


User = get_user_model()


# pylint: disable=E1101
class Command(BaseCommand):
    """Upsert a collection of plugins from a GitHub repository."""

    HERE = os.path.abspath(os.path.dirname(__file__))

    def clone_repo(self, url, path):
        """Synchronously clone a GitHub repository to the local file system."""
        result = subprocess.call(["git", "clone", url, path])
        if result != 0:
            raise subprocess.CalledProcessError(
                returncode=result, cmd=f"git clone {url} {path}", output="Failed to clone repository"
            )

    def load_plugin(self, filespec: str, user_profile: UserProfile):
        """Load a plugin from a file."""

        with open(filespec, "r", encoding="utf-8") as file:
            data = file.read()

        if data:
            try:
                data = yaml.safe_load(data)
            except yaml.YAMLError as exc:
                print("Error in configuration file:", exc)
        else:
            raise ValueError("Could not read the file.")

        data["user"] = user_profile.user
        data["account"] = user_profile.account
        data["user_profile"] = user_profile
        data["meta_data"]["author"] = user_profile.id

        plugin = Plugin(data=data, user_profile=user_profile)
        return plugin

    def get_filename(self, url: str):
        """Get the filename from a URL."""
        return url.split("/")[-1]

    def process_repo(self, url: str, user_profile: UserProfile):
        """
        Process a GitHub repository.
        Iterated the folder structure of the repository scanning for plugin YAML files.
        """
        filename = self.get_filename(url)
        path = os.path.join(self.HERE, filename)
        self.clone_repo(url, path)

        for root, directory_names, _ in os.walk(path):
            for directory in directory_names:
                # yaml plugins are separated by directories
                # representing different kinds of demo plugins
                # (e.g. "hr", "sales-support", "government", "university-admissions", etc.)
                # and each directory contains a collection of yaml files.
                #
                # We're not currently doing anything with the directory names,
                # but we could use them to create a customer api of the same name.
                directory_path = os.path.join(root, directory)
                api_name = directory_path
                chatbot, _ = ChatBot.objects.get_or_create(name=api_name, user_profile=user_profile)
                for _, _, files in os.walk(directory_path):
                    for file in files:
                        if file.endswith(".yaml") or file.endswith(".yml"):
                            filespec = os.path.join(directory_path, file)
                            plugin = self.load_plugin(filespec=filespec, user_profile=user_profile)
                            ChatBotPlugin.objects.get_or_create(chatbot=chatbot, plugin=plugin)

                deploy_default_api(chatbot_id=chatbot.id, with_domain_verification=False)

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument(
            "account_number", type=str, nargs="?", default=None, help="Account number that will own the new plugin."
        )
        parser.add_argument("username", type=str, nargs="?", default=None, help="A user associated with the account.")
        parser.add_argument("url", type=str, default=None, help="A public url to a plugin YAML file")

    def handle(self, *args, **options):
        """create the plugin."""
        account_number = options["account_number"]
        username = options["username"]
        url = options["url"]

        account: Account = None
        user: User = None
        user_profile: UserProfile = None

        try:
            # want to ensure that we either get both or neither or these, and also
            # that we can distinguish between a user who is not an admin vs
            # a username that doesn't exist.
            if username:
                user = User.objects.get(username=username)
                if not user.is_staff:
                    raise ValueError(f"User {username} is not an account admin.")
                user_profile, _ = UserProfile.objects.get_or_create(user=user, account=account)
        except (User.DoesNotExist, UserProfile.DoesNotExist) as e:
            raise ValueError(f"User {username} does not exist for account {account.account_number}.") from e

        try:
            # if account_number is not provided then we need to ensure that it is consistent
            # with the account from the user profile of an optionally-provided username.
            #
            # if we don't have a username then we'll default to the most senior account admin.
            if account_number:
                account = Account.objects.get(account_number=account_number)
                if user_profile:
                    if account != user_profile.account:
                        raise ValueError(f"User {username} does not belong to account {account.account_number}.")
                else:
                    try:
                        user_profile = (
                            UserProfile.objects.filter(account=account, user__is_staff=True).order_by("pk").first()
                        )
                    except UserProfile.DoesNotExist as e:
                        raise ValueError(f"No account admin found for account {account.account_number}.") from e
        except Account.DoesNotExist as e:
            raise ValueError(f"Account {account_number} does not exist.") from e

        self.process_repo(url, user_profile)
