"""
Test mixins for the plugin module.
"""

import logging
import os
from typing import Optional

from django.http import HttpRequest
from django.test import Client

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.plugin.manifest.models.api_connection.model import SAMApiConnection
from smarter.apps.plugin.manifest.models.sql_connection.model import SAMSqlConnection
from smarter.apps.plugin.models import ApiConnection, SqlConnection
from smarter.common.utils import camel_to_snake_dict, get_readonly_yaml_file
from smarter.lib import json
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.manifest.loader import SAMLoader

from .factories import secret_factory


HERE = os.path.abspath(os.path.dirname(__file__))


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PLUGIN_LOGGING) and level >= logging.INFO


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class ConnectionTextMixinBase(TestAccountMixin):
    """
    A base mixin class for testing connections.
    adds account plus an admin and non-admin user to the test case.
    """


class AuthenticatedRequestMixin(ConnectionTextMixinBase):
    """
    A mixin class that adds an authenticated request to the test case.
    """

    client: Client
    request: HttpRequest

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        super().setUpClass()
        logger.info("Setting up AuthenticatedRequestMixin")
        cls.client = Client()
        cls.client.force_login(cls.admin_user)
        response = cls.client.get("/some-url/")
        cls.request = response.wsgi_request

    @classmethod
    def tearDownClass(cls):
        """Tear down test fixtures."""
        logger.info("Tearing down AuthenticatedRequestMixin")
        super().tearDownClass()


class ApiConnectionTestMixin(ConnectionTextMixinBase):
    """
    A mixin class that adds ApiConnection class setUpClass and
    tearDownClass methods."""

    connection_loader: Optional[SAMLoader]
    connection_manifest_path: Optional[str] = None
    connection_manifest: Optional[dict] = None
    connection_model: Optional[SAMApiConnection]
    connection_django_model: Optional[ApiConnection] = None

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
        if not isinstance(connection_manifest, dict):
            raise ValueError(f"Connection manifest not found at {connection_manifest_path}")
        connection_loader = SAMLoader(manifest=json.dumps(connection_manifest))
        connection_model = SAMApiConnection(**connection_loader.pydantic_model_dump())
        if not isinstance(connection_model, SAMApiConnection):
            raise ValueError("Connection model is not an instance of SAMApiConnection")
        if connection_model.spec is None:
            raise ValueError("Connection manifest spec is None")
        if connection_model.metadata is None:
            raise ValueError("Connection manifest metadata is None")

        # 2.) transform the manifest for a django model
        # ---------------------------------------------------------------------
        connection_model_dump = connection_model.spec.connection.model_dump()
        connection_model_dump["account"] = cls.account
        connection_model_dump["name"] = connection_model.metadata.name
        connection_model_dump["description"] = connection_model.metadata.description
        connection_model_dump["kind"] = connection_model.kind

        if connection_model.spec.connection.apiKey:
            clear_api_key = connection_model_dump.pop("apiKey")
            secret_name = f"test_secret_{cls.hash_suffix}"
            secret = secret_factory(user_profile=cls.user_profile, name=secret_name, value=clear_api_key)
            connection_model_dump["apiKey"] = secret

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
        connection_model_dump = camel_to_snake_dict(connection_model_dump)
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
            if isinstance(cls.connection_django_model, ApiConnection):
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

    connection_loader: Optional[SAMLoader]
    connection_manifest_path: Optional[str] = None
    connection_manifest: Optional[dict] = None
    connection_model: Optional[SAMSqlConnection]
    connection_django_model: Optional[SqlConnection] = None

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
        if not isinstance(connection_manifest, dict):
            raise ValueError(f"Connection manifest not found at {connection_manifest_path}")
        connection_loader = SAMLoader(manifest=json.dumps(connection_manifest))
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
        connection_model_dump = camel_to_snake_dict(connection_model_dump)
        connection_model_dump["kind"] = connection_model.kind
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
            if isinstance(cls.connection_django_model, SqlConnection):
                cls.connection_django_model.delete()
        # pylint: disable=W0718
        except Exception:
            pass
        cls.connection_django_model = None
        super().tearDownClass()

    def test_00_sql_connection_mixin(self):
        """Test the SqlConnection itself, lest we get ahead of ourselves"""
        self.assertIsInstance(self.connection_django_model, SqlConnection)
        self.assertIsInstance(self.connection_loader, SAMLoader)
        self.assertIsInstance(self.connection_manifest, dict)
        self.assertIsInstance(self.connection_manifest_path, str)
