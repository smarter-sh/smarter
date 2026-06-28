"""Initialize Smarter vectorstore providers."""

import logging
from pathlib import Path

from pydantic import SecretStr

from smarter.apps.account.models import UserProfile
from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.secret.models import Secret
from smarter.apps.vectorstore.const import PINECONE_API_KEY_SECRET_NAME
from smarter.common.conf.const import get_env
from smarter.lib.django.management.base import SmarterCommand

logger = logging.getLogger(__name__)

HERE = Path(__file__).resolve().parent


class Command(SmarterCommand):
    """
    Django manage.py initialize_providers.py command.

    This command is used to create/update the principal
    vectorstore providers that are preloaded on all platforms.

    This runs during deployment.
    """

    user_profile: UserProfile

    def initialize_pinecone(self):
        """Initialize Pinecone provider."""
        API_KEY_ENV_VAR = "PINECONE_API_KEY"

        logger.info("initialize_pinecone")
        if self.user_profile is None:
            self.stdout.write(self.style.ERROR("initialize_pinecone: User profile is not set."))
            return

        secret_string = SecretStr(get_env(API_KEY_ENV_VAR, is_secret=True, is_required=True))
        if not secret_string or not secret_string.get_secret_value():
            self.stdout.write(
                self.style.WARNING(
                    f"initialize_pinecone: {API_KEY_ENV_VAR} is not set. Cannot initialize Pinecone provider."
                    f"Get your API key from https://www.pinecone.io/start/ and add it to your .env file as {API_KEY_ENV_VAR}."
                )
            )
            return

        Secret.objects.update_or_create(
            name=PINECONE_API_KEY_SECRET_NAME,
            encrypted_value=Secret.encrypt(secret_string.get_secret_value()),
            defaults={
                "description": "API key for Pinecone services.",
                "user_profile": self.user_profile,
            },
        )

    def handle(self, *args, **options):
        """Initialize all built-in providers."""
        self.handle_begin()

        try:
            self.user_profile = smarter_cached_objects.smarter_admin_user_profile
            self.initialize_pinecone()
        # pylint: disable=broad-except
        except Exception as exc:
            self.handle_completed_failure(msg=f"initialize_providers: Error initializing providers: {exc}")
            return

        self.handle_completed_success()
