"""Create the ApiConnections of the managed vector database services: Pinecone, and Qdrant Cloud."""

import os
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
from smarter.lib import logging
from smarter.lib.django.management.base import SmarterCommand

logger = logging.getLogger(__name__)


class Command(SmarterCommand):
    """
    Django manage.py initialize_vectorstore_providers command.

    For each managed vector database service whose environment variables are set, it creates, or
    updates, a Secret with its API key, and an ApiConnection, owned by the Smarter admin, which the
    built-in Vectorstore manifests use:

    - Pinecone: ``PINECONE_API_KEY``. The ApiConnection ``pinecone``.
    - Qdrant Cloud: ``QDRANT_CLOUD_URL`` and ``QDRANT_CLOUD_API_KEY``. The ApiConnection ``qdrant_cloud``.

    A self-hosted Qdrant database needs neither: Smarter runs it, and generates its API key.
    """

    help = "Create the ApiConnections of Pinecone and Qdrant Cloud, from PINECONE_API_KEY, QDRANT_CLOUD_URL and QDRANT_CLOUD_API_KEY."

    def connection(
        self, user_profile: UserProfile, name: str, base_url: str, secret_name: str, api_key: str, description: str
    ) -> ApiConnection:
        """Create or update a Secret with an API key, and an ApiConnection that uses it."""
        secret = Secret.objects.filter(user_profile=user_profile, name=secret_name).first() or Secret(
            user_profile=user_profile, name=secret_name
        )
        secret.description = f"The API key of {description}."
        secret.encrypted_value = Secret.encrypt(api_key)
        secret.save()
        connection = ApiConnection.objects.filter(user_profile=user_profile, name=name).first() or ApiConnection(
            user_profile=user_profile, name=name
        )
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
        api_key_var: str,
        secret_name: str,
        description: str,
    ) -> None:
        api_key = os.environ.get(api_key_var)
        if not api_key or not url:
            self.stdout.write(self.style.WARNING(f"Skipped {description}: {api_key_var} is not set."))
            return
        self.connection(user_profile, name, url, secret_name, api_key, description)
        self.stdout.write(self.style.SUCCESS(f"Created the ApiConnection {name}, for {description}."))

    def handle(self, *args, **options):
        self.handle_begin()
        user_profile = smarter_cached_objects.smarter_admin_user_profile
        try:
            self.initialize(
                user_profile,
                PINECONE_CONNECTION_NAME,
                PINECONE_API_URL,
                "PINECONE_API_KEY",
                PINECONE_API_KEY_SECRET_NAME,
                "Pinecone",
            )
            self.initialize(
                user_profile,
                QDRANT_CLOUD_CONNECTION_NAME,
                os.environ.get("QDRANT_CLOUD_URL"),
                "QDRANT_CLOUD_API_KEY",
                QDRANT_CLOUD_API_KEY_SECRET_NAME,
                "Qdrant Cloud",
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.handle_completed_failure(exc, f"initialize_vectorstore_providers: {exc}")
            return
        self.handle_completed_success()
