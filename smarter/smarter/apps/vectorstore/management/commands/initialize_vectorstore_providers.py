"""Create the ApiConnections of the managed vector database services: Pinecone, and Qdrant Cloud."""

from typing import Optional

from smarter.apps.account.models import UserProfile
from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.connection.models import ApiConnection
from smarter.apps.secret.models import Secret
from smarter.apps.vectorstore.const import (
    PINECONE_API_KEY_SECRET_NAME,
    PINECONE_API_URL,
    PINECONE_CONNECTION_NAME,
    QDRANT_CLOUD_API_KEY_SECRET_NAME,
    QDRANT_CLOUD_CONNECTION_NAME,
)
from smarter.common.conf.env import get_env, is_missing_value
from smarter.lib import logging
from smarter.lib.django.management.base import SmarterCommand

logger = logging.getSmarterLogger(__name__)


class Command(SmarterCommand):
    """
    Django manage.py initialize_vectorstore_providers command.

    For each managed vector database service whose API key Secret exists, it creates, or updates, an
    ApiConnection that uses it, owned by the Smarter admin, which the built-in Vectorstore manifests use:

    - Pinecone: the Secret ``pinecone_api_key``. The ApiConnection ``pinecone``.
    - Qdrant Cloud: the Secret ``qdrant_cloud_api_key``, and ``APP_VECTORSTORE_QDRANT_CLOUD_URL``. The
      ApiConnection ``qdrant_cloud``.

    Each key's only source is its Secret (issue #1099), which ``initialize_bootstrap_secrets`` creates from the
    platform's bootstrap secrets, before this command runs.

    A self-hosted Qdrant database needs neither: Smarter runs it, and generates its API key.
    """

    help = "Create the ApiConnections of Pinecone and Qdrant Cloud, from their api key Secrets and APP_VECTORSTORE_QDRANT_CLOUD_URL."

    def connection(
        self, user_profile: UserProfile, name: str, base_url: str, secret: Secret, description: str
    ) -> ApiConnection:
        """
        Create or update an ApiConnection that uses an API key Secret.

        :param user_profile: The owner.
        :param name: The ApiConnection's name.
        :param base_url: The provider's API url.
        :param secret: The Secret that holds the API key.
        :param description: The provider's name, e.g. ``Pinecone``.
        :returns: The ApiConnection.
        """
        connection = ApiConnection.objects.filter(user_profile=user_profile, name=name).first()
        if connection is None:
            connection = ApiConnection(user_profile=user_profile, name=name)
        connection.kind = SAMKinds.API_CONNECTION.value
        connection.description = description
        connection.base_url = base_url
        connection.api_key = secret
        connection.auth_method = "token"
        connection.save()
        return connection

    def initialize(
        self,
        user_profile: UserProfile,
        name: str,
        url: Optional[str],
        secret_name: str,
        description: str,
    ) -> None:
        """
        Create the ApiConnection of a provider, if its API key's Secret exists and its url is set.

        The key's only source is its Secret (issue #1099), which ``initialize_bootstrap_secrets`` creates from the
        platform's bootstrap secrets, or an admin sets in the web console or with ``smarter apply``.

        :param user_profile: The owner, the platform's admin.
        :param name: The ApiConnection's name.
        :param url: The provider's API url, or None.
        :param secret_name: The name of the Secret that holds the API key.
        :param description: The provider's name, e.g. ``Pinecone``.
        """
        secret = Secret.objects.filter(user_profile=user_profile, name=secret_name).first()
        if secret is None or url is None or is_missing_value(url):
            self.stdout.write(
                self.style.WARNING(f"Skipped {description}: its Secret {secret_name}, or its url, is not set.")
            )
            return
        self.connection(user_profile, name, url, secret, description)
        self.stdout.write(self.style.SUCCESS(f"Created the ApiConnection {name}, for {description}."))

    def handle(self, *args, **options):
        """
        Create the ApiConnections of Pinecone and Qdrant Cloud, skipping each whose environment is not set.

        :param args: Unused.
        :param options: Unused.
        """
        self.handle_begin()
        user_profile = smarter_cached_objects.smarter_admin_user_profile
        try:
            self.initialize(
                user_profile,
                PINECONE_CONNECTION_NAME,
                PINECONE_API_URL,
                PINECONE_API_KEY_SECRET_NAME,
                "Pinecone",
            )
            self.initialize(
                user_profile,
                QDRANT_CLOUD_CONNECTION_NAME,
                get_env("APP_VECTORSTORE_QDRANT_CLOUD_URL", default=None),
                QDRANT_CLOUD_API_KEY_SECRET_NAME,
                "Qdrant Cloud",
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.handle_completed_failure(exc, f"initialize_vectorstore_providers: {exc}")
            return
        self.handle_completed_success()
