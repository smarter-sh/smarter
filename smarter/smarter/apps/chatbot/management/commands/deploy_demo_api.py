# -*- coding: utf-8 -*-
"""This module is used to initialize the environment."""

from django.core.management.base import BaseCommand

from smarter.apps.account.models import Account
from smarter.apps.chatbot.models import ChatBot
from smarter.apps.chatbot.tasks import deploy_default_api
from smarter.common.const import SMARTER_COMPANY_NAME


# pylint: disable=E1101
class Command(BaseCommand):
    """Deploy the Smarter demo API."""

    def handle(self, *args, **options):
        log_prefix = "manage.py deploy_demo_api:"
        print(log_prefix, "Deploying the Smarter demo API...")

        account = Account.objects.get(company_name=SMARTER_COMPANY_NAME)
        chatbot, _ = ChatBot.objects.get_or_create(account=account, name="demo-api")

        deploy_default_api.delay(chatbot_id=chatbot.id)
