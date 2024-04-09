# -*- coding: utf-8 -*-
"""This module is used to generate seed records for the chat history models."""

import glob
import json
import os
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from smarter.apps.account.models import UserProfile
from smarter.apps.chat.providers.smarter import handler
from smarter.apps.chatbot.models import ChatBot, ChatBotPlugins
from smarter.common.const import SMARTER_DEMO_API_NAME


User = get_user_model()
HERE = Path(__file__).resolve().parent


# pylint: disable=E1101
class Command(BaseCommand):
    """Django manage.py get_plugins command. This command is used to generate a JSON list of all accounts."""

    def handle(self, *args, **options):
        data_folder_path = os.path.join(HERE, "data", "*.json")
        user_profile = UserProfile.objects.filter(user__username="admin").first()
        chatbot = ChatBot.objects.get(account=user_profile.account, name=SMARTER_DEMO_API_NAME)

        for file_path in glob.glob(data_folder_path):
            print("Processing file: ", file_path)
            with open(file_path, "r", encoding="utf-8") as file:
                data = json.loads(file.read())
                plugins = ChatBotPlugins().plugins(chatbot=chatbot)
                handler(plugins=plugins, user=user_profile.user, data=data)
