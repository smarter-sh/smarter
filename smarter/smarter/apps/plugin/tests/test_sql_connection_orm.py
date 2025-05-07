"""Test SqlConnection Django ORM"""

import os
import unittest

from django.conf import settings
from django.db.backends.base.base import BaseDatabaseWrapper

from smarter.apps.account.tests.factories import (
    admin_user_factory,
    admin_user_teardown,
    generate_hash_suffix,
    mortal_user_factory,
)
from smarter.apps.plugin.manifest.enum import SAMPluginMetadataClassValues
from smarter.apps.plugin.manifest.models.sql_connection.enum import DbEngines
from smarter.apps.plugin.manifest.models.sql_connection.model import (
    SAMSqlConnection,
)
from smarter.apps.plugin.models import PluginMeta, SqlConnection
from smarter.common.api import SmarterApiVersions
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.loader import SAMLoader
from smarter.lib.unittest.utils import get_readonly_yaml_file

from .factories import plugin_meta_factory


HERE = os.path.abspath(os.path.dirname(__file__))


class TestPluginSql(unittest.TestCase):
    """Test SqlConnection Django ORM"""

    _manifest_path: str = None
    _manifest: str = None
    _loader: SAMLoader = None
    _model: SAMSqlConnection = None

    @classmethod
    def setUpClass(cls):
        """
        Set up the test class with a single account, and admin and non-admin users.
        using the class setup so that we retain the same user_profile for each test,
        which is needed so that the django Secret model can be queried.
        """
        cls.hash_suffix = generate_hash_suffix()
        cls.admin_user, cls.account, cls.user_profile = admin_user_factory()
        cls.non_admin_user, _, cls.non_admin_user_profile = mortal_user_factory(account=cls.account)
        cls.meta_data = plugin_meta_factory(
            plugin_class=SAMPluginMetadataClassValues.SQL.value, account=cls.account, user_profile=cls.user_profile
        )

    @classmethod
    def tearDownClass(cls):
        admin_user_teardown(user=cls.admin_user, account=None, user_profile=cls.user_profile)
        admin_user_teardown(user=cls.non_admin_user, account=cls.account, user_profile=cls.non_admin_user_profile)
        try:
            cls.meta_data.delete()
        except PluginMeta.DoesNotExist:
            pass

    def setUp(self):
        """Set up the test case with a single account, and admin and non-admin users."""
        self._manifest = None
        self._manifest_path = None
        self._loader = None
        self._model = None

    @property
    def manifest_path(self) -> str:
        return self._manifest_path

    @manifest_path.setter
    def manifest_path(self, value: str):
        self._manifest_path = value
        self._manifest = None
        self._loader = None
        self._model = None

    @property
    def manifest(self) -> str:
        if not self._manifest and self.manifest_path:
            self._manifest = get_readonly_yaml_file(self.manifest_path)
        return self._manifest

    @property
    def loader(self) -> SAMLoader:
        # initialize a SAMLoader object with the manifest raw data
        if not self._loader and self.manifest:
            self._loader = SAMLoader(manifest=self.manifest)
        return self._loader

    @property
    def model(self) -> SAMSqlConnection:
        # create a SAMSqlConnection pydantic model from the loader
        if not self._model and self.loader:
            self._model = SAMSqlConnection(**self.loader.pydantic_model_dump())
        return self._model

    def properties_factory(self) -> dict:
        return {
            "properties": {
                "location": {"type": "string", "description": "The city and state, e.g., San Francisco, CA"},
                "unit": {
                    "type": "string",
                    "enum": ["Celsius", "Fahrenheit"],
                    "description": "The temperature unit to use. Infer this from the user's location.",
                },
            },
        }

    def test_validate_db_engine_invalid_value(self):
        """Test that the db_engine validator raises an error for invalid values."""
        invalid_db_engine = "invalid_engine"
        with self.assertRaises(SAMValidationError) as context:
            SAMSqlConnection(db_engine=invalid_db_engine)
        self.assertIn(
            f"Invalid SQL connection engine: {invalid_db_engine}. Must be one of {DbEngines.all_values()}",
            str(context.exception),
        )

    def test_validate_db_engine_valid_value(self):
        """Test that the db_engine validator accepts valid values."""
        valid_db_engine = DbEngines.all_values()[0]
        model = SAMSqlConnection(db_engine=valid_db_engine)
        self.assertEqual(model.spec.connection.db_engine, valid_db_engine)

    def test_validate_hostname_invalid_value(self):
        """Test that the hostname validator raises an error for invalid values."""
        invalid_hostname = "invalid_host"
        with self.assertRaises(SAMValidationError) as context:
            SAMSqlConnection(hostname=invalid_hostname)
        self.assertIn(
            f"Invalid SQL connection host: {invalid_hostname}. Must be a valid domain, IPv4, or IPv6 address.",
            str(context.exception),
        )

    def test_validate_hostname_valid_value(self):
        """Test that the hostname validator accepts valid values."""
        valid_hostname = "example.com"
        model = SAMSqlConnection(hostname=valid_hostname)
        self.assertEqual(model.spec.connection.hostname, valid_hostname)

    def test_validate_port_invalid_value(self):
        """Test that the port validator raises an error for invalid values."""
        invalid_port = 70000
        with self.assertRaises(SAMValidationError) as context:
            SAMSqlConnection(port=invalid_port)
        self.assertIn(
            f"Invalid SQL connection port: {invalid_port}. Must be between 1 and 65535.", str(context.exception)
        )

    def test_validate_port_valid_value(self):
        """Test that the port validator accepts valid values."""
        valid_port = 3306
        model = SAMSqlConnection(port=valid_port)
        self.assertEqual(model.spec.connection.port, valid_port)

    def test_validate_database_invalid_value(self):
        """Test that the database validator raises an error for invalid values."""
        invalid_database = ""
        with self.assertRaises(SAMValidationError) as context:
            SAMSqlConnection(database=invalid_database)
        self.assertIn(f"Invalid database name: {invalid_database}. Must be a valid string.", str(context.exception))

    def test_validate_database_valid_value(self):
        """Test that the database validator accepts valid values."""
        valid_database = "test_db"
        model = SAMSqlConnection(database=valid_database)
        self.assertEqual(model.spec.connection.database, valid_database)

    def test_validate_username_invalid_value(self):
        """Test that the username validator raises an error for invalid values."""
        invalid_username = ""
        with self.assertRaises(SAMValidationError) as context:
            SAMSqlConnection(username=invalid_username)
        self.assertIn(f"Invalid username: {invalid_username}. Must be a valid string.", str(context.exception))

    def test_validate_username_valid_value(self):
        """Test that the username validator accepts valid values."""
        valid_username = "user"
        model = SAMSqlConnection(username=valid_username)
        self.assertEqual(model.spec.connection.username, valid_username)

    def test_validate_timeout_invalid_value(self):
        """Test that the timeout validator raises an error for invalid values."""
        invalid_timeout = -1
        with self.assertRaises(SAMValidationError) as context:
            SAMSqlConnection(timeout=invalid_timeout)
        self.assertIn(f"Invalid timeout: {invalid_timeout}. Must be greater than 0.", str(context.exception))

    def test_validate_timeout_valid_value(self):
        """Test that the timeout validator accepts valid values."""
        valid_timeout = 30
        model = SAMSqlConnection(timeout=valid_timeout)
        self.assertEqual(model.spec.connection.timeout, valid_timeout)

    def test_validate_proxy_host_invalid_value(self):
        """Test that the proxy_host validator raises an error for invalid values."""
        invalid_proxy_host = "invalid_proxy"
        with self.assertRaises(SAMValidationError) as context:
            SAMSqlConnection(proxy_host=invalid_proxy_host)
        self.assertIn(
            f"Invalid SQL proxy host: {invalid_proxy_host}. Must be a valid domain, IPv4, or IPv6 address.",
            str(context.exception),
        )

    def test_validate_proxy_host_valid_value(self):
        """Test that the proxy_host validator accepts valid values."""
        valid_proxy_host = "proxy.example.com"
        model = SAMSqlConnection(proxy_host=valid_proxy_host)
        self.assertEqual(model.spec.connection.proxy_host, valid_proxy_host)

    def test_validate_proxy_port_invalid_value(self):
        """Test that the proxy_port validator raises an error for invalid values."""
        invalid_proxy_port = 70000
        with self.assertRaises(SAMValidationError) as context:
            SAMSqlConnection(proxy_port=invalid_proxy_port)
        self.assertIn(
            f"Invalid SQL proxy port: {invalid_proxy_port}. Must be between 1 and 65535.", str(context.exception)
        )

    def test_validate_proxy_port_valid_value(self):
        """Test that the proxy_port validator accepts valid values."""
        valid_proxy_port = 8080
        model = SAMSqlConnection(proxy_port=valid_proxy_port)
        self.assertEqual(model.spec.connection.proxy_port, valid_proxy_port)

    def test_validate_pool_size_invalid_value(self):
        """Test that the pool_size validator raises an error for invalid values."""
        invalid_pool_size = 0
        with self.assertRaises(SAMValidationError) as context:
            SAMSqlConnection(pool_size=invalid_pool_size)
        self.assertIn(f"Invalid pool size: {invalid_pool_size}. Must be greater than 0.", str(context.exception))

    def test_validate_pool_size_valid_value(self):
        """Test that the pool_size validator accepts valid values."""
        valid_pool_size = 10
        model = SAMSqlConnection(pool_size=valid_pool_size)
        self.assertEqual(model.spec.connection.pool_size, valid_pool_size)

    def test_validate_max_overflow_invalid_value(self):
        """Test that the max_overflow validator raises an error for invalid values."""
        invalid_max_overflow = -1
        with self.assertRaises(SAMValidationError) as context:
            SAMSqlConnection(max_overflow=invalid_max_overflow)
        self.assertIn(f"Invalid max overflow: {invalid_max_overflow}. Must be 0 or greater.", str(context.exception))

    def test_validate_max_overflow_valid_value(self):
        """Test that the max_overflow validator accepts valid values."""
        valid_max_overflow = 5
        model = SAMSqlConnection(max_overflow=valid_max_overflow)
        self.assertEqual(model.spec.connection.max_overflow, valid_max_overflow)

    def test_validate_authentication_method_invalid_value(self):
        """Test that the authentication_method validator raises an error for invalid values."""
        invalid_auth_method = "invalid_method"
        with self.assertRaises(SAMValidationError) as context:
            SAMSqlConnection(authentication_method=invalid_auth_method)
        self.assertIn(
            f"Invalid authentication method: {invalid_auth_method}. Must be one of {SqlConnectionORM.DBMSAuthenticationMethods.choices()}",
            str(context.exception),
        )

    def test_validate_authentication_method_valid_value(self):
        """Test that the authentication_method validator accepts valid values."""
        valid_auth_method = SqlConnection.DBMSAuthenticationMethods.choices()[0]
        model = SAMSqlConnection(authentication_method=valid_auth_method)
        self.assertEqual(model.spec.connection.authentication_method, valid_auth_method)

    def test_validate_use_ssl_invalid_value(self):
        """Test that the use_ssl validator raises an error for invalid values."""
        invalid_use_ssl = "not_a_boolean"
        with self.assertRaises(SAMValidationError) as context:
            SAMSqlConnection(use_ssl=invalid_use_ssl)
        self.assertIn(f"Invalid use_ssl value: {invalid_use_ssl}. Must be a boolean.", str(context.exception))

    def test_validate_use_ssl_valid_value(self):
        """Test that the use_ssl validator accepts valid values."""
        valid_use_ssl = True
        model = SAMSqlConnection(use_ssl=valid_use_ssl)
        self.assertEqual(model.spec.connection.use_ssl, valid_use_ssl)

    def test_model_tcpip(self):
        """Test that the Loader can load the manifest."""
        self.manifest_path = os.path.join(HERE, "mock_data/sql-connection.yaml")

        self.assertEqual(self.loader.manifest_api_version, SmarterApiVersions.V1)
        self.assertEqual(self.loader.manifest_kind, "SqlConnection")
        self.assertIsNotNone(self.loader.manifest_metadata)
        self.assertIsNotNone(self.model.spec)

        self.assertEqual(self.model.spec.connection.db_engine, "django.db.backends.mysql")
        self.assertEqual(self.model.spec.connection.hostname, "smarter-mysql")
        self.assertEqual(self.model.spec.connection.port, 3306)
        self.assertEqual(self.model.spec.connection.username, "smarter")
        self.assertEqual(self.model.spec.connection.password, "smarter")
        self.assertEqual(self.model.spec.connection.database, "smarter")
        self.assertEqual(self.model.spec.connection.timeout, 30)
        self.assertEqual(self.model.spec.connection.authentication_method, "tcpip")
        self.assertEqual(self.model.spec.connection.pool_size, 15)
        self.assertEqual(self.model.spec.connection.max_overflow, 20)

    def test_django_orm_tcpip(self):
        """Test that the Django model can be initialized from the Pydantic model."""
        self.manifest_path = os.path.join(HERE, "mock_data/sql-connection.yaml")
        model_dump = self.model.spec.connection.model_dump()

        model_dump["account"] = self.account
        model_dump["name"] = self.model.metadata.name
        django_model = SqlConnection(**model_dump)
        django_model.save()

        self.assertIsNotNone(django_model)
        self.assertEqual(django_model.account, self.account)
        self.assertEqual(django_model.name, self.model.metadata.name)
        self.assertEqual(django_model.db_engine, self.model.spec.connection.db_engine)
        self.assertEqual(django_model.hostname, self.model.spec.connection.hostname)
        self.assertEqual(django_model.port, self.model.spec.connection.port)
        self.assertEqual(django_model.username, self.model.spec.connection.username)
        self.assertEqual(django_model.password, self.model.spec.connection.password)
        self.assertEqual(django_model.database, self.model.spec.connection.database)
        self.assertEqual(django_model.timeout, self.model.spec.connection.timeout)
        self.assertEqual(django_model.authentication_method, self.model.spec.connection.authentication_method)
        self.assertEqual(django_model.pool_size, self.model.spec.connection.pool_size)
        self.assertEqual(django_model.max_overflow, self.model.spec.connection.max_overflow)
        self.assertEqual(django_model.use_ssl, False)
        self.assertEqual(django_model.ssl_cert, None)
        self.assertEqual(django_model.ssl_key, None)
        self.assertEqual(django_model.ssl_ca, None)
        self.assertEqual(django_model.proxy_host, None)
        self.assertEqual(django_model.proxy_port, None)
        self.assertEqual(django_model.proxy_username, None)
        self.assertEqual(django_model.proxy_password, None)
        self.assertEqual(django_model.ssh_known_hosts, None)
        self.assertEqual(django_model.authentication_method, self.model.spec.connection.authentication_method)
        self.assertEqual(django_model.pool_size, self.model.spec.connection.pool_size)
        self.assertEqual(django_model.max_overflow, self.model.spec.connection.max_overflow)

        django_model.delete()

    def test_model_tcpip_ssl(self):
        """Test that the Loader can load the manifest."""
        self.manifest_path = os.path.join(HERE, "mock_data/sql-connection-ssl.yaml")

        self.assertEqual(self.loader.manifest_api_version, SmarterApiVersions.V1)
        self.assertEqual(self.loader.manifest_kind, "SqlConnection")
        self.assertIsNotNone(self.loader.manifest_metadata)
        self.assertIsNotNone(self.model.spec)

        self.assertEqual(self.model.spec.connection.db_engine, "django.db.backends.mysql")
        self.assertEqual(self.model.spec.connection.hostname, "smarter-mysql")
        self.assertEqual(self.model.spec.connection.port, 3306)
        self.assertEqual(self.model.spec.connection.username, "smarter")
        self.assertEqual(self.model.spec.connection.password, "smarter")
        self.assertEqual(self.model.spec.connection.database, "smarter")
        self.assertEqual(self.model.spec.connection.timeout, 30)
        self.assertEqual(self.model.spec.connection.use_ssl, True)
        self.assertEqual(self.model.spec.connection.ssl_cert, "/path/to/cert.pem")
        self.assertEqual(self.model.spec.connection.ssl_key, "/path/to/key.pem")
        self.assertEqual(self.model.spec.connection.ssl_ca, "/path/to/ca.pem")
        self.assertEqual(self.model.spec.connection.authentication_method, "tcpip")

    def test_django_orm_tcpip_ssl(self):
        """Test that the Django model can be initialized from the Pydantic model."""
        self.manifest_path = os.path.join(HERE, "mock_data/sql-connection-ssl.yaml")
        model_dump = self.model.spec.connection.model_dump()

        model_dump["account"] = self.account
        model_dump["name"] = self.model.metadata.name
        django_model = SqlConnection(**model_dump)
        django_model.save()

        self.assertIsNotNone(django_model)
        self.assertEqual(django_model.account, self.account)
        self.assertEqual(django_model.name, self.model.metadata.name)
        self.assertEqual(django_model.db_engine, self.model.spec.connection.db_engine)
        self.assertEqual(django_model.hostname, self.model.spec.connection.hostname)
        self.assertEqual(django_model.port, self.model.spec.connection.port)
        self.assertEqual(django_model.username, self.model.spec.connection.username)
        self.assertEqual(django_model.password, self.model.spec.connection.password)
        self.assertEqual(django_model.database, self.model.spec.connection.database)
        self.assertEqual(django_model.timeout, self.model.spec.connection.timeout)
        self.assertEqual(django_model.use_ssl, True)
        self.assertEqual(django_model.ssl_cert, self.model.spec.connection.ssl_cert)
        self.assertEqual(django_model.ssl_key, self.model.spec.connection.ssl_key)
        self.assertEqual(django_model.ssl_ca, self.model.spec.connection.ssl_ca)
        self.assertEqual(django_model.authentication_method, self.model.spec.connection.authentication_method)
        self.assertEqual(django_model.pool_size, self.model.spec.connection.pool_size)
        self.assertEqual(django_model.max_overflow, self.model.spec.connection.max_overflow)
        self.assertEqual(django_model.proxy_host, None)
        self.assertEqual(django_model.proxy_port, None)
        self.assertEqual(django_model.proxy_username, None)
        self.assertEqual(django_model.proxy_password, None)
        self.assertEqual(django_model.ssh_known_hosts, None)

        django_model.delete()

    def test_model_tcpip_ssh(self):
        """Test that the Loader can load the manifest."""
        self.manifest_path = os.path.join(HERE, "mock_data/sql-connection-ssh.yaml")

        self.assertEqual(self.loader.manifest_api_version, SmarterApiVersions.V1)
        self.assertEqual(self.loader.manifest_kind, "SqlConnection")
        self.assertIsNotNone(self.loader.manifest_metadata)
        self.assertIsNotNone(self.model.spec)

        self.assertEqual(self.model.spec.connection.db_engine, "django.db.backends.mysql")
        self.assertEqual(self.model.spec.connection.hostname, "smarter-mysql")
        self.assertEqual(self.model.spec.connection.port, 3306)
        self.assertEqual(self.model.spec.connection.username, "smarter")
        self.assertEqual(self.model.spec.connection.password, "smarter")
        self.assertEqual(self.model.spec.connection.database, "smarter")
        self.assertEqual(self.model.spec.connection.timeout, 30)
        self.assertEqual(self.model.spec.connection.proxy_host, "proxy.example.com")
        self.assertEqual(self.model.spec.connection.proxy_port, 8080)
        self.assertEqual(self.model.spec.connection.proxy_username, "proxyUser")
        self.assertEqual(self.model.spec.connection.proxy_password, "proxyPass")
        self.assertEqual(self.model.spec.connection.ssh_known_hosts, "/path/to/known_hosts")
        self.assertEqual(self.model.spec.connection.authentication_method, "tcpip_ssh")
        self.assertEqual(self.model.spec.connection.pool_size, 5)
        self.assertEqual(self.model.spec.connection.max_overflow, 10)
        self.assertEqual(self.model.spec.connection.authentication_method, "tcpip_ssh")
        self.assertEqual(self.model.spec.connection.use_ssl, False)
        self.assertEqual(self.model.spec.connection.ssl_cert, None)
        self.assertEqual(self.model.spec.connection.ssl_key, None)
        self.assertEqual(self.model.spec.connection.ssl_ca, None)

    def test_django_orm_tcpip_ssh(self):
        """Test that the Django model can be initialized from the Pydantic model."""
        self.manifest_path = os.path.join(HERE, "mock_data/sql-connection-ssh.yaml")
        model_dump = self.model.spec.connection.model_dump()

        model_dump["account"] = self.account
        model_dump["name"] = self.model.metadata.name
        django_model = SqlConnection(**model_dump)
        django_model.save()

        self.assertIsNotNone(django_model)
        self.assertEqual(django_model.account, self.account)
        self.assertEqual(django_model.name, self.model.metadata.name)
        self.assertEqual(django_model.db_engine, self.model.spec.connection.db_engine)
        self.assertEqual(django_model.hostname, self.model.spec.connection.hostname)
        self.assertEqual(django_model.port, self.model.spec.connection.port)
        self.assertEqual(django_model.username, self.model.spec.connection.username)
        self.assertEqual(django_model.password, self.model.spec.connection.password)
        self.assertEqual(django_model.database, self.model.spec.connection.database)
        self.assertEqual(django_model.timeout, self.model.spec.connection.timeout)
        self.assertEqual(django_model.proxy_host, self.model.spec.connection.proxy_host)
        self.assertEqual(django_model.proxy_port, self.model.spec.connection.proxy_port)
        self.assertEqual(django_model.proxy_username, self.model.spec.connection.proxy_username)
        self.assertEqual(django_model.proxy_password, self.model.spec.connection.proxy_password)
        self.assertEqual(django_model.ssh_known_hosts, self.model.spec.connection.ssh_known_hosts)
        self.assertEqual(django_model.authentication_method, self.model.spec.connection.authentication_method)
        self.assertEqual(django_model.pool_size, self.model.spec.connection.pool_size)
        self.assertEqual(django_model.max_overflow, self.model.spec.connection.max_overflow)

        django_model.delete()
