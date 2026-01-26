"""
Test ApiConnection Django ORM and Manifest Loader.

mcdaniel jan-2026: TestApiConnectionLegacy should be refactored. it contains a mix
of Pydantic model tests combined with Django ORM model tests,
which really should be (or might already be) in the broker test bank.
"""

import logging
import os
from typing import Optional

from django.core.exceptions import ValidationError as DjangoValidationError
from pydantic_core import ValidationError as PydanticValidationError

from smarter.apps.account.models import Secret
from smarter.apps.plugin.const import DATA_PATH as PLUGIN_DATA_PATH
from smarter.apps.plugin.manifest.models.api_connection.enum import AuthMethods
from smarter.apps.plugin.manifest.models.api_connection.model import SAMApiConnection
from smarter.apps.plugin.manifest.models.api_connection.spec import (
    SAMApiConnectionSpec,
)
from smarter.apps.plugin.manifest.models.common.connection.metadata import (
    SAMConnectionCommonMetadata,
)
from smarter.apps.plugin.manifest.models.common.connection.status import (
    SAMConnectionCommonStatus,
)
from smarter.apps.plugin.models import ApiConnection
from smarter.apps.plugin.tests.base_classes import TestConnectionBase
from smarter.apps.plugin.tests.factories import secret_factory
from smarter.common.helpers.console_helpers import formatted_text
from smarter.common.utils import camel_to_snake, camel_to_snake_dict
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.loader import SAMLoader
from smarter.lib.manifest.tests.test_broker_base import TestSAMBrokerBaseClass

logger = logging.getLogger(__name__)
MANIFEST_PATH_API_CONNECTION = os.path.abspath(
    os.path.join(PLUGIN_DATA_PATH, "manifest", "brokers", "tests", "data", "api-connection.yaml")
)
"""
Path to the Api plugin manifest file 'api-connection.yaml' which
contains the actual connection parameters for the remote test database.

Note that we're borrowing the api-connection.yaml file from the
broker tests.
"""
HERE = __name__


