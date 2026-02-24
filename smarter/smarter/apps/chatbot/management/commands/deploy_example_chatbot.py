"""This module is used to initialize the environment."""

import logging

from smarter.apps.account.models import Account, UserProfile
from smarter.apps.account.utils import get_cached_admin_user_for_account
from smarter.apps.chatbot.models import ChatBot, ChatBotPlugin
from smarter.apps.chatbot.tasks import deploy_default_api
from smarter.apps.plugin.models import PluginMeta
from smarter.common.conf import SettingsDefaults
from smarter.common.const import SMARTER_ACCOUNT_NUMBER, SMARTER_EXAMPLE_CHATBOT_NAME
from smarter.lib.django.management.base import SmarterCommand

logger = logging.getLogger(__name__)


# pylint: disable=E1101
class Command(SmarterCommand):
    """
    Deploy the Smarter demo ChatBot for demonstration and testing purposes.

    This management command provisions and deploys a pre-configured demo chatbot for the Smarter platform.
    It is intended to showcase platform features and provide a ready-to-use example for evaluation or onboarding.

    The command performs the following actions:
      - Retrieves the demo account and its admin user.
      - Ensures the demo chatbot exists, creating it if necessary.
      - Sets default provider, model, system role, temperature, and token limits for the chatbot.
      - Configures demo-specific application metadata, such as name, assistant, welcome message, example prompts, and branding.
      - Attaches example plugins to the chatbot if they are available for the account.
      - Initiates deployment of the chatbot, either synchronously (foreground) or asynchronously (Celery task).
      - Reports deployment status and completion.

    The deployed demo chatbot is accessible via a public URL and is configured to demonstrate typical user interactions,
    plugin integration, and platform branding. This command is useful for quickly setting up a showcase environment
    or verifying platform functionality.
    """

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("--account_number", type=str, help="The account number for the demo chatbot.")
        parser.add_argument("--foreground", action="store_true", help="Run the task in the foreground")

    def handle(self, *args, **options):
        """Deploy the Smarter demo ChatBot."""

        self.handle_begin()

        foreground = options["foreground"]
        account_number = options.get("account_number") or SMARTER_ACCOUNT_NUMBER

        log_prefix = "manage.py deploy_example_chatbot:"
        self.stdout.write(self.style.NOTICE(log_prefix + "Deploying the Smarter demo API..."))

        try:
            account = Account.objects.get(account_number=account_number)
        except Account.DoesNotExist:
            logger.error("Account with account number '%s' does not exist.", account_number)
            self.handle_completed_failure()
            return
        user = get_cached_admin_user_for_account(account)
        user_profile, _ = UserProfile.objects.get_or_create(user=user, account=account)
        chatbot, _ = ChatBot.objects.get_or_create(user_profile=user_profile, name=SMARTER_EXAMPLE_CHATBOT_NAME)
        chatbot.provider = SettingsDefaults.LLM_DEFAULT_PROVIDER
        chatbot.default_model = SettingsDefaults.LLM_DEFAULT_MODEL
        chatbot.default_system_role = SettingsDefaults.LLM_DEFAULT_SYSTEM_ROLE
        chatbot.default_temperature = SettingsDefaults.LLM_DEFAULT_TEMPERATURE
        chatbot.default_max_tokens = SettingsDefaults.LLM_DEFAULT_MAX_TOKENS

        chatbot.app_name = "Smarter Demo"
        chatbot.app_assistant = "Lawrence"
        chatbot.app_welcome_message = "Welcome to the Smarter demo!"
        chatbot.app_example_prompts = [
            "What is the weather in San Francisco?",
            "What is an Everlasting Gobstopper?",
            "example function calling configuration",
        ]
        chatbot.app_placeholder = "Ask me anything..."
        chatbot.app_info_url = "https://smarter.sh"
        chatbot.app_background_image_url = None
        chatbot.app_logo_url = "https://cdn.smarter.sh/images/logo/smarter-crop.png"
        chatbot.save()

        for plugin_meta in PluginMeta.objects.filter(user_profile=user_profile):
            if plugin_meta.name in ["everlasting_gobstopper", "example_configuration"]:
                if not ChatBotPlugin.objects.filter(chatbot=chatbot, plugin_meta=plugin_meta).exists():
                    ChatBotPlugin.objects.create(chatbot=chatbot, plugin_meta=plugin_meta)

        chatbot.deployed = True
        if foreground:
            chatbot.save()
        else:
            chatbot.save(asynchronous=True)

        self.handle_completed_success()
