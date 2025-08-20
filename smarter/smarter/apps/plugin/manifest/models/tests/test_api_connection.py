"""Test ApiConnection Django ORM and Manifest Loader."""

import logging

from pydantic_core import ValidationError

from smarter.apps.account.models import Secret
from smarter.apps.plugin.manifest.models.api_connection.enum import AuthMethods
from smarter.apps.plugin.manifest.models.api_connection.model import SAMApiConnection
from smarter.apps.plugin.models import ApiConnection
from smarter.apps.plugin.tests.base_classes import TestConnectionBase
from smarter.apps.plugin.tests.factories import secret_factory
from smarter.common.utils import camel_to_snake, camel_to_snake_dict
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.manifest.exceptions import SAMValidationError


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PLUGIN_LOGGING) and level >= logging.INFO


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class TestApiConnection(TestConnectionBase):
    """Test ApiConnection Django ORM and Manifest Loader"""

    _model: SAMApiConnection = None

    @property
    def model(self) -> SAMApiConnection:
        # override to create a SAMApiConnection pydantic model from the loader
        if not self._model and self.loader:
            self._model = SAMApiConnection(**self.loader.pydantic_model_dump())
            self.assertIsNotNone(self._model)
        return self._model

    def test_valid_manifest(self):
        """
        Test valid file path and that we can instantiate without errors
        """
        self.load_manifest(filename="api-connection.yaml")
        self.assertIsNotNone(self.model)

        snake_case_name = camel_to_snake(self.model.metadata.name)
        self.assertEqual(self.model.metadata.name, snake_case_name)

        self.assertEqual(self.model.metadata.description, "points to smarter api localhost")
        self.assertEqual(self.model.spec.connection.baseUrl, "http://localhost:8000/")
        self.assertEqual(self.model.spec.connection.apiKey, "12345-abcde-67890-fghij")
        self.assertEqual(self.model.spec.connection.timeout, 10)
        self.assertEqual(self.model.spec.connection.authMethod, AuthMethods.TOKEN.value)
        self.assertEqual(self.model.spec.connection.proxyProtocol, "http")
        self.assertEqual(self.model.spec.connection.proxyHost, "proxy.example.com")
        self.assertEqual(self.model.spec.connection.proxyPort, 8080)
        self.assertEqual(self.model.spec.connection.proxyUsername, "proxyUser")
        self.assertEqual(self.model.spec.connection.proxyPassword, "proxyPass")

    def test_validate_base_url_invalid_value(self):
        """Test that the baseUrl validator raises an error for invalid values."""
        self.load_manifest(filename="api-connection.yaml")

        invalid_base_url = "not-a-valid-url"
        self._manifest["spec"]["connection"]["baseUrl"] = invalid_base_url
        self._loader = None
        self._model = None
        with self.assertRaises(SAMValidationError) as context:
            print(self.model)
        self.assertIn(
            f"Invalid root domain or protocol: {invalid_base_url}. Must be a valid domain on http or https",
            str(context.exception),
        )

    def test_validate_timeout_negative_value(self):
        """Test that the timeout validator raises an error for negative values."""
        self.load_manifest(filename="api-connection.yaml")

        invalid_timeout = -10
        self._manifest["spec"]["connection"]["timeout"] = invalid_timeout
        self._loader = None
        self._model = None
        with self.assertRaises(ValidationError) as context:
            print(self.model)
        self.assertIn(
            "Input should be greater than or equal to 1",
            str(context.exception),
        )

    def test_validate_timeout_valid_value(self):
        """Test that the timeout validator does not raise an error for valid values."""
        self.load_manifest(filename="api-connection.yaml")

        invalid_timeout = 30
        self._manifest["spec"]["connection"]["timeout"] = invalid_timeout
        self._loader = None
        self._model = None
        self.assertIsNotNone(self.model)

    def test_validate_auth_method_invalid_value(self):
        """Test that the authMethod validator raises an error for invalid values."""
        self.load_manifest(filename="api-connection.yaml")

        invalid_auth_method = "nonsense"
        self._manifest["spec"]["connection"]["authMethod"] = invalid_auth_method
        self._loader = None
        self._model = None
        with self.assertRaises(SAMValidationError) as context:
            print(self.model)
        valid_methods = AuthMethods.all_values()
        self.assertIn(
            f"Invalid authentication method: {invalid_auth_method}. Must be one of {valid_methods}.",
            str(context.exception),
        )

    def test_validate_base_url_null_value(self):
        """Test that the baseUrl validator raises an error for null values."""
        self.load_manifest(filename="api-connection.yaml")

        invalid_base_url = None
        self._manifest["spec"]["connection"]["baseUrl"] = invalid_base_url
        self._loader = None
        self._model = None
        with self.assertRaises(ValidationError) as context:
            print(self.model)
        self.assertIn(
            "Input should be a valid string",
            str(context.exception),
        )

    def test_validate_proxy_port_invalid_type(self):
        """Test that the proxyPort validator raises an error for non-integer values."""
        self.load_manifest(filename="api-connection.yaml")

        invalid_proxy_port = "not-a-number"
        self._manifest["spec"]["connection"]["proxyPort"] = invalid_proxy_port
        self._loader = None
        self._model = None
        with self.assertRaises(ValidationError) as context:
            print(self.model)
        self.assertIn(
            "Input should be a valid integer",
            str(context.exception),
        )

    def test_validate_proxy_port_empty_value(self):
        """Test that the proxyPort validator allow missing values."""
        self.load_manifest(filename="api-connection.yaml")

        invalid_proxy_port = None
        self._manifest["spec"]["connection"]["proxyPort"] = invalid_proxy_port
        self._loader = None
        self._model = None
        self.assertIsNotNone(self.model)

    def test_validate_proxy_username_empty_value(self):
        """Test that the proxyUsername validator allows empty values."""
        self.load_manifest(filename="api-connection.yaml")

        invalid_proxy_password = None
        self._manifest["spec"]["connection"]["proxyUsername"] = invalid_proxy_password
        self._loader = None
        self._model = None
        self.assertIsNotNone(self.model)

    def test_validate_proxy_password_empty_value(self):
        """Test that the proxyPassword validator allows empty values."""
        self.load_manifest(filename="api-connection.yaml")

        invalid_proxy_password = None
        self._manifest["spec"]["connection"]["proxyPassword"] = invalid_proxy_password
        self._loader = None
        self._model = None
        self.assertIsNotNone(self.model)

    def test_validate_base_url_invalid_protocol(self):
        """Test that the baseUrl validator raises an error for unsupported protocols."""
        self.load_manifest(filename="api-connection.yaml")

        invalid_base_url = "ftp://example.com"
        self._manifest["spec"]["connection"]["baseUrl"] = invalid_base_url
        self._loader = None
        self._model = None
        with self.assertRaises(SAMValidationError) as context:
            print(self.model)
        self.assertIn(
            f"Invalid root domain or protocol: {invalid_base_url}. Must be a valid domain on http or https",
            str(context.exception),
        )

    def test_validate_timeout_zero_value(self):
        """Test that the timeout validator raises an error for a zero value."""
        self.load_manifest(filename="api-connection.yaml")

        invalid_timeout = 0
        self._manifest["spec"]["connection"]["timeout"] = invalid_timeout
        self._loader = None
        self._model = None
        with self.assertRaises(ValidationError) as context:
            print(self.model)
        self.assertIn(
            "Input should be greater than or equal to 1",
            str(context.exception),
        )

    def test_validate_auth_method_empty_value(self):
        """Test that the authMethod validator raises an error for an empty value."""
        self.load_manifest(filename="api-connection.yaml")

        invalid_auth_method = ""
        self._manifest["spec"]["connection"]["authMethod"] = invalid_auth_method
        self._loader = None
        self._model = None
        with self.assertRaises(SAMValidationError) as context:
            print(self.model)
        self.assertIn(
            f"Invalid authentication method: . Must be one of {AuthMethods.all_values()}.",
            str(context.exception),
        )

    def test_validate_proxy_protocol_invalid_value(self):
        """Test that the proxyProtocol validator raises an error for invalid values."""
        self.load_manifest(filename="api-connection.yaml")

        invalid_proxy_protocol = "unsupported-protocol"
        self._manifest["spec"]["connection"]["proxyProtocol"] = invalid_proxy_protocol
        self._loader = None
        self._model = None
        with self.assertRaises(SAMValidationError) as context:
            print(self.model)
        valid_protocols = ["http", "https"]
        self.assertIn(
            f"Invalid protocol {invalid_proxy_protocol}. Proxy protocol must be in {valid_protocols}",
            str(context.exception),
        )

    def test_validate_proxy_host_null_value(self):
        """Test that the proxyHost validator allows null values."""
        self.load_manifest(filename="api-connection.yaml")

        invalid_proxy_host = None
        self._manifest["spec"]["connection"]["proxyHost"] = invalid_proxy_host
        self._loader = None
        self._model = None
        self.assertIsNotNone(self.model)

    def test_validate_proxy_port_out_of_range(self):
        """Test that the proxyPort validator raises an error for out-of-range values."""
        self.load_manifest(filename="api-connection.yaml")

        invalid_proxy_port = 70000  # Port numbers must be between 1 and 65535
        self._manifest["spec"]["connection"]["proxyPort"] = invalid_proxy_port
        self._loader = None
        self._model = None
        with self.assertRaises(SAMValidationError) as context:
            print(self.model)
        self.assertIn(
            f"Invalid proxy host: {invalid_proxy_port}. Must be between 1 and 65535",
            str(context.exception),
        )

    def test_validate_api_key_null_value(self):
        """Test that the apiKey validator allows null values."""
        self.load_manifest(filename="api-connection.yaml")

        invalid_api_key = None
        self._manifest["spec"]["connection"]["apiKey"] = invalid_api_key
        self._loader = None
        self._model = None
        self.assertIsNotNone(self.model)

    def test_validate_api_key_empty_value(self):
        """Test that the apiKey validator allows an empty string."""
        self.load_manifest(filename="api-connection.yaml")

        invalid_api_key = ""
        self._manifest["spec"]["connection"]["apiKey"] = invalid_api_key
        self._loader = None
        self._model = None
        self.assertIsNotNone(self.model)

    def test_django_orm(self):
        """Test that the Django model can be initialized from the Pydantic model."""
        self.load_manifest(filename="api-connection.yaml")
        model_dump = self.model.spec.connection.model_dump()

        model_dump["account"] = self.account
        model_dump["name"] = self.model.metadata.name
        model_dump["description"] = self.model.metadata.description
        model_dump["kind"] = self.model.kind

        if self.model.spec.connection.apiKey:
            clear_api_key = model_dump.pop("apiKey")
            secret_name = f"test_secret_{self.hash_suffix}"
            secret = secret_factory(user_profile=self.user_profile, name=secret_name, value=clear_api_key)
            model_dump["apiKey"] = secret

        if self.model.spec.connection.proxyPassword:
            clear_proxy_password = model_dump.pop("proxyPassword")
            proxy_secret_name = f"test_proxy_secret_{self.hash_suffix}"
            proxy_secret = secret_factory(
                user_profile=self.user_profile, name=proxy_secret_name, value=clear_proxy_password
            )
            model_dump["proxyPassword"] = proxy_secret

        model_dump = camel_to_snake_dict(model_dump)
        django_model = ApiConnection(**model_dump)
        django_model.save()

        self.assertIsNotNone(django_model)
        self.assertEqual(django_model.account, self.account)

        snake_case_name = camel_to_snake(self.model.metadata.name)
        self.assertEqual(django_model.name, snake_case_name)

        self.assertEqual(django_model.base_url, self.model.spec.connection.baseUrl)
        self.assertEqual(django_model.api_key.get_secret(), self.model.spec.connection.apiKey)
        self.assertEqual(django_model.auth_method, self.model.spec.connection.authMethod)
        self.assertEqual(django_model.timeout, self.model.spec.connection.timeout)
        self.assertEqual(django_model.proxy_protocol, self.model.spec.connection.proxyProtocol)
        self.assertEqual(django_model.proxy_host, self.model.spec.connection.proxyHost)
        self.assertEqual(django_model.proxy_port, self.model.spec.connection.proxyPort)
        self.assertEqual(django_model.proxy_username, self.model.spec.connection.proxyUsername)
        self.assertEqual(django_model.proxy_password.get_secret(), self.model.spec.connection.proxyPassword)
        try:
            django_model.delete()
            secret.delete()
        except (Secret.DoesNotExist, ValueError):
            pass