class TestSAMApiConnection(TestSAMBrokerBaseClass):
    """
    Test SAMApiConnection Pydantic model.

    .. note::

        TestSAMBrokerBaseClass is generically useful for testing SAM-based
        Pydantic models.
    """

    test_sam_api_plugin_logger_prefix = formatted_text(f"{HERE}.TestSAMApiPlugin()")

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        logger.debug("%s.setUpClass()", cls.test_sam_api_plugin_logger_prefix)
        cls.loader = SAMLoader(file_path=MANIFEST_PATH_API_CONNECTION)

    @classmethod
    def tearDownClass(cls):
        logger.debug("%s.tearDownClass()", cls.test_sam_api_plugin_logger_prefix)
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self._manifest_filespec = MANIFEST_PATH_API_CONNECTION

    def test_missing_required_fields(self):
        """Test that missing required fields raises ValidationError."""
        with self.assertRaises(PydanticValidationError):
            SAMApiConnection()  # type: ignore

    def test_invalid_field_types(self):
        """Test that wrong types for fields raises ValidationError."""
        with self.assertRaises(PydanticValidationError):
            SAMApiConnection(
                apiVersion=123,  # type: ignore
                kind=456,  # type: ignore
                metadata=self.loader.manifest_metadata,  # type: ignore
                spec=self.loader.manifest_spec,  # type: ignore
            )

    def test_alternative_initialization(self):
        """
        Test that the SAMApiConnection model can be initialized using a single dict.
        """
        data = {
            "apiVersion": self.loader.manifest_api_version,
            "kind": self.loader.manifest_kind,
            "metadata": self.loader.manifest_metadata,
            "spec": self.loader.manifest_spec,
        }
        SAMApiConnection(**data)

    def test_immutability(self):
        """Test that the SAMApiConnection model is immutable after creation."""
        model = SAMApiConnection(
            apiVersion=self.loader.manifest_api_version,
            kind=self.loader.manifest_kind,
            metadata=SAMConnectionCommonMetadata(**self.loader.manifest_metadata),
            spec=SAMApiConnectionSpec(**self.loader.manifest_spec),
        )
        with self.assertRaises(PydanticValidationError):
            model.kind = "NewKind"

    def test_invalid_spec_structure(self):
        """Test that invalid spec structure raises ValidationError."""
        with self.assertRaises(PydanticValidationError):
            SAMApiConnection(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMConnectionCommonMetadata(**self.loader.manifest_metadata),
                spec={"not": "a valid spec"},  # type: ignore
            )

    def test_invalid_metadata_structure(self):
        """Test that invalid metadata structure raises ValidationError."""
        with self.assertRaises(PydanticValidationError):
            SAMApiConnection(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata={"not": "a valid metadata"},  # type: ignore
                spec=SAMApiConnectionSpec(**self.loader.manifest_spec),
            )

    def test_repr_and_str(self):
        """Test that model __repr__ and __str__ do not raise and include class name."""
        model = SAMApiConnection(
            apiVersion=self.loader.manifest_api_version,
            kind=self.loader.manifest_kind,
            metadata=SAMConnectionCommonMetadata(**self.loader.manifest_metadata),
            spec=SAMApiConnectionSpec(**self.loader.manifest_spec),
        )
        self.assertIn("SAMApiConnection", repr(model))
        self.assertIn("SAMApiConnection", str(model))

    def test_connection_required_fields(self):
        """Test that required fields in spec.connection are enforced."""
        manifest_spec = dict(self.loader.manifest_spec)
        # Remove a required field, e.g., baseUrl
        if "connection" in manifest_spec:
            manifest_spec["connection"] = dict(manifest_spec["connection"])
            if "baseUrl" in manifest_spec["connection"]:
                del manifest_spec["connection"]["baseUrl"]
        with self.assertRaises(PydanticValidationError):
            SAMApiConnection(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMConnectionCommonMetadata(**self.loader.manifest_metadata),
                spec=SAMApiConnectionSpec(**manifest_spec),
            )

    def test_connection_wrong_type(self):
        """Test that wrong type for a connection field raises ValidationError."""
        manifest_spec = dict(self.loader.manifest_spec)
        if "connection" in manifest_spec:
            manifest_spec["connection"] = dict(manifest_spec["connection"])
            manifest_spec["connection"]["timeout"] = "notanint"
        with self.assertRaises(PydanticValidationError):
            SAMApiConnection(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMConnectionCommonMetadata(**self.loader.manifest_metadata),
                spec=SAMApiConnectionSpec(**manifest_spec),
            )

    def test_connection_optional_fields(self):
        """Test that optional fields in spec.connection can be omitted or set to None."""
        manifest_spec = dict(self.loader.manifest_spec)
        if "connection" in manifest_spec:
            manifest_spec["connection"] = dict(manifest_spec["connection"])
            manifest_spec["connection"]["proxyHost"] = None
            manifest_spec["connection"]["proxyPort"] = None
        model = SAMApiConnection(
            apiVersion=self.loader.manifest_api_version,
            kind=self.loader.manifest_kind,
            metadata=SAMConnectionCommonMetadata(**self.loader.manifest_metadata),
            spec=SAMApiConnectionSpec(**manifest_spec),
        )
        self.assertIsNone(model.spec.connection.proxyHost)
        self.assertIsNone(model.spec.connection.proxyPort)

    def test_connection_enum_fields(self):
        """Test that enum fields in spec.connection only accept valid values."""
        manifest_spec = dict(self.loader.manifest_spec)
        if "connection" in manifest_spec:
            manifest_spec["connection"] = dict(manifest_spec["connection"])
            manifest_spec["connection"]["authMethod"] = "notavalidmethod"
        with self.assertRaises(Exception):
            SAMApiConnection(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMConnectionCommonMetadata(**self.loader.manifest_metadata),
                spec=SAMApiConnectionSpec(**manifest_spec),
            )

    def test_connection_numeric_constraints(self):
        """Test that numeric fields in spec.connection respect constraints (e.g., port range)."""
        manifest_spec = dict(self.loader.manifest_spec)
        if "connection" in manifest_spec:
            manifest_spec["connection"] = dict(manifest_spec["connection"])
            manifest_spec["connection"]["proxyPort"] = 70000  # invalid port
        with self.assertRaises(Exception):
            SAMApiConnection(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMConnectionCommonMetadata(**self.loader.manifest_metadata),
                spec=SAMApiConnectionSpec(**manifest_spec),
            )

    def test_connection_repr_and_str(self):
        """Test that connection __repr__ and __str__ do not raise and include class name."""
        model = SAMApiConnection(
            apiVersion=self.loader.manifest_api_version,
            kind=self.loader.manifest_kind,
            metadata=SAMConnectionCommonMetadata(**self.loader.manifest_metadata),
            spec=SAMApiConnectionSpec(**self.loader.manifest_spec),
        )

        def test_model_initialization(self):
            """Test that the SAMSqlConnection model can be initialized with valid data."""
            SAMApiConnection(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest.kind,
                metadata=SAMConnectionCommonMetadata(**self.loader.manifest_metadata),
                spec=SAMApiConnectionSpec(**self.loader.manifest_spec),
                status=(
                    SAMConnectionCommonStatus(**self.loader.manifest_status)
                    if self.loader and self.loader.manifest_status
                    else None
                ),
            )


