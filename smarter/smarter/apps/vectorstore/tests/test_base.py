# pylint: disable=wrong-import-position
"""Vectorstore base test class."""

# python stuff
import logging

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.provider.models import Provider, ProviderModel
from smarter.apps.secret.models import Secret
from smarter.apps.vectorstore.models import (
    VectorestoreMeta,
    VectorstoreBackendKind,
    VectorstoreStatus,
)
from smarter.apps.vectorstore.service import VectorstoreService
from smarter.common.conf.settings import smarter_settings
from smarter.common.exceptions import SmarterConfigurationError
from smarter.common.helpers.logger_helpers import formatted_text

logger = logging.getLogger(__name__)
logger_prefix = formatted_text(f"{__name__}.VectorstoreTestBase()")


class VectorstoreTestBase(TestAccountMixin):
    """Base test class for Vectorstore"""

    password: Secret
    provider: Provider
    provider_model: ProviderModel
    vector_database: VectorestoreMeta
    vectorstore_service: VectorstoreService

    @classmethod
    def setUpClass(cls):
        """
        Setup the test class with common resources for all unit tests:
        - test VectorestoreMeta instance with Pinecone backend
        - test Secret instance for the vector database password
        - active OpenAI provider and a random active LLM with embedding support
        - VectorstoreService instance using the test VectorestoreMeta
        - connect the VectorstoreService backend to ensure it's ready for testing
        """
        super().setUpClass()

        logger.debug("Setting up VectorstoreTestBase class resources")

        try:
            cls.provider = Provider.objects.get(name="openai", is_active=True)
            logger.debug("%s.setUpClass() Found active OpenAI provider: %s", logger_prefix, cls.provider)
        except Provider.DoesNotExist as e:
            raise SmarterConfigurationError("Active OpenAI provider not found. Cannot setup vectorstore tests.") from e

        try:
            cls.provider_model = ProviderModel.objects.filter(provider=cls.provider, supports_embedding=True).first()  # type: ignore
            if cls.provider_model is None:
                raise ProviderModel.DoesNotExist()
            logger.debug(
                "%s.setUpClass() Found active OpenAI provider model with embedding support: %s",
                logger_prefix,
                cls.provider_model,
            )
        except ProviderModel.DoesNotExist as e:
            raise SmarterConfigurationError(
                "Active OpenAI provider model with embedding support not found. Cannot setup vectorstore tests."
            ) from e

        cls.password = Secret.objects.create(
            name="test_password",
            description="A test password",
            user_profile=cls.user_profile,
            value=smarter_settings.pinecone_api_key.get_secret_value(),
            is_active=True,
        )

        logger.debug("%s.setUpClass() Created test password secret: %s", logger_prefix, cls.password)

        cls.vector_database = VectorestoreMeta.objects.create(
            name="test_vector_database",
            description="A test vector database",
            user_profile=cls.user_profile,
            backend=VectorstoreBackendKind.PINECONE,
            host="test-pinecone-host",
            port=1234,
            auth_config={},
            password=cls.password,
            config={},
            is_active=True,
            status=VectorstoreStatus.PROVISIONING,
            provider=cls.provider,
            provider_model=cls.provider_model,
        )
        logger.debug("%s.setUpClass() Created test vector database: %s", logger_prefix, cls.vector_database)

        cls.vectorstore_service = VectorstoreService(db=cls.vector_database)
        logger.debug("%s.setUpClass() Created VectorstoreService instance: %s", logger_prefix, cls.vectorstore_service)

        cls.vectorstore_service.backend.connect()
        if cls.vectorstore_service.ready:
            logger.debug("%s.setUpClass() VectorstoreService backend is ready for testing.", logger_prefix)
        else:
            raise SmarterConfigurationError(
                "VectorstoreService backend is not ready for testing. Check backend connection and configuration."
            )

        logger.debug(
            "%s.setUpClass() Finished setting up VectorstoreTestBase class resources -- happy testing!", logger_prefix
        )

    @classmethod
    def tearDownClass(cls):
        """
        Prune the vector database and password secret created for testing.
        """
        try:
            cls.vector_database.delete()
        # pylint: disable=broad-except
        except Exception as e:
            logger.error("%s.tearDownClass() Error deleting vector database: %s", logger_prefix, e)

        try:
            cls.password.delete()
        # pylint: disable=broad-except
        except Exception as e:
            logger.error("%s.tearDownClass() Error deleting password secret: %s", logger_prefix, e)

        logger.debug("%s.tearDownClass() Finished tearing down VectorstoreTestBase class resources.", logger_prefix)
        super().tearDownClass()
