"""Store the api keys of the llmtool app's plugins as Secrets: Tavily's, for web search, and Brave Search's."""

from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.llmtool.const import (
    BRAVE_SEARCH_API_KEY_SECRET_NAME,
    TAVILY_API_KEY_SECRET_NAME,
)
from smarter.apps.provider.utils import initialize_secret
from smarter.common.conf.const import get_env
from smarter.common.conf.env import is_missing_value
from smarter.common.helpers.console_helpers import SmarterFormattedText
from smarter.lib import logging
from smarter.lib.django.management.base import SmarterCommand

logger = logging.getSmarterLogger(__name__)

API_KEYS = (
    (
        "APP_LLMTOOL_TAVILY_API_KEY",
        TAVILY_API_KEY_SECRET_NAME,
        "Tavily web search",
        "web search: WebsearchPlugins such as smarter_project_websearch",
        "https://app.tavily.com/home",
    ),
    (
        "APP_LLMTOOL_BRAVE_SEARCH_API_KEY",
        BRAVE_SEARCH_API_KEY_SECRET_NAME,
        "Brave Search",
        "image and web search: ImageSearchPlugins such as safe_image_search, and the Brave WebsearchPlugin samples",
        "https://api-dashboard.search.brave.com/app/keys",
    ),
)
"""
The llmtool app's api keys: for each, its environment variable without the optional ``SMARTER_``.

prefix, its Secret, its service, what uses it, and where to get one.
"""


class Command(SmarterCommand):
    """
    Django manage.py initialize_llmtool_api_keys command.

    For each of the llmtool app's api keys whose environment variable is set, it creates, or
    updates, a Secret, owned by the Smarter admin, which the plugins read their key from:

    - ``SMARTER_APP_LLMTOOL_TAVILY_API_KEY``: the Secret ``tavily_api_key``, for WebsearchPlugins whose
      search provider is Tavily, such as the sample smarter_project_websearch.
    - ``SMARTER_APP_LLMTOOL_BRAVE_SEARCH_API_KEY``: the Secret ``brave_search_api_key``, for
      ImageSearchPlugins such as safe_image_search, and the Brave WebsearchPlugin samples.

    A missing key, or a placeholder such as ``SET-ME-PLEASE``, is never stored: applying a plugin
    that needs it then reports the missing Secret. ``initialize_platform`` runs it before the
    example manifests, whose plugins name these Secrets.
    """

    help = "Store the Tavily and Brave Search api keys, SMARTER_APP_LLMTOOL_TAVILY_API_KEY and SMARTER_APP_LLMTOOL_BRAVE_SEARCH_API_KEY, as Secrets."

    def initialize(self, env_var: str, secret_name: str, service: str, used_for: str, url: str) -> bool:
        """
        Store one api key as a Secret, if its environment variable is set.

        :param env_var: The environment variable, without the optional ``SMARTER_`` prefix.
        :param secret_name: The Secret's name.
        :param service: The service's name, for the Secret's description.
        :param used_for: What uses the key, for the warning when it is not set.
        :param url: Where to get a key.
        :returns: True if the Secret was stored, False if the key is not set.
        """
        api_key = get_env(env_var, "", is_secret=True)
        if is_missing_value(api_key):
            self.stdout.write(self.style.WARNING(f"{env_var} is not set. It is used for {used_for}. Get one at {url}"))
            return False
        initialize_secret(
            secret_string=api_key,
            secret_name=secret_name,
            description=f"API key for {service}.",
            user_profile=smarter_cached_objects.smarter_admin_user_profile,
        )
        self.stdout.write(self.style.SUCCESS(f"Stored the Secret {secret_name}, from {env_var}."))
        return True

    def handle(self, *args, **options):
        """
        Store each of the llmtool app's api keys that is set, and log one banner for those that are not.

        :param args: Unused.
        :param options: Unused.
        """
        self.handle_begin()
        missing = []
        try:
            for env_var, secret_name, service, used_for, url in API_KEYS:
                if not self.initialize(env_var, secret_name, service, used_for, url):
                    missing.append(f"  SMARTER_{env_var}, for {used_for}")
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.handle_completed_failure(exc, f"initialize_llmtool_api_keys: {exc}")
            return
        if missing:
            logger.error(
                SmarterFormattedText.banner(
                    f"[API KEYS NOT SET] {len(missing)} llmtool api keys are not set:",
                    *missing,
                    "",
                    "The plugins that use them fail, with an error, until they are set. Add them to .env,",
                    "restart the platform, and run:",
                    "",
                    "    docker exec smarter-api python manage.py initialize_llmtool_api_keys",
                )
            )
        self.handle_completed_success()
