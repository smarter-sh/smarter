"""This module is used to initialize the environment."""

import logging

from smarter.apps.account.models import Account, UserProfile
from smarter.apps.account.utils import get_cached_admin_user_for_account
from smarter.apps.llm_client.models import LLMClient, LLMClientPlugin
from smarter.apps.plugin.models import PluginMeta
from smarter.common.conf import settings_defaults
from smarter.common.const import SMARTER_ACCOUNT_NUMBER, SMARTER_EXAMPLE_LLM_CLIENT_NAME
from smarter.lib.django.management.base import SmarterCommand

logger = logging.getLogger(__name__)


# pylint: disable=E1101
class Command(SmarterCommand):
    """
    Deploy the Smarter demo LLMClient for demonstration and testing purposes.

    This management command provisions and deploys a pre-configured demo llm_client for the Smarter platform.
    It is intended to showcase platform features and provide a ready-to-use example for evaluation or onboarding.

    The command performs the following actions:
      - Retrieves the demo account and its admin user.
      - Ensures the demo llm_client exists, creating it if necessary.
      - Sets default provider, model, system role, temperature, and token limits for the llm_client.
      - Configures demo-specific application metadata, such as name, assistant, welcome message, example prompts, and branding.
      - Attaches example plugins to the llm_client if they are available for the account.
      - Initiates deployment of the llm_client, either synchronously (foreground) or asynchronously (Celery task).
      - Reports deployment status and completion.

    The deployed demo llm_client is accessible via a public URL and is configured to demonstrate typical user interactions,
    plugin integration, and platform branding. This command is useful for quickly setting up a showcase environment
    or verifying platform functionality.
    """

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument(
            "--account_number",
            type=str,
            help="The account number for the demo llm_client.",
            default=SMARTER_ACCOUNT_NUMBER,
        )
        parser.add_argument("--foreground", action="store_true", help="Run the task in the foreground")

    def handle(self, *args, **options):
        """Deploy the Smarter demo LLMClient."""

        self.handle_begin()

        foreground = options["foreground"]
        account_number = options.get("account_number")

        log_prefix = "manage.py deploy_example_llm_client:"
        self.stdout.write(self.style.NOTICE(log_prefix + "Deploying the Smarter demo API..."))

        try:
            account = Account.objects.get(account_number=account_number)
        except Account.DoesNotExist:
            logger.error("Account with account number '%s' does not exist.", account_number)
            self.handle_completed_failure()
            return
        user = get_cached_admin_user_for_account(account=account)
        user_profile, _ = UserProfile.objects.get_or_create(user=user, account=account)
        llm_client, _ = LLMClient.objects.get_or_create(user_profile=user_profile, name=SMARTER_EXAMPLE_LLM_CLIENT_NAME)
        llm_client.provider = settings_defaults.LLM_DEFAULT_PROVIDER
        llm_client.default_model = settings_defaults.LLM_DEFAULT_MODEL
        llm_client.default_system_role = settings_defaults.LLM_DEFAULT_SYSTEM_ROLE
        llm_client.default_temperature = settings_defaults.LLM_DEFAULT_TEMPERATURE
        llm_client.default_max_tokens = settings_defaults.LLM_DEFAULT_MAX_TOKENS

        llm_client.app_name = "Smarter Demo"
        llm_client.app_assistant = "Lawrence"
        llm_client.app_welcome_message = "Welcome to the Smarter demo!"
        llm_client.app_example_prompts = [
            "What is the weather in San Francisco?",
            "What is an Everlasting Gobstopper?",
            "example function calling configuration",
        ]
        llm_client.app_placeholder = "Ask me anything..."
        llm_client.app_info_url = "https://smarter.sh"
        llm_client.app_background_image_url = None
        llm_client.app_logo_url = "https://cdn.smarter.sh/images/logo/smarter-crop.png"
        llm_client.save()

        for plugin_meta in PluginMeta.objects.filter(user_profile=user_profile):
            if plugin_meta.name in ["everlasting_gobstopper", "example_configuration"]:
                if not LLMClientPlugin.objects.filter(llm_client=llm_client, plugin_meta=plugin_meta).exists():
                    LLMClientPlugin.objects.create(llm_client=llm_client, plugin_meta=plugin_meta)

        llm_client.deployed = True
        if foreground:
            llm_client.save()
        else:
            llm_client.save(asynchronous=True)

        self.handle_completed_success()
