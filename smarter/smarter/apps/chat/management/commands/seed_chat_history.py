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
from smarter.apps.chat.providers.langchain import handler
from smarter.apps.chatbot.models import ChatBot, ChatBotPlugin
from smarter.common.conf import settings as smarter_settings
from smarter.common.const import SMARTER_ACCOUNT_NUMBER, SMARTER_EXAMPLE_CHATBOT_NAME


HERE = Path(__file__).resolve().parent


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

        user = account_admin_user(account)
        if not user:
            raise ValueError(f"User not found for account: {account}")

        user_profile = UserProfile.objects.get(account=account, user=user)
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

                # send this text prompt to the Smarter chatbot provider
                handler(
                    chat=chat,
                    plugins=plugins,
                    user=user_profile.user,
                    data=data,
                    llm_vendor=chatbot.llm_vendor,
                    default_system_role=smarter_settings.openai_default_system_role,
                    default_temperature=smarter_settings.openai_default_temperature,
                    default_max_tokens=smarter_settings.openai_default_max_tokens,
                )
