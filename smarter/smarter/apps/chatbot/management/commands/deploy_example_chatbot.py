"""This module is used to initialize the environment."""

from smarter.apps.account.models import Account, UserProfile
from smarter.apps.account.utils import get_cached_admin_user_for_account
from smarter.apps.chatbot.models import ChatBot, ChatBotPlugin
from smarter.apps.chatbot.tasks import deploy_default_api
from smarter.apps.plugin.models import PluginMeta
from smarter.common.conf import SettingsDefaults
from smarter.common.const import SMARTER_ACCOUNT_NUMBER, SMARTER_EXAMPLE_CHATBOT_NAME
from smarter.lib.django.management.base import SmarterCommand


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
        parser.add_argument("--foreground", action="store_true", help="Run the task in the foreground")

    def handle(self, *args, **options):
        """Deploy the Smarter demo ChatBot."""

        self.handle_begin()

        foreground = options["foreground"] if "foreground" in options else False

        log_prefix = "manage.py deploy_example_chatbot:"
        self.stdout.write(self.style.NOTICE(log_prefix + "Deploying the Smarter demo API..."))

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
        chatbot.app_logo_url = "https://cdn.platform.smarter.sh/images/logo/smarter-crop.png"
        chatbot.save()

        if chatbot.deployed and chatbot.dns_verification_status == ChatBot.DnsVerificationStatusChoices.VERIFIED:
            self.handle_completed_success(msg=f"The Smarter demo API is already deployed.")
            return

        for plugin_meta in PluginMeta.objects.filter(account=user_profile.account):
            if plugin_meta.name in ["everlasting_gobstopper", "example_configuration"]:
                if not ChatBotPlugin.objects.filter(chatbot=chatbot, plugin_meta=plugin_meta).exists():
                    ChatBotPlugin.objects.create(chatbot=chatbot, plugin_meta=plugin_meta)

        if foreground:
            deploy_default_api(chatbot_id=chatbot.id)
        else:
            self.stdout.write(self.style.NOTICE(log_prefix + "Deploying example api as a Celery task."))
            deploy_default_api.delay(chatbot_id=chatbot.id)
            self.handle_completed_success(msg=f"Deployment of the Smarter demo API has been initiated.")
            return

        self.handle_completed_success()
