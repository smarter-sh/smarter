"""Test SqlConnection Django ORM and Manifest Loader."""

# pylint: disable=W0104

import logging
from typing import Optional

from pydantic_core import ValidationError

from smarter.apps.account.models import Secret
from smarter.apps.plugin.manifest.models.sql_connection.enum import (
    DbEngines,
    DBMSAuthenticationMethods,
)
from smarter.apps.plugin.manifest.models.sql_connection.model import SAMSqlConnection
from smarter.apps.plugin.models import SqlConnection
from smarter.apps.plugin.tests.base_classes import TestConnectionBase
from smarter.apps.plugin.tests.factories import secret_factory
from smarter.common.api import SmarterApiVersions
from smarter.common.exceptions import SmarterValueError
from smarter.common.utils import camel_to_snake, camel_to_snake_dict
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.manifest.exceptions import SAMValidationError


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PLUGIN_LOGGING) and level <= logging.INFO


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class TestSqlConnection(TestConnectionBase):
    """Test SqlConnection Django ORM and Manifest Loader"""

    _model: Optional[SAMSqlConnection] = None

    @property
    def model(self) -> Optional[SAMSqlConnection]:
        # create a SAMSqlConnection pydantic model from the loader
        if not self._model and self.loader:
            self._model = SAMSqlConnection(**self.loader.pydantic_model_dump())
            self.assertIsNotNone(self._model)
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
        """Test that the dbEngine validator raises an error for invalid values."""
        self.load_manifest(filename="sql-connection-ssh.yaml")
        logger.info("Testing dbEngine validator:\n%s", self.manifest)
        if not self._manifest:
            self.fail("Manifest should not be None after loading the file")

        invalid_db_engine = "invalid_engine"
        self._manifest["spec"]["connection"]["dbEngine"] = invalid_db_engine
        self._loader = None
        self._model = None  # type: ignore[assignment]
        with self.assertRaises(SAMValidationError) as context:
            print(self.model)
        self.assertIn(
            f"Invalid SQL connection engine: {invalid_db_engine}. Must be one of {DbEngines.all_values()}",
            str(context.exception),
        )

    def test_validate_hostname_invalid_value(self):
        """Test that the hostname validator raises an error for invalid values."""
        self.load_manifest(filename="sql-connection-ssh.yaml")
        if not self._manifest:
            self.fail("Manifest should not be None after loading the file")

        invalid_hostname = "$invalid-host&"
        self._manifest["spec"]["connection"]["hostname"] = invalid_hostname
        self._loader = None
        self._model = None  # type: ignore[assignment]
        with self.assertRaises(SAMValidationError) as context:
            print(self.model)
        self.assertIn(
            f"Invalid SQL connection host: {invalid_hostname}. Must be a valid domain, IPv4, or IPv6 address.",
            str(context.exception),
        )

    def test_validate_port_invalid_value(self):
        """Test that the port validator raises an error for invalid values."""
        self.load_manifest(filename="sql-connection-ssh.yaml")
        if not self._manifest:
            self.fail("Manifest should not be None after loading the file")

        invalid_port = 70000
        self._manifest["spec"]["connection"]["port"] = invalid_port
        self._loader = None
        self._model = None  # type: ignore[assignment]
        with self.assertRaises(SAMValidationError) as context:
            print(self.model)
        self.assertIn(
            f"Invalid SQL connection port: {invalid_port}. Must be between 1 and 65535.", str(context.exception)
        )

    def test_validate_database_invalid_value(self):
        """Test that the database validator raises an error for invalid values."""
        self.load_manifest(filename="sql-connection-ssh.yaml")
        if not self._manifest:
            self.fail("Manifest should not be None after loading the file")

        invalid_database = ""
        self._manifest["spec"]["connection"]["database"] = invalid_database
        self._loader = None
        self._model = None  # type: ignore[assignment]
        with self.assertRaises(SAMValidationError) as context:
            print(self.model)
        self.assertIn(f"Invalid database name: {invalid_database}. Must be a valid string.", str(context.exception))

    def test_validate_username_invalid_value(self):
        """Test that the username validator raises an error for invalid values."""
        self.load_manifest(filename="sql-connection-ssh.yaml")
        if not self._manifest:
            self.fail("Manifest should not be None after loading the file")

        invalid_username = ""
        self._manifest["spec"]["connection"]["username"] = invalid_username
        self._loader = None
        self._model = None  # type: ignore[assignment]
        with self.assertRaises(SAMValidationError) as context:
            print(self.model)
        self.assertIn(f"Invalid username: {invalid_username}. Must be a valid string.", str(context.exception))

    def test_validate_timeout_invalid_value(self):
        """Test that the timeout validator raises an error for invalid values."""
        self.load_manifest(filename="sql-connection-ssh.yaml")
        if not self._manifest:
            self.fail("Manifest should not be None after loading the file")

        invalid_timeout = -1
        self._manifest["spec"]["connection"]["timeout"] = invalid_timeout
        self._loader = None
        self._model = None  # type: ignore[assignment]
        with self.assertRaises(SAMValidationError) as context:
            print(self.model)
        self.assertIn(f"Invalid timeout: {invalid_timeout}. Must be greater than 0.", str(context.exception))

    def test_validate_timeout_valid_value(self):
        """Test that the timeout validator accepts valid values."""
        self.load_manifest(filename="sql-connection-ssh.yaml")
        if not self._manifest:
            self.fail("Manifest should not be None after loading the file")
        if not self.model:
            self.fail("Model should not be None after loading the manifest")

        valid_timeout = 30
        self._manifest["spec"]["connection"]["timeout"] = valid_timeout
        self._loader = None
        self._model = None  # type: ignore[assignment]
        self.model
        self.assertEqual(self.model.spec.connection.timeout, valid_timeout)

    def test_validate_proxy_host_invalid_value(self):
        """Test that the proxyHost validator raises an error for invalid values."""
        self.load_manifest(filename="sql-connection-ssh.yaml")
        if not self._manifest:
            self.fail("Manifest should not be None after loading the file")

        invalid_proxy_host = "/invalid_proxy$$--"
        self._manifest["spec"]["connection"]["proxyHost"] = invalid_proxy_host
        self._loader = None
        self._model = None  # type: ignore[assignment]
        with self.assertRaises(SAMValidationError) as context:
            print(self.model)
        self.assertIn(
            f"Invalid SQL proxy host: {invalid_proxy_host}. Must be a valid domain, IPv4, or IPv6 address.",
            str(context.exception),
        )

    def test_validate_proxy_host_valid_value(self):
        """Test that the proxyHost validator accepts valid values."""
        self.load_manifest(filename="sql-connection-ssh.yaml")
        if not self._manifest:
            self.fail("Manifest should not be None after loading the file")

        valid_proxy_host = "proxy.example.com"
        self._manifest["spec"]["connection"]["proxyHost"] = valid_proxy_host
        self._loader = None
        self._model = None  # type: ignore[assignment]
        self.model
        self.assertEqual(self.model.spec.connection.proxyHost, valid_proxy_host)  # type: ignore[no-any-return]

    def test_validate_proxy_port_invalid_value(self):
        """Test that the proxyPort validator raises an error for invalid values."""
        self.load_manifest(filename="sql-connection-ssh.yaml")
        if not self._manifest:
            self.fail("Manifest should not be None after loading the file")

        invalid_proxy_port = 70000
        self._manifest["spec"]["connection"]["proxyPort"] = invalid_proxy_port
        self._loader = None
        self._model = None  # type: ignore[assignment]
        with self.assertRaises(SAMValidationError) as context:
            print(self.model)
        self.assertIn(
            f"Invalid SQL proxy port: {invalid_proxy_port}. Must be between 1 and 65535.", str(context.exception)
        )

    def test_validate_proxy_port_valid_value(self):
        """Test that the proxyPort validator accepts valid values."""
        self.load_manifest(filename="sql-connection-ssh.yaml")
        if not self._manifest:
            self.fail("Manifest should not be None after loading the file")
        if not self.model:
            self.fail("Model should not be None after loading the manifest")

        valid_proxy_port = 8080
        self._manifest["spec"]["connection"]["proxyPort"] = valid_proxy_port
        self._loader = None
        self._model = None  # type: ignore[assignment]
        self.model
        self.assertEqual(self.model.spec.connection.proxyPort, valid_proxy_port)

    def test_validate_pool_size_invalid_value(self):
        """Test that the poolSize validator raises an error for invalid values."""
        self.load_manifest(filename="sql-connection-ssh.yaml")
        if not self._manifest:
            self.fail("Manifest should not be None after loading the file")
        if not isinstance(self.manifest, dict):
            self.fail("Manifest should be a dictionary")

        invalid_pool_size = 0
        self.manifest["spec"]["connection"]["poolSize"] = invalid_pool_size
        self._loader = None
        self._model = None  # type: ignore[assignment]

        with self.assertRaises(SAMValidationError) as context:
            print(self.model)
        self.assertIn(f"Invalid pool size: {invalid_pool_size}. Must be greater than 0.", str(context.exception))

    def test_validate_pool_size_valid_value(self):
        """Test that the poolSize validator accepts valid values."""
        self.load_manifest(filename="sql-connection-ssh.yaml")
        if not self.model:
            self.fail("Model should not be None after loading the manifest")

        if not self._manifest:
            self.fail("Manifest should not be None after loading the file")
        if not isinstance(self.manifest, dict):
            self.fail("Manifest should be a dictionary")
        valid_pool_size = 10
        self.manifest["spec"]["connection"]["poolSize"] = valid_pool_size
        self._loader = None
        self._model = None  # type: ignore[assignment]
        self.model
        self.assertEqual(self.model.spec.connection.poolSize, valid_pool_size)

    def test_validate_max_overflow_invalid_value(self):
        """Test that the maxOverflow validator raises an error for invalid values."""
        self.load_manifest(filename="sql-connection-ssh.yaml")
        if not self._manifest:
            self.fail("Manifest should not be None after loading the file")
        if not isinstance(self.manifest, dict):
            self.fail("Manifest should be a dictionary")

        invalid_max_overflow = -1
        self.manifest["spec"]["connection"]["maxOverflow"] = invalid_max_overflow
        self._loader = None
        self._model = None  # type: ignore[assignment]
        with self.assertRaises(SAMValidationError) as context:
            print(self.model)
        self.assertIn(f"Invalid max overflow: {invalid_max_overflow}. Must be 0 or greater.", str(context.exception))

    def test_validate_max_overflow_valid_value(self):
        """Test that the maxOverflow validator accepts valid values."""
        self.load_manifest(filename="sql-connection-ssh.yaml")
        if not self.manifest:
            self.fail("Manifest should not be None after loading the file")
        if not self.model:
            self.fail("Model should not be None after loading the manifest")

        valid_max_overflow = 5
        self.manifest["spec"]["connection"]["maxOverflow"] = valid_max_overflow
        self._loader = None
        self._model = None  # type: ignore[assignment]
        self.model
        self.assertEqual(self.model.spec.connection.maxOverflow, valid_max_overflow)

    def test_validate_authentication_method_invalid_value(self):
        """Test that the authenticationMethod validator raises an error for invalid values."""
        self.load_manifest(filename="sql-connection-ssh.yaml")
        if not self._manifest:
            self.fail("Manifest should not be None after loading the file")

        invalid_auth_method = "invalid_method"
        self._manifest["spec"]["connection"]["authenticationMethod"] = invalid_auth_method
        self._loader = None
        self._model = None  # type: ignore[assignment]
        with self.assertRaises(SAMValidationError) as context:
            print(self.model)
        self.assertIn(
            f"Invalid authentication method: {invalid_auth_method}. Must be one of {DBMSAuthenticationMethods.all_values()}",
            str(context.exception),
        )

    def test_validate_authentication_method_valid_value(self):
        """Test that the authenticationMethod validator accepts valid values."""
        self.load_manifest(filename="sql-connection-ssh.yaml")
        if not self._manifest:
            self.fail("Manifest should not be None after loading the file")
        if not self.model:
            self.fail("Model should not be None after loading the manifest")

        valid_auth_method = DBMSAuthenticationMethods.all_values()[0]
        self._manifest["spec"]["connection"]["authenticationMethod"] = valid_auth_method
        self._loader = None
        self._model = None  # type: ignore[assignment]
        self.model
        self.assertEqual(self.model.spec.connection.authenticationMethod, valid_auth_method)

    def test_validate_use_ssl_invalid_value(self):
        """Test that the useSsl validator raises an error for invalid values."""
        self.load_manifest(filename="sql-connection-ssh.yaml")
        if not self._manifest:
            self.fail("Manifest should not be None after loading the file")

        invalid_use_ssl = "not_a_boolean"
        self._manifest["spec"]["connection"]["useSsl"] = invalid_use_ssl
        self._loader = None
        self._model = None  # type: ignore[assignment]
        with self.assertRaises(ValidationError) as context:
            print(self.model)
        self.assertIn("Input should be a valid boolean, unable to interpret input", str(context.exception))

    def test_validate_use_ssl_valid_value(self):
        """Test that the useSsl validator accepts valid values."""
        self.load_manifest(filename="sql-connection-ssh.yaml")
        if not self._manifest:
            self.fail("Manifest should not be None after loading the file")
        if not self.model:
            self.fail("Model should not be None after loading the manifest")

        valid_use_ssl = True
        self._manifest["spec"]["connection"]["useSsl"] = valid_use_ssl
        self._loader = None
        self._model = None  # type: ignore[assignment]
        self.model
        self.assertEqual(self.model.spec.connection.useSsl, valid_use_ssl)

    def test_model_tcpip(self):
        """Test that the Loader can load the manifest."""
        self.load_manifest(filename="sql-connection.yaml")
        if not self.loader:
            self.fail("Loader should not be None after loading the manifest")
        if not self.model:
            self.fail("Model should not be None after loading the manifest")

        self.assertEqual(self.loader.manifest_api_version, SmarterApiVersions.V1)
        self.assertEqual(self.loader.manifest_kind, "SqlConnection")
        self.assertIsNotNone(self.loader.manifest_metadata)
        self.assertIsNotNone(self.model.spec)

        self.assertEqual(self.model.spec.connection.dbEngine, "django.db.backends.mysql")
        self.assertEqual(self.model.spec.connection.hostname, "smarter-mysql")
        self.assertEqual(self.model.spec.connection.port, 3306)
        self.assertEqual(self.model.spec.connection.username, "smarter")
        self.assertEqual(self.model.spec.connection.password, "smarter")
        self.assertEqual(self.model.spec.connection.database, "smarter")
        self.assertEqual(self.model.spec.connection.timeout, 30)
        self.assertEqual(self.model.spec.connection.authenticationMethod, "tcpip")
        self.assertEqual(self.model.spec.connection.poolSize, 15)
        self.assertEqual(self.model.spec.connection.maxOverflow, 20)

    def test_django_orm_tcpip(self):
        """Test that the Django model can be initialized from the Pydantic model."""
        self.load_manifest(filename="sql-connection.yaml")
        if not self.model:
            self.fail("Model should not be None after loading the manifest")

        model_dump = self.model.spec.connection.model_dump()

        model_dump["name"] = self.model.metadata.name
        model_dump["account"] = self.account
        model_dump["description"] = self.model.metadata.description
        model_dump["kind"] = self.model.kind

        if self.model.spec.connection.password:
            clear_password = model_dump.pop("password")
            secret_name = f"test_secret_{self.hash_suffix}"
            secret = secret_factory(user_profile=self.user_profile, name=secret_name, value=clear_password)
            model_dump["password"] = secret

        model_dump = camel_to_snake_dict(model_dump)
        logger.info("test_django_orm_tcpip model_dump: %s", model_dump)

        django_model = SqlConnection(**model_dump)
        django_model.save()

        self.assertIsNotNone(django_model)
        self.assertEqual(django_model.account, self.account)

        snake_case_name = camel_to_snake(self.model.metadata.name)
        self.assertEqual(django_model.name, snake_case_name)

        self.assertEqual(django_model.db_engine, self.model.spec.connection.dbEngine)
        self.assertEqual(django_model.hostname, self.model.spec.connection.hostname)
        self.assertEqual(django_model.port, self.model.spec.connection.port)
        self.assertEqual(django_model.username, self.model.spec.connection.username)
        self.assertEqual(django_model.password.get_secret(), self.model.spec.connection.password)
        self.assertEqual(django_model.database, self.model.spec.connection.database)
        self.assertEqual(django_model.timeout, self.model.spec.connection.timeout)
        self.assertEqual(django_model.authentication_method, self.model.spec.connection.authenticationMethod)
        self.assertEqual(django_model.pool_size, self.model.spec.connection.poolSize)
        self.assertEqual(django_model.max_overflow, self.model.spec.connection.maxOverflow)
        self.assertEqual(django_model.use_ssl, False)
        self.assertEqual(django_model.ssl_cert, None)
        self.assertEqual(django_model.ssl_key, None)
        self.assertEqual(django_model.ssl_ca, None)
        self.assertEqual(django_model.proxy_host, None)
        self.assertEqual(django_model.proxy_port, None)
        self.assertEqual(django_model.proxy_username, None)
        self.assertEqual(django_model.proxy_password, None)
        self.assertEqual(django_model.ssh_known_hosts, None)
        self.assertEqual(django_model.authentication_method, self.model.spec.connection.authenticationMethod)
        self.assertEqual(django_model.pool_size, self.model.spec.connection.poolSize)
        self.assertEqual(django_model.max_overflow, self.model.spec.connection.maxOverflow)

        try:
            django_model.delete()
            secret.delete()
        except (Secret.DoesNotExist, ValueError):
            pass

    def test_model_tcpip_ssl(self):
        """Test that the Loader can load the manifest."""
        self.load_manifest(filename="sql-connection-ssl.yaml")
        if not self.loader:
            self.fail("Loader should not be None")
        if not self.model:
            self.fail("Model should not be None after loading the manifest")

        self.assertEqual(self.loader.manifest_api_version, SmarterApiVersions.V1)
        self.assertEqual(self.loader.manifest_kind, "SqlConnection")
        self.assertIsNotNone(self.loader.manifest_metadata)
        self.assertIsNotNone(self.model.spec)

        self.assertEqual(self.model.spec.connection.dbEngine, "django.db.backends.mysql")
        self.assertEqual(self.model.spec.connection.hostname, "smarter-mysql")
        self.assertEqual(self.model.spec.connection.port, 3306)
        self.assertEqual(self.model.spec.connection.username, "smarter")
        self.assertEqual(self.model.spec.connection.password, "smarter")
        self.assertEqual(self.model.spec.connection.database, "smarter")
        self.assertEqual(self.model.spec.connection.timeout, 30)
        self.assertEqual(self.model.spec.connection.useSsl, True)
        self.assertEqual(self.model.spec.connection.sslCert, "/path/to/cert.pem")
        self.assertEqual(self.model.spec.connection.sslKey, "/path/to/key.pem")
        self.assertEqual(self.model.spec.connection.sslCa, "/path/to/ca.pem")
        self.assertEqual(self.model.spec.connection.authenticationMethod, "tcpip")

    def test_django_orm_tcpip_ssl(self):
        """Test that the Django model can be initialized from the Pydantic model."""
        self.load_manifest(filename="sql-connection-ssl.yaml")
        if not self.model:
            self.fail("Model should not be None after loading the manifest")

        model_dump = self.model.spec.connection.model_dump()

        model_dump["account"] = self.account
        model_dump["name"] = self.model.metadata.name
        model_dump["description"] = self.model.metadata.description
        model_dump["kind"] = self.model.kind

        if self.model.spec.connection.password:
            clear_password = model_dump.pop("password")
            secret_name = f"test_secret_{self.hash_suffix}"
            secret = secret_factory(user_profile=self.user_profile, name=secret_name, value=clear_password)
            model_dump["password"] = secret

        model_dump = camel_to_snake_dict(model_dump)

        logger.info("test_django_orm_tcpip_ssl model_dump: %s", model_dump)

        django_model = SqlConnection(**model_dump)
        with self.assertRaises(SmarterValueError):
            django_model.save()
            logger.warning("FIX NOTE: we still need a good test case for sql tcpip_ssl connection")

        self.assertIsNotNone(django_model)
        self.assertEqual(django_model.account, self.account)

        snake_case_name = camel_to_snake(self.model.metadata.name)
        self.assertEqual(django_model.name, snake_case_name)

        self.assertEqual(django_model.db_engine, self.model.spec.connection.dbEngine)
        self.assertEqual(django_model.hostname, self.model.spec.connection.hostname)
        self.assertEqual(django_model.port, self.model.spec.connection.port)
        self.assertEqual(django_model.username, self.model.spec.connection.username)
        self.assertEqual(django_model.password.get_secret(), self.model.spec.connection.password)
        self.assertEqual(django_model.database, self.model.spec.connection.database)
        self.assertEqual(django_model.timeout, self.model.spec.connection.timeout)
        self.assertEqual(django_model.use_ssl, True)
        self.assertEqual(django_model.ssl_cert, self.model.spec.connection.sslCert)
        self.assertEqual(django_model.ssl_key, self.model.spec.connection.sslKey)
        self.assertEqual(django_model.ssl_ca, self.model.spec.connection.sslCa)
        self.assertEqual(django_model.authentication_method, self.model.spec.connection.authenticationMethod)
        self.assertEqual(django_model.pool_size, self.model.spec.connection.poolSize)
        self.assertEqual(django_model.max_overflow, self.model.spec.connection.maxOverflow)
        self.assertEqual(django_model.proxy_host, None)
        self.assertEqual(django_model.proxy_port, None)
        self.assertEqual(django_model.proxy_username, None)
        self.assertEqual(django_model.proxy_password, None)
        self.assertEqual(django_model.ssh_known_hosts, None)

        try:
            django_model.delete()
            secret.delete()
        except (Secret.DoesNotExist, ValueError):
            pass

    def test_model_tcpip_ssh(self):
        """Test that the Loader can load the self._manifest["spec"]["connection"]["username"]."""
        self.load_manifest(filename="sql-connection-ssh.yaml")
        if not self.loader:
            self.fail("Loader should not be None after loading the manifest")
        if not self.model:
            self.fail("Model should not be None after loading the manifest")

        self.assertEqual(self.loader.manifest_api_version, SmarterApiVersions.V1)
        self.assertEqual(self.loader.manifest_kind, "SqlConnection")
        self.assertIsNotNone(self.loader.manifest_metadata)
        self.assertIsNotNone(self.model.spec)

        self.assertEqual(self.model.spec.connection.dbEngine, "django.db.backends.mysql")
        self.assertEqual(self.model.spec.connection.hostname, "smarter-mysql")
        self.assertEqual(self.model.spec.connection.port, 3306)
        self.assertEqual(self.model.spec.connection.username, "smarter")
        self.assertEqual(self.model.spec.connection.password, "smarter")
        self.assertEqual(self.model.spec.connection.database, "smarter")
        self.assertEqual(self.model.spec.connection.timeout, 30)
        self.assertEqual(self.model.spec.connection.proxyHost, "proxy.example.com")
        self.assertEqual(self.model.spec.connection.proxyPort, 8080)
        self.assertEqual(self.model.spec.connection.proxyUsername, "proxyUser")
        self.assertEqual(self.model.spec.connection.proxyPassword, "proxyPass")
        self.assertEqual(self.model.spec.connection.sshKnownHosts, "/path/to/known_hosts")
        self.assertEqual(self.model.spec.connection.authenticationMethod, "tcpip_ssh")
        self.assertEqual(self.model.spec.connection.poolSize, 5)
        self.assertEqual(self.model.spec.connection.maxOverflow, 10)
        self.assertEqual(self.model.spec.connection.authenticationMethod, "tcpip_ssh")
        self.assertEqual(self.model.spec.connection.useSsl, False)
        self.assertEqual(self.model.spec.connection.sslCert, None)
        self.assertEqual(self.model.spec.connection.sslKey, None)
        self.assertEqual(self.model.spec.connection.sslCa, None)

    def test_django_orm_tcpip_ssh(self):
        """Test that the Django model can be initialized from the Pydantic model."""
        self.load_manifest(filename="sql-connection-ssh.yaml")
        if not self.model:
            self.fail("Model should not be None after loading the manifest")

        model_dump = self.model.spec.connection.model_dump()

        model_dump["account"] = self.account
        model_dump["name"] = self.model.metadata.name
        model_dump["description"] = self.model.metadata.description
        model_dump["kind"] = self.model.kind

        if self.model.spec.connection.password:
            clear_password = model_dump.pop("password")
            secret_name = f"test_secret_{self.hash_suffix}"
            secret = secret_factory(user_profile=self.user_profile, name=secret_name, value=clear_password)
            model_dump["password"] = secret

        if self.model.spec.connection.proxyPassword:
            clear_proxy_password = model_dump.pop("proxyPassword")
            proxy_secret_name = f"test_proxy_secret_{self.hash_suffix}"
            proxy_secret = secret_factory(
                user_profile=self.user_profile, name=proxy_secret_name, value=clear_proxy_password
            )
            model_dump["proxyPassword"] = proxy_secret

        model_dump = camel_to_snake_dict(model_dump)

        logger.info("test_django_orm_tcpip_ssh model_dump: %s", model_dump)

        # pylint: disable=W0612
        example_output = {
            "dbEngine": "django.db.backends.mysql",
            "hostname": "smarter-mysql",
            "port": 3306,
            "database": "smarter",
            "username": "smarter",
            "timeout": 30,
            "useSsl": True,
            "sslCert": "/path/to/cert.pem",
            "sslKey": "/path/to/key.pem",
            "sslCa": "/path/to/ca.pem",
            "proxyHost": None,
            "proxyPort": None,
            "proxyUsername": None,
            "proxyPassword": None,
            "sshKnownHosts": None,
            "poolSize": 5,
            "maxOverflow": 10,
            "authenticationMethod": "none",
            "account": "<Account: TestAccount_AdminUser_c8383754ac60882b>",
            "name": "test_sql_connection",
            "description": "points to the Django mysql database",
            "password": "<Secret: test_secret_968d486895af353a>",
        }

        django_model = SqlConnection(**model_dump)
        with self.assertRaises(SmarterValueError):
            django_model.save()
            logger.warning("FIX NOTE: we still need a good test case for sql tcpip_ssh connection")

        self.assertIsNotNone(django_model)
        self.assertEqual(django_model.account, self.account)

        snake_case_name = camel_to_snake(self.model.metadata.name)
        self.assertEqual(django_model.name, snake_case_name)

        self.assertEqual(django_model.db_engine, self.model.spec.connection.dbEngine)
        self.assertEqual(django_model.hostname, self.model.spec.connection.hostname)
        self.assertEqual(django_model.port, self.model.spec.connection.port)
        self.assertEqual(django_model.username, self.model.spec.connection.username)
        self.assertEqual(django_model.password.get_secret(), self.model.spec.connection.password)
        self.assertEqual(django_model.database, self.model.spec.connection.database)
        self.assertEqual(django_model.timeout, self.model.spec.connection.timeout)
        self.assertEqual(django_model.proxy_host, self.model.spec.connection.proxyHost)
        self.assertEqual(django_model.proxy_port, self.model.spec.connection.proxyPort)
        self.assertEqual(django_model.proxy_username, self.model.spec.connection.proxyUsername)
        self.assertEqual(django_model.proxy_password.get_secret(), self.model.spec.connection.proxyPassword)
        self.assertEqual(django_model.ssh_known_hosts, self.model.spec.connection.sshKnownHosts)
        self.assertEqual(django_model.authentication_method, self.model.spec.connection.authenticationMethod)
        self.assertEqual(django_model.pool_size, self.model.spec.connection.poolSize)
        self.assertEqual(django_model.max_overflow, self.model.spec.connection.maxOverflow)

        try:
            django_model.delete()
            secret.delete()
        except (Secret.DoesNotExist, ValueError):
            pass