class TestApiConnectionLegacy(TestConnectionBase):
    """Test ApiConnection Django ORM and Manifest Loader"""

    _model: Optional[SAMApiConnection] = None

    @property
    def model(self) -> SAMApiConnection:
        # override to create a SAMApiConnection pydantic model from the loader
        if not self._model and self.loader:
            self._model = SAMApiConnection(**self.loader.pydantic_model_dump())
            self.assertIsNotNone(self._model)
        if not isinstance(self._model, SAMApiConnection):
            raise TypeError(f"Expected SAMApiConnection, got {type(self._model)}")
        return self._model

    def test_valid_manifest(self):
        """
        Test valid file path and that we can instantiate without errors
        """
        self.load_manifest(filename="api-connection.yaml")
        self.assertIsNotNone(self.model)
        self.assertIsNotNone(self.model.metadata)
        self.assertIsNotNone(self.model.spec)
        self.assertIsNotNone(self.model.spec.connection)

        snake_case_name = camel_to_snake(self.model.metadata.name)
        self.assertEqual(self.model.metadata.name, snake_case_name)

        self.assertEqual(self.model.metadata.description, "points to smarter api localhost")
        self.assertEqual(self.model.spec.connection.baseUrl, "http://localhost:9357/")
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
        if not isinstance(self.manifest, dict):
            self.fail("Manifest should be a dictionary after loading")

        invalid_base_url = "not-a-valid-url"
        self.manifest["spec"]["connection"]["baseUrl"] = invalid_base_url
        self._loader = None
        self._model = None
        with self.assertRaises((SAMValidationError, PydanticValidationError, DjangoValidationError)):
            print(self.model)

    def test_validate_timeout_negative_value(self):
        """Test that the timeout validator raises an error for negative values."""
        self.load_manifest(filename="api-connection.yaml")
        if not isinstance(self.manifest, dict):
            self.fail("Manifest should be a dictionary after loading")

        invalid_timeout = -10
        self.manifest["spec"]["connection"]["timeout"] = invalid_timeout
        self._loader = None
        self._model = None
        with self.assertRaises(PydanticValidationError) as context:
            print(self.model)
        self.assertIn(
            "Input should be greater than or equal to 1",
            str(context.exception),
        )

    def test_validate_timeout_valid_value(self):
        """Test that the timeout validator does not raise an error for valid values."""
        self.load_manifest(filename="api-connection.yaml")
        if not isinstance(self.manifest, dict):
            self.fail("Manifest should be a dictionary after loading")

        invalid_timeout = 30
        self.manifest["spec"]["connection"]["timeout"] = invalid_timeout
        self._loader = None
        self._model = None
        self.assertIsNotNone(self.model)

    def test_validate_auth_method_invalid_value(self):
        """Test that the authMethod validator raises an error for invalid values."""
        self.load_manifest(filename="api-connection.yaml")
        if not isinstance(self.manifest, dict):
            self.fail("Manifest should be a dictionary after loading")

        invalid_auth_method = "nonsense"
        self.manifest["spec"]["connection"]["authMethod"] = invalid_auth_method
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
        if not isinstance(self.manifest, dict):
            self.fail("Manifest should be a dictionary after loading")

        invalid_base_url = None
        self.manifest["spec"]["connection"]["baseUrl"] = invalid_base_url
        self._loader = None
        self._model = None
        with self.assertRaises(PydanticValidationError) as context:
            print(self.model)
        self.assertIn(
            "Input should be a valid string",
            str(context.exception),
        )

    def test_validate_proxy_port_invalid_type(self):
        """Test that the proxyPort validator raises an error for non-integer values."""
        self.load_manifest(filename="api-connection.yaml")
        if not isinstance(self.manifest, dict):
            self.fail("Manifest should be a dictionary after loading")

        invalid_proxy_port = "not-a-number"
        self.manifest["spec"]["connection"]["proxyPort"] = invalid_proxy_port
        self._loader = None
        self._model = None
        with self.assertRaises(PydanticValidationError) as context:
            print(self.model)
        self.assertIn(
            "Input should be a valid integer",
            str(context.exception),
        )

    def test_validate_proxy_port_empty_value(self):
        """Test that the proxyPort validator allow missing values."""
        self.load_manifest(filename="api-connection.yaml")
        if not isinstance(self.manifest, dict):
            self.fail("Manifest should be a dictionary after loading")

        invalid_proxy_port = None
        self.manifest["spec"]["connection"]["proxyPort"] = invalid_proxy_port
        self._loader = None
        self._model = None
        self.assertIsNotNone(self.model)

    def test_validate_proxy_username_empty_value(self):
        """Test that the proxyUsername validator allows empty values."""
        self.load_manifest(filename="api-connection.yaml")
        if not isinstance(self.manifest, dict):
            self.fail("Manifest should be a dictionary after loading")

        invalid_proxy_password = None
        self.manifest["spec"]["connection"]["proxyUsername"] = invalid_proxy_password
        self._loader = None
        self._model = None
        self.assertIsNotNone(self.model)

    def test_validate_proxy_password_empty_value(self):
        """Test that the proxyPassword validator allows empty values."""
        self.load_manifest(filename="api-connection.yaml")
        if not isinstance(self.manifest, dict):
            self.fail("Manifest should be a dictionary after loading")

        invalid_proxy_password = None
        self.manifest["spec"]["connection"]["proxyPassword"] = invalid_proxy_password
        self._loader = None
        self._model = None
        self.assertIsNotNone(self.model)

    def test_validate_base_url_invalid_protocol(self):
        """Test that the baseUrl validator raises an error for unsupported protocols."""
        self.load_manifest(filename="api-connection.yaml")
        if not isinstance(self.manifest, dict):
            self.fail("Manifest should be a dictionary after loading")

        invalid_base_url = "ftp://example.com"
        self.manifest["spec"]["connection"]["baseUrl"] = invalid_base_url
        self._loader = None
        self._model = None
        with self.assertRaises((AssertionError, SAMValidationError, PydanticValidationError, DjangoValidationError)):
            print(self.model)

    def test_validate_timeout_zero_value(self):
        """Test that the timeout validator raises an error for a zero value."""
        self.load_manifest(filename="api-connection.yaml")
        if not isinstance(self.manifest, dict):
            self.fail("Manifest should be a dictionary after loading")

        invalid_timeout = 0
        self.manifest["spec"]["connection"]["timeout"] = invalid_timeout
        self._loader = None
        self._model = None
        with self.assertRaises(PydanticValidationError) as context:
            print(self.model)
        self.assertIn(
            "Input should be greater than or equal to 1",
            str(context.exception),
        )

    def test_validate_auth_method_empty_value(self):
        """Test that the authMethod validator raises an error for an empty value."""
        self.load_manifest(filename="api-connection.yaml")
        if not isinstance(self.manifest, dict):
            self.fail("Manifest should be a dictionary after loading")

        invalid_auth_method = ""
        self.manifest["spec"]["connection"]["authMethod"] = invalid_auth_method
        self._loader = None
        self._model = None
        with self.assertRaises(PydanticValidationError) as context:
            print(self.model)
        self.assertIn(
            "Input should be a valid string",
            str(context.exception),
        )

    def test_validate_proxy_protocol_invalid_value(self):
        """Test that the proxyProtocol validator raises an error for invalid values."""
        self.load_manifest(filename="api-connection.yaml")
        if not isinstance(self.manifest, dict):
            self.fail("Manifest should be a dictionary after loading")

        invalid_proxy_protocol = "unsupported-protocol"
        self.manifest["spec"]["connection"]["proxyProtocol"] = invalid_proxy_protocol
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
        if not isinstance(self.manifest, dict):
            self.fail("Manifest should be a dictionary after loading")

        invalid_proxy_host = None
        self.manifest["spec"]["connection"]["proxyHost"] = invalid_proxy_host
        self._loader = None
        self._model = None
        self.assertIsNotNone(self.model)

    def test_validate_proxy_port_out_of_range(self):
        """Test that the proxyPort validator raises an error for out-of-range values."""
        self.load_manifest(filename="api-connection.yaml")
        if not isinstance(self.manifest, dict):
            self.fail("Manifest should be a dictionary after loading")

        invalid_proxy_port = 70000  # Port numbers must be between 1 and 65535
        self.manifest["spec"]["connection"]["proxyPort"] = invalid_proxy_port
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
        if not isinstance(self.manifest, dict):
            self.fail("Manifest should be a dictionary after loading")

        invalid_api_key = None
        self.manifest["spec"]["connection"]["apiKey"] = invalid_api_key
        self._loader = None
        self._model = None
        self.assertIsNotNone(self.model)

    def test_validate_api_key_empty_value(self):
        """Test that the apiKey validator allows an empty string."""
        self.load_manifest(filename="api-connection.yaml")
        if not isinstance(self.manifest, dict):
            self.fail("Manifest should be a dictionary after loading")

        invalid_api_key = ""
        self.manifest["spec"]["connection"]["apiKey"] = invalid_api_key
        self._loader = None
        self._model = None
        self.assertIsNotNone(self.model)

    def test_django_orm(self):
        """Test that the Django model can be initialized from the Pydantic model."""
        self.load_manifest(filename="api-connection.yaml")
        model_dump = self.model.spec.connection.model_dump()

        model_dump["user_profile"] = self.user_profile
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
        self.assertEqual(django_model.user_profile, self.user_profile)

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
