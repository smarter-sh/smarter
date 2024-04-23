"""This module is used to generate seed records for the chat history models."""

import glob
import json
import os
import secrets
from pathlib import Path

from django.core.management.base import BaseCommand

from smarter.apps.account.models import Account, UserProfile
from smarter.apps.account.utils import account_admin_user
from smarter.apps.chat.models import Chat
from smarter.apps.chat.providers.smarter import handler
from smarter.apps.chatbot.models import ChatBot, ChatBotPlugin
from smarter.common.conf import settings as smarter_settings
from smarter.common.const import SMARTER_ACCOUNT_NUMBER, SMARTER_EXAMPLE_CHATBOT_NAME


HERE = Path(__file__).resolve().parent


# pylint: disable=E1101
class Command(BaseCommand):
    """Django manage.py get_plugins command. This command is used to generate a JSON list of all accounts."""

    def handle(self, *args, **options):
        data_folder_path = os.path.join(HERE, "data", "*.json")
        account = Account.objects.get(account_number=SMARTER_ACCOUNT_NUMBER)
        user = account_admin_user(account)
        user_profile = UserProfile.objects.get(account=account, user=user)
        chatbot = ChatBot.objects.get(account=user_profile.account, name=SMARTER_EXAMPLE_CHATBOT_NAME)
        session_key = "seed_chat_history.py_" + secrets.token_urlsafe(16)
        chat = Chat.objects.create(
            session_key=session_key,
            url="https://smarter.com/seed-chat-history",
            ip_address="192.1.1.1",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
        )

        for file_path in glob.glob(data_folder_path):
            print("Processing file: ", file_path)
            with open(file_path, encoding="utf-8") as file:
                data = json.loads(file.read())
                plugins = ChatBotPlugin().plugins(chatbot=chatbot)
                handler(
                    chat_id=chat.id,
                    plugins=plugins,
                    user=user_profile.user,
                    data=data,
                    default_model=smarter_settings.openai_default_model,
                    default_temperature=smarter_settings.openai_default_temperature,
                    default_max_tokens=smarter_settings.openai_default_max_tokens,
                )
