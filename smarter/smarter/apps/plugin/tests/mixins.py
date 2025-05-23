"""
Test mixins for the plugin module.
"""

import os
from logging import getLogger

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.plugin.manifest.models.api_connection.model import SAMApiConnection
from smarter.apps.plugin.manifest.models.sql_connection.model import SAMSqlConnection
from smarter.apps.plugin.models import ApiConnection, SqlConnection
from smarter.common.utils import get_readonly_yaml_file
from smarter.lib.manifest.loader import SAMLoader

from .factories import secret_factory


HERE = os.path.abspath(os.path.dirname(__file__))
logger = getLogger(__name__)


class ConnectionTextMixinBase(TestAccountMixin):
    """
    A base mixin class for testing connections.
    adds account plus an admin and non-admin user to the test case.
    """


class ApiConnectionTestMixin(ConnectionTextMixinBase):
    """
    A mixin class that adds ApiConnection class setUpClass and
    tearDownClass methods."""

    connection_loader: SAMLoader
    connection_manifest_path: str = None
    connection_manifest: dict = None
    connection_model: SAMApiConnection
    connection_django_model: ApiConnection = None

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        super().setUpClass()
        logger.info("Setting up ApiConnectionTestMixin")

        # setup an instance of ApiConnection() - a Django model
        # ---------------------------------------------------------------------
        # 1.) create an ApiConnection manifest
        connection_manifest_filename = "api-connection.yaml"
        connection_manifest_path = os.path.join(HERE, "mock_data", connection_manifest_filename)
        connection_manifest = get_readonly_yaml_file(connection_manifest_path)
        connection_loader = SAMLoader(manifest=connection_manifest)
        connection_model = SAMApiConnection(**connection_loader.pydantic_model_dump())

        # 2.) transform the manifest for a django model
        # ---------------------------------------------------------------------
        connection_model_dump = connection_model.spec.connection.model_dump()
        connection_model_dump["account"] = cls.account
        connection_model_dump["name"] = connection_model.metadata.name
        connection_model_dump["description"] = connection_model.metadata.description

        if connection_model.spec.connection.apiKey:
            clear_api_key = connection_model_dump.pop("api_key")
            secret_name = f"test_secret_{cls.hash_suffix}"
            secret = secret_factory(user_profile=cls.user_profile, name=secret_name, value=clear_api_key)
            connection_model_dump["api_key"] = secret

        if connection_model.spec.connection.proxyPassword:
            clear_proxy_password = connection_model_dump.pop("proxyPassword")
            proxy_secret_name = f"test_proxy_secret_{cls.hash_suffix}"
            proxy_secret = secret_factory(
                user_profile=cls.user_profile, name=proxy_secret_name, value=clear_proxy_password
            )
            connection_model_dump["proxyPassword"] = proxy_secret

        # 2.) initialize all of our class variables
        # ---------------------------------------------------------------------
        cls.connection_loader = connection_loader
        cls.connection_manifest_path = connection_manifest_path
        cls.connection_manifest = connection_manifest
        cls.connection_model = connection_model
        cls.connection_django_model = ApiConnection(**connection_model_dump)
        cls.connection_django_model.save()

        logger.info("connection_manifest_path initialized: %s", str(connection_manifest_path))
        logger.info("connection_manifest initialized: %s", str(connection_manifest))
        logger.info("connection_loader initialized: %s", str(connection_loader))
        logger.info("connection_model initialized: %s", str(connection_model))
        logger.info("connection_django_model initialized: %s", str(cls.connection_django_model))

    @classmethod
    def tearDownClass(cls):
        """Tear down test fixtures."""
        logger.info("Tearing down ApiConnectionTestMixin")

        cls.connection_manifest_path = None
        cls.connection_manifest = None
        cls.connection_loader = None
        cls.connection_model = None
        try:
            cls.connection_django_model.delete()
        # pylint: disable=W0718
        except Exception:
            pass
        cls.connection_django_model = None

        super().tearDownClass()


class SqlConnectionTestMixin(ConnectionTextMixinBase):
    """
    A mixin class that adds SqlConnection class setUpClass and
    tearDownClass methods.
    """

    connection_loader: SAMLoader
    connection_manifest_path: str = None
    connection_manifest: dict = None
    connection_model: SAMSqlConnection
    connection_django_model: SqlConnection = None

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        super().setUpClass()

        # setup an instance of SqlConnection() - a Django model
        # ---------------------------------------------------------------------
        # 1.) create an SqlConnection manifest
        connection_manifest_filename = "sql-connection.yaml"
        connection_manifest_path = os.path.join(HERE, "mock_data", connection_manifest_filename)
        connection_manifest = get_readonly_yaml_file(connection_manifest_path)
        connection_loader = SAMLoader(manifest=connection_manifest)
        connection_model = SAMSqlConnection(**connection_loader.pydantic_model_dump())

        # 2.) transform the manifest for a django model
        # ---------------------------------------------------------------------
        connection_model_dump = connection_model.spec.connection.model_dump()
        connection_model_dump["account"] = cls.account
        connection_model_dump["name"] = connection_model.metadata.name
        connection_model_dump["description"] = connection_model.metadata.description

        if connection_model.spec.connection.password:
            clear_password = connection_model_dump.pop("password")
            secret_name = f"test_secret_{cls.hash_suffix}"
            secret = secret_factory(user_profile=cls.user_profile, name=secret_name, value=clear_password)
            connection_model_dump["password"] = secret

        if connection_model.spec.connection.proxyPassword:
            clear_proxy_password = connection_model_dump.pop("proxyPassword")
            proxy_secret_name = f"test_proxy_secret_{cls.hash_suffix}"
            proxy_secret = secret_factory(
                user_profile=cls.user_profile, name=proxy_secret_name, value=clear_proxy_password
            )
            connection_model_dump["proxyPassword"] = proxy_secret

        # 2.) initialize all of our class variables
        # ---------------------------------------------------------------------
        cls.connection_loader = connection_loader
        cls.connection_manifest_path = connection_manifest_path
        cls.connection_manifest = connection_manifest
        cls.connection_model = connection_model
        cls.connection_django_model = SqlConnection(**connection_model_dump)
        cls.connection_django_model.save()

        logger.info("connection_manifest_path initialized: %s", str(connection_manifest_path))
        logger.info("connection_manifest initialized: %s", str(connection_manifest))
        logger.info("connection_loader initialized: %s", str(connection_loader))
        logger.info("connection_model initialized: %s", str(connection_model))
        logger.info("connection_django_model initialized: %s", str(cls.connection_django_model))

    @classmethod
    def tearDownClass(cls):
        """Tear down test fixtures."""
        logger.info("Tearing down ApiConnectionTestMixin")

        cls.connection_manifest_path = None
        cls.connection_manifest = None
        cls.connection_loader = None
        cls.connection_model = None
        try:
            cls.connection_django_model.delete()
        # pylint: disable=W0718
        except Exception:
            pass
        cls.connection_django_model = None
        super().tearDownClass()
