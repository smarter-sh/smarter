"""Test manage.py initialize_vectorstore_providers: :mod:`smarter.apps.vectorstore.management.commands.initialize_vectorstore_providers`."""

import os
from io import StringIO
from unittest.mock import MagicMock, patch

from smarter.apps.vectorstore.const import (
    PINECONE_API_KEY_SECRET_NAME,
    PINECONE_API_URL,
    PINECONE_CONNECTION_NAME,
)
from smarter.apps.vectorstore.management.commands.initialize_vectorstore_providers import (
    Command,
)
from smarter.lib.unittest.base_classes import SmarterTestBase

VARIABLES = (
    "APP_VECTORSTORE_PINECONE_API_KEY",
    "SMARTER_APP_VECTORSTORE_PINECONE_API_KEY",
    "APP_VECTORSTORE_QDRANT_CLOUD_URL",
    "SMARTER_APP_VECTORSTORE_QDRANT_CLOUD_URL",
    "APP_VECTORSTORE_QDRANT_CLOUD_API_KEY",
    "SMARTER_APP_VECTORSTORE_QDRANT_CLOUD_API_KEY",
)


class TestInitializeVectorstoreProviders(SmarterTestBase):
    """Each managed service's ApiConnection is created from its environment variables, or skipped."""

    def setUp(self):
        super().setUp()
        self.command = Command(stdout=StringIO(), stderr=StringIO())
        environ = patch.dict(os.environ, {})
        environ.start()
        self.addCleanup(environ.stop)
        for name in VARIABLES:
            os.environ.pop(name, None)
        connection = patch.object(Command, "connection")
        self.connection = connection.start()
        self.addCleanup(connection.stop)

    def initialize_pinecone(self, user_profile: MagicMock) -> None:
        self.command.initialize(
            user_profile,
            PINECONE_CONNECTION_NAME,
            PINECONE_API_URL,
            "APP_VECTORSTORE_PINECONE_API_KEY",
            PINECONE_API_KEY_SECRET_NAME,
            "Pinecone",
        )

    def test_the_smarter_prefixed_variable(self):
        """SMARTER_APP_VECTORSTORE_PINECONE_API_KEY, the Helm chart's name, is read, and the Secret keeps its name."""
        user_profile = MagicMock()
        os.environ["SMARTER_APP_VECTORSTORE_PINECONE_API_KEY"] = "pinecone-key"
        self.initialize_pinecone(user_profile)
        self.connection.assert_called_once_with(
            user_profile,
            PINECONE_CONNECTION_NAME,
            PINECONE_API_URL,
            PINECONE_API_KEY_SECRET_NAME,
            "pinecone-key",
            "Pinecone",
        )

    def test_a_missing_key_is_skipped(self):
        """No key, a .env.example placeholder, or the Helm chart's, creates nothing, and says which variable."""
        for value in (None, "SET-ME-PLEASE", "SET-ME-IN-helm/charts/smarter/values.yaml"):
            with self.subTest(value=value):
                os.environ.pop("APP_VECTORSTORE_PINECONE_API_KEY", None)
                if value:
                    os.environ["APP_VECTORSTORE_PINECONE_API_KEY"] = value
                self.initialize_pinecone(MagicMock())
                self.connection.assert_not_called()
        self.assertIn("APP_VECTORSTORE_PINECONE_API_KEY is not set", self.command.stdout.getvalue())  # type: ignore[attr-defined]

    def test_qdrant_cloud_reads_its_url(self):
        """The Qdrant Cloud url is APP_VECTORSTORE_QDRANT_CLOUD_URL, with the optional SMARTER_ prefix too."""
        os.environ["SMARTER_APP_VECTORSTORE_QDRANT_CLOUD_URL"] = "https://qdrant.example.test"
        os.environ["APP_VECTORSTORE_QDRANT_CLOUD_API_KEY"] = "qdrant-key"
        with (
            patch(
                "smarter.apps.vectorstore.management.commands.initialize_vectorstore_providers.smarter_cached_objects"
            ),
            patch.object(Command, "initialize", wraps=self.command.initialize) as initialize,
        ):
            self.command.handle()
        urls = [call.args[2] for call in initialize.call_args_list]
        self.assertIn("https://qdrant.example.test", urls)
        self.assertEqual(self.connection.call_args.args[4], "qdrant-key")
