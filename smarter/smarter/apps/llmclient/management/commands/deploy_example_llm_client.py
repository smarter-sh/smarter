"""This module is used to initialize the environment."""

from smarter.apps.account.models import Account, UserProfile
from smarter.apps.account.utils import get_cached_admin_user_for_account
from smarter.apps.llmclient.models import LLMClient, LLMClientPlugin
from smarter.apps.plugin.models import PluginMeta
from smarter.common.conf import settings_defaults
from smarter.common.const import SMARTER_ACCOUNT_NUMBER, SMARTER_EXAMPLE_LLM_CLIENT_NAME
from smarter.lib import logging
from smarter.lib.django.management.base import SmarterCommand

logger = logging.getLogger(__name__)


# pylint: disable=E1101
class Command(SmarterCommand):
    """
    Deploy the Smarter demo LLMClient for demonstration and testing purposes.

    This management command provisions and deploys a pre-configured demo llmclient for the Smarter platform.
    It is intended to showcase platform features and provide a ready-to-use example for evaluation or onboarding.

    The command performs the following actions:
      - Retrieves the demo account and its admin user.
      - Ensures the demo llmclient exists, creating it if necessary.
      - Sets default provider, model, system role, temperature, and token limits for the llmclient.
      - Configures demo-specific application metadata, such as name, assistant, welcome message, example prompts, and branding.
      - Attaches example plugins to the llmclient if they are available for the account.
      - Initiates deployment of the llmclient, either synchronously (foreground) or asynchronously (Celery task).
      - Reports deployment status and completion.

    The deployed demo llmclient is accessible via a public URL and is configured to demonstrate typical user interactions,
    plugin integration, and platform branding. This command is useful for quickly setting up a showcase environment
    or verifying platform functionality.
    """

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument(
            "--account_number",
            type=str,
            help="The account number for the demo llmclient.",
            default=SMARTER_ACCOUNT_NUMBER,
        )
        parser.add_argument("--foreground", action="store_true", help="Run the task in the foreground")

    def handle(self, *args, **options):
        """Deploy the Smarter demo LLMClient."""

        self.handle_begin()

        foreground = options["foreground"]
        account_number = options.get("account_number")

        log_prefix = "manage.py deploy_example_llmclient:"
        self.stdout.write(self.style.NOTICE(log_prefix + "Deploying the Smarter demo API..."))

        try:
            account = Account.objects.get(account_number=account_number)
        except Account.DoesNotExist:
            logger.error("Account with account number '%s' does not exist.", account_number)
            self.handle_completed_failure()
            return
        user = get_cached_admin_user_for_account(account=account)
        user_profile, _ = UserProfile.objects.get_or_create(user=user, account=account)
        llmclient, _ = LLMClient.objects.get_or_create(user_profile=user_profile, name=SMARTER_EXAMPLE_LLM_CLIENT_NAME)
        llmclient.provider = settings_defaults.LLM_DEFAULT_PROVIDER
        llmclient.default_model = settings_defaults.LLM_DEFAULT_MODEL
        llmclient.default_system_role = settings_defaults.LLM_DEFAULT_SYSTEM_ROLE
        llmclient.default_temperature = settings_defaults.LLM_DEFAULT_TEMPERATURE
        llmclient.default_max_tokens = settings_defaults.LLM_DEFAULT_MAX_TOKENS

        llmclient.app_name = "Smarter Demo"
        llmclient.app_assistant = "Lawrence"
        llmclient.app_welcome_message = "Welcome to the Smarter demo!"
        llmclient.app_example_prompts = [
            "What is the weather in San Francisco?",
            "What is an Everlasting Gobstopper?",
            "example function calling configuration",
        ]
        llmclient.app_placeholder = "Ask me anything..."
        llmclient.app_info_url = "https://smarter.sh"
        llmclient.app_background_image_url = None
        llmclient.app_logo_url = "https://cdn.smarter.sh/images/logo/smarter-crop.png"
        llmclient.save()

        for plugin_meta in PluginMeta.objects.filter(user_profile=user_profile):
            if plugin_meta.name in ["everlasting_gobstopper", "example_configuration"]:
                if not LLMClientPlugin.objects.filter(llmclient=llmclient, plugin_meta=plugin_meta).exists():
                    LLMClientPlugin.objects.create(llmclient=llmclient, plugin_meta=plugin_meta)

        llmclient.deployed = True
        if foreground:
            llmclient.save()
        else:
            llmclient.save(asynchronous=True)

        self.handle_completed_success()
