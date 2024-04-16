"""This module is used to generate seed records for the chat history models."""

import glob
import json
import os
from pathlib import Path

from django.core.management.base import BaseCommand

from smarter.apps.account.models import Account, UserProfile
from smarter.apps.account.utils import account_admin_user
from smarter.apps.chat.providers.smarter import handler
from smarter.apps.chatbot.models import ChatBot, ChatBotPlugin
from smarter.common.const import SMARTER_ACCOUNT_NUMBER, SMARTER_DEMO_API_NAME


HERE = Path(__file__).resolve().parent


# pylint: disable=E1101
class Command(BaseCommand):
    """Django manage.py get_plugins command. This command is used to generate a JSON list of all accounts."""

    def handle(self, *args, **options):
        data_folder_path = os.path.join(HERE, "data", "*.json")
        account = Account.objects.get(account_number=SMARTER_ACCOUNT_NUMBER)
        user = account_admin_user(account)
        user_profile = UserProfile.objects.get(account=account, user=user)
        chatbot = ChatBot.objects.get(account=user_profile.account, name=SMARTER_DEMO_API_NAME)

        for file_path in glob.glob(data_folder_path):
            print("Processing file: ", file_path)
            with open(file_path, encoding="utf-8") as file:
                data = json.loads(file.read())
                plugins = ChatBotPlugin().plugins(chatbot=chatbot)
                handler(plugins=plugins, user=user_profile.user, data=data)
