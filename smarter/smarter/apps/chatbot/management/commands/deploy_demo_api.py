"""This module is used to initialize the environment."""

from django.core.management.base import BaseCommand

from smarter.apps.account.models import Account, SmarterAuthToken
from smarter.apps.account.utils import account_admin_user
from smarter.apps.chatbot.models import ChatBot, ChatBotAPIKey, ChatBotPlugin
from smarter.apps.chatbot.tasks import deploy_default_api
from smarter.apps.plugin.plugin import Plugins
from smarter.common.const import SMARTER_ACCOUNT_NUMBER, SMARTER_DEMO_API_NAME


# pylint: disable=E1101
class Command(BaseCommand):
    """Deploy the Smarter demo API."""

    def handle(self, *args, **options):
        log_prefix = "manage.py deploy_demo_api:"
        print(log_prefix, "Deploying the Smarter demo API...")

        account = Account.objects.get(account_number=SMARTER_ACCOUNT_NUMBER)
        user = account_admin_user(account)
        chatbot, _ = ChatBot.objects.get_or_create(account=account, name=SMARTER_DEMO_API_NAME)

        if chatbot.deployed:
            print(log_prefix, "The Smarter demo API is already deployed.")
            return

        for plugin in Plugins(account=account).plugins:
            ChatBotPlugin.objects.create(chatbot=chatbot, plugin_meta=plugin.plugin_meta)

        deploy_default_api.delay(chatbot_id=chatbot.id)

        # Add an api key, if we have one for the Smarter account
        try:
            api_key = SmarterAuthToken.objects.filter(account=account, user=user).order_by("pk").first()
            ChatBotAPIKey.objects.create(chatbot=chatbot, api_key=api_key)
        except SmarterAuthToken.DoesNotExist:
            pass
