"""Store the api keys of the llmtool app's plugins as Secrets: Tavily's, for web search, and Brave Search's."""

from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.llmtool.const import (
    BRAVE_SEARCH_API_KEY_SECRET_NAME,
    TAVILY_API_KEY_SECRET_NAME,
)
from smarter.apps.secret.models import Secret
from smarter.common.helpers.console_helpers import SmarterFormattedText
from smarter.lib import logging
from smarter.lib.django.management.base import SmarterCommand

logger = logging.getSmarterLogger(__name__)

API_KEYS = (
    (
        TAVILY_API_KEY_SECRET_NAME,
        "Tavily web search",
        "web search: WebsearchPlugins such as smarter_project_websearch",
        "https://app.tavily.com/home",
    ),
    (
        BRAVE_SEARCH_API_KEY_SECRET_NAME,
        "Brave Search",
        "image and web search: ImageSearchPlugins such as safe_image_search, and the Brave WebsearchPlugin samples",
        "https://api-dashboard.search.brave.com/app/keys",
    ),
)
"""The llmtool app's api keys: for each, its Smarter Secret, its service, what uses it, and where to get one."""


class Command(SmarterCommand):
    """
    Django manage.py initialize_llmtool_api_keys command.

    Reports which of the llmtool app's api key Secrets, the Smarter admin's, don't exist, which the plugins read
    their key from:

    - ``tavily_api_key``, for WebsearchPlugins whose search provider is Tavily, such as the sample
      smarter_project_websearch.
    - ``brave_search_api_key``, for ImageSearchPlugins such as safe_image_search, and the Brave WebsearchPlugin
      samples.

    Each key's only source is its Secret (issue #1099): ``initialize_bootstrap_secrets`` creates it from the
    platform's bootstrap secrets, which ``initialize_platform`` runs before this, or an admin sets it in the web
    console or with ``smarter apply``. Applying a plugin whose Secret doesn't exist reports the missing Secret.
    """

    help = "Report which of the Tavily and Brave Search api key Secrets do not exist."

    def handle(self, *args, **options):
        """
        Log one banner for the api key Secrets that don't exist.

        :param args: Unused.
        :param options: Unused.
        """
        self.handle_begin()
        user_profile = smarter_cached_objects.smarter_admin_user_profile
        missing = []
        for secret_name, _service, used_for, url in API_KEYS:
            if Secret.objects.filter(name=secret_name, user_profile=user_profile).exists():
                self.stdout.write(self.style.SUCCESS(f"The Secret {secret_name} exists."))
                continue
            self.stdout.write(
                self.style.WARNING(f"The Secret {secret_name} does not exist. It is used for {used_for}.")
            )
            missing.append(f"  {secret_name}, for {used_for}: get a key at {url}")
        if missing:
            logger.error(
                SmarterFormattedText.banner(
                    f"[API KEYS NOT SET] {len(missing)} llmtool api key Secrets do not exist:",
                    *missing,
                    "",
                    "The plugins that use them fail, with an error, until they are set. Set each Secret in the web",
                    "console or with smarter apply, or add it to the platform's bootstrap secrets: the Helm chart's",
                    "bootstrapSecrets, or, locally, a file of that name in bootstrap-secrets/ (make bootstrap-secrets).",
                )
            )
        self.handle_completed_success()
