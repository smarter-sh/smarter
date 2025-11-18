"""This module is used to generate seed records for the chat history models."""

import glob
import os
import secrets
from pathlib import Path

from django.core.management.base import BaseCommand

from smarter.apps.account.models import Account
from smarter.apps.account.utils import (
    get_cached_admin_user_for_account,
    get_cached_user_profile,
)
from smarter.apps.chatbot.models import ChatBot, ChatBotPlugin
from smarter.apps.prompt.models import Chat
from smarter.apps.prompt.providers.providers import chat_providers
from smarter.common.const import SMARTER_ACCOUNT_NUMBER, SMARTER_EXAMPLE_CHATBOT_NAME
from smarter.lib import json


HERE = Path(__file__).resolve().parent
default_handler = chat_providers.default_handler


# pylint: disable=E1101
class Command(BaseCommand):
    """
    Django manage.py seed_chat_history.py command.
    This command is used to seed the chat history and audit tables.
    This is only used for local development and testing purposes.
    This command secondarily is a run-time verification of the
    Chat, Chatbot, Plugin and function calling sub systems.
    """

    def handle(self, *args, **options):
        """
        Handle the command. This command is typically invoked as part
        of bootstrapping the local development environment. We need to
        be mindful of we are in the bootstrapping sequence. The
        smarter system account, admin user and profile are *SUPPOSED*
        to exist at this point, as well as the built-in example
        chatbot and plugins.
        """
        data_folder_path = os.path.join(HERE, "data", "*.json")

        account = Account.objects.get(account_number=SMARTER_ACCOUNT_NUMBER)
        if not account:
            raise ValueError(f"Account not found: {SMARTER_ACCOUNT_NUMBER}")

        user = get_cached_admin_user_for_account(account)
        if not user:
            raise ValueError(f"User not found for account: {account}")

        user_profile = get_cached_user_profile(account=account, user=user)
        if not user_profile:
            raise ValueError(f"User profile not found for account: {account} user: {user}")

        chatbot = ChatBot.objects.get(account=user_profile.account, name=SMARTER_EXAMPLE_CHATBOT_NAME)
        if not chatbot:
            raise ValueError(f"Chatbot not found {SMARTER_EXAMPLE_CHATBOT_NAME}")

        session_key = "seed_chat_history.py_" + secrets.token_urlsafe(16)
        chat, _ = Chat.objects.get_or_create(
            session_key=session_key,
            chatbot=chatbot,
            account=account,
            url="https://localhost:8000/seed-chat-history",
            ip_address="192.1.1.1",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
        )

        for file_path in glob.glob(data_folder_path):
            print("Processing file: ", file_path)
            with open(file_path, encoding="utf-8") as file:
                data = json.loads(file.read())
                plugins = ChatBotPlugin().plugins(chatbot=chatbot)
                if not plugins or len(plugins) == 0:
                    raise ValueError(
                        f"No plugins found for chatbot: {chatbot}. "
                        "Seeding the chat history is only useful if the Chatbot has "
                        "one or more plugins. Please check the ChatBotPlugin model."
                    )

                default_handler(chat=chat, plugins=plugins, user=user_profile.user, data=data)
                print("Chat history seeded.")
        print("Chat history seeding complete.")
