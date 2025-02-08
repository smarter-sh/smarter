"""This module is used to initialize the environment."""

from django.core.management.base import BaseCommand

from smarter.apps.account.models import Account, UserProfile
from smarter.apps.account.utils import get_cached_admin_user_for_account
from smarter.apps.chatbot.models import ChatBot, ChatBotPlugin
from smarter.apps.chatbot.tasks import deploy_default_api
from smarter.apps.plugin.models import PluginMeta
from smarter.common.conf import SettingsDefaults
from smarter.common.const import SMARTER_ACCOUNT_NUMBER, SMARTER_EXAMPLE_CHATBOT_NAME


# pylint: disable=E1101
class Command(BaseCommand):
    """Deploy the Smarter demo ChatBot."""

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("--foreground", action="store_true", help="Run the task in the foreground")

    def handle(self, *args, **options):
        foreground = options["foreground"]

        log_prefix = "manage.py deploy_example_chatbot:"
        print(log_prefix, "Deploying the Smarter demo API...")

        account = Account.objects.get(account_number=SMARTER_ACCOUNT_NUMBER)
        user = get_cached_admin_user_for_account(account)
        user_profile, _ = UserProfile.objects.get_or_create(user=user, account=account)
        chatbot, _ = ChatBot.objects.get_or_create(account=account, name=SMARTER_EXAMPLE_CHATBOT_NAME)
        chatbot.provider = SettingsDefaults.LLM_DEFAULT_PROVIDER
        chatbot.default_model = SettingsDefaults.LLM_DEFAULT_MODEL
        chatbot.default_system_role = SettingsDefaults.LLM_DEFAULT_SYSTEM_ROLE
        chatbot.default_temperature = SettingsDefaults.LLM_DEFAULT_TEMPERATURE
        chatbot.default_max_tokens = SettingsDefaults.LLM_DEFAULT_MAX_TOKENS

        chatbot.app_name = "Smarter Demo"
        chatbot.app_assistant = "Kent"
        chatbot.app_welcome_message = "Welcome to the Smarter demo!"
        chatbot.app_example_prompts = [
            "What is the weather in San Francisco?",
            "What is an Everlasting Gobstopper?",
            "example function calling configuration",
        ]
        chatbot.app_placeholder = "Ask me anything..."
        chatbot.app_info_url = "https://smarter.sh"
        chatbot.app_background_image_url = None
        chatbot.app_logo_url = "/static/querium/querium-logo-white-transparent.png"
        chatbot.save()

        if chatbot.deployed and chatbot.dns_verification_status == ChatBot.DnsVerificationStatusChoices.VERIFIED:
            self.stdout.write(self.style.SUCCESS(log_prefix + "The Smarter demo API is already deployed."))
            return

        for plugin_meta in PluginMeta.objects.filter(account=user_profile.account):
            if plugin_meta.name in ["EverlastingGobstopper", "ExampleConfiguration"]:
                if not ChatBotPlugin.objects.filter(chatbot=chatbot, plugin_meta=plugin_meta).exists():
                    ChatBotPlugin.objects.create(chatbot=chatbot, plugin_meta=plugin_meta)

        if foreground:
            deploy_default_api(chatbot_id=chatbot.id)
        else:
            self.stdout.write(self.style.NOTICE(log_prefix + "Deploying example api as a Celery task."))
            deploy_default_api.delay(chatbot_id=chatbot.id)
