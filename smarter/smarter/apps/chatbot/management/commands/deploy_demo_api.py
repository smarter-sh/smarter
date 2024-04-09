# -*- coding: utf-8 -*-
"""This module is used to initialize the environment."""

from django.core.management.base import BaseCommand

from smarter.apps.account.models import Account
from smarter.apps.chatbot.models import ChatBot, ChatBotPlugins
from smarter.apps.chatbot.tasks import deploy_default_api
from smarter.apps.plugin.plugin import Plugins
from smarter.common.const import SMARTER_COMPANY_NAME, SMARTER_DEMO_API_NAME


# pylint: disable=E1101
class Command(BaseCommand):
    """Deploy the Smarter demo API."""

    def handle(self, *args, **options):
        log_prefix = "manage.py deploy_demo_api:"
        print(log_prefix, "Deploying the Smarter demo API...")

        account = Account.objects.get(company_name=SMARTER_COMPANY_NAME)
        chatbot, _ = ChatBot.objects.get_or_create(account=account, name=SMARTER_DEMO_API_NAME)

        if chatbot.deployed:
            print(log_prefix, "The Smarter demo API is already deployed.")
            return

        for plugin in Plugins(account=account).plugins:
            ChatBotPlugins.objects.create(chatbot=chatbot, plugin_meta=plugin.plugin_meta)

        deploy_default_api.delay(chatbot_id=chatbot.id)
