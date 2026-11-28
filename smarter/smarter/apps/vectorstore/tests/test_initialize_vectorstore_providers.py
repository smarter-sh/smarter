"""Test manage.py initialize_vectorstore_providers: :mod:`smarter.apps.vectorstore.management.commands.initialize_vectorstore_providers`."""

import os
from io import StringIO
from unittest.mock import MagicMock, patch

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.secret.models import Secret
from smarter.apps.vectorstore.const import (
    PINECONE_API_KEY_SECRET_NAME,
    PINECONE_API_URL,
    PINECONE_CONNECTION_NAME,
    QDRANT_CLOUD_API_KEY_SECRET_NAME,
)
from smarter.apps.vectorstore.management.commands.initialize_vectorstore_providers import (
    Command,
)

MODULE = "smarter.apps.vectorstore.management.commands.initialize_vectorstore_providers"


class TestInitializeVectorstoreProviders(TestAccountMixin):
    """Each managed service's ApiConnection uses its API key Secret, or is skipped; no key is read from the environment."""

    def setUp(self):
        super().setUp()
        self.command = Command(stdout=StringIO(), stderr=StringIO())
        connection = patch.object(Command, "connection")
        self.connection = connection.start()
        self.addCleanup(connection.stop)

    def admin_secret(self, name: str) -> Secret:
        """Create one of the test account's Secrets, deleted when the test ends."""
        secret = Secret.objects.create(name=name, user_profile=self.user_profile, encrypted_value=Secret.encrypt("k"))
        self.addCleanup(Secret.objects.filter(pk=secret.pk).delete)
        return secret

    def initialize_pinecone(self) -> None:
        self.command.initialize(
            self.user_profile,
            PINECONE_CONNECTION_NAME,
            PINECONE_API_URL,
            PINECONE_API_KEY_SECRET_NAME,
            "Pinecone",
        )

    def test_the_connection_uses_the_secret(self):
        """The ApiConnection is created with the Secret that holds its key, which keeps its name."""
        secret = self.admin_secret(PINECONE_API_KEY_SECRET_NAME)
        self.initialize_pinecone()
        self.connection.assert_called_once_with(
            self.user_profile, PINECONE_CONNECTION_NAME, PINECONE_API_URL, secret, "Pinecone"
        )

    def test_a_missing_secret_is_skipped(self):
        """Without its Secret, nothing is created, whatever the environment holds, and the Secret is named."""
        with patch.dict(os.environ, {"SMARTER_APP_VECTORSTORE_PINECONE_API_KEY": "pinecone-key"}):
            self.initialize_pinecone()
        self.connection.assert_not_called()
        self.assertIn(f"its Secret {PINECONE_API_KEY_SECRET_NAME}", self.command.stdout.getvalue())  # type: ignore[attr-defined]

    def test_qdrant_cloud_reads_its_url(self):
        """The Qdrant Cloud url, which isn't a credential, is APP_VECTORSTORE_QDRANT_CLOUD_URL, with the optional SMARTER_ prefix."""
        self.admin_secret(QDRANT_CLOUD_API_KEY_SECRET_NAME)
        with (
            patch.dict(os.environ, {"SMARTER_APP_VECTORSTORE_QDRANT_CLOUD_URL": "https://qdrant.example.test"}),
            patch(f"{MODULE}.smarter_cached_objects", MagicMock(smarter_admin_user_profile=self.user_profile)),
            patch.object(Command, "initialize", wraps=self.command.initialize) as initialize,
        ):
            self.command.handle()
        urls = [call.args[2] for call in initialize.call_args_list]
        self.assertIn("https://qdrant.example.test", urls)
        secret = self.connection.call_args.args[3]
        self.assertEqual(secret.name, QDRANT_CLOUD_API_KEY_SECRET_NAME)
