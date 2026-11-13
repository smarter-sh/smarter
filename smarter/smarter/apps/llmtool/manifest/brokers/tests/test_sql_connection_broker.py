# pylint: disable=wrong-import-position
"""Test SAMSqlConnectionBroker."""

import os

from django.http import HttpRequest
from pydantic_core import ValidationError
from taggit.managers import TaggableManager, _TaggableManager

from smarter.apps.connection.manifest.brokers.sql_connection import (
    SAMSqlConnectionBroker,
)
from smarter.apps.connection.manifest.models.common.connection.metadata import (
    SAMConnectionCommonMetadata,
)
from smarter.apps.connection.manifest.models.sql_connection.model import (
    SAMSqlConnection,
)
from smarter.apps.connection.manifest.models.sql_connection.spec import (
    SAMSqlConnectionSpec,
)
from smarter.apps.connection.models import SqlConnection
from smarter.apps.secret.models import Secret
from smarter.lib import json, logging
from smarter.lib.manifest.broker import (
    SAMBrokerErrorNotImplemented,
)
from smarter.lib.manifest.loader import SAMLoader

from .base_classes.connection_base import TestSmarterConnectionBrokerBase

logger = logging.getLogger(__name__)


class TestSmarterSqlConnectionBroker(TestSmarterConnectionBrokerBase):
    """
    Test the Smarter SAMSqlConnectionBroker.

    TestSAMBrokerBaseClass provides common setup for SAM broker tests,
    including SAMLoader and HttpRequest properties.
    """

    def setUp(self):
        super().setUp()
        self._here = os.path.abspath(os.path.dirname(__file__))
        self._broker_class = SAMSqlConnectionBroker
        self._manifest_filespec = self.get_data_full_filepath("sql-connection.yaml")

    @property
    def ready(self) -> bool:
        if not super().ready:
            return False
        self.assertIsInstance(self.loader, SAMLoader)
        self.assertIsInstance(self.loader.json_data, dict)
        self.assertIsInstance(self.loader.yaml_data, str)
        self.assertIsInstance(self.request, HttpRequest)
        return True

    @property
    def SAMBrokerClass(self) -> type[SAMSqlConnectionBroker]:
        return SAMSqlConnectionBroker

    @property
    def broker(self) -> SAMSqlConnectionBroker:
        return super().broker  # type: ignore

    def test_setup(self):
        """
        Test that the test setup is correct.

        1. ready property is True.
        2. non_admin_user_profile is initialized.
        3. loader is an instance of SAMLoader with valid json_data and yaml_data.
        4. request is an instance of HttpRequest.
        5. broker is an instance of SAMSqlConnectionBroker.
        """
        self.assertTrue(self.ready)
        self.assertIsNotNone(self.non_admin_user_profile, "Non-admin user profile not initialized in base class setup.")
        self.assertIsInstance(self.loader, SAMLoader)
        self.assertIsInstance(self.loader.json_data, dict)
        self.assertIsInstance(self.loader.yaml_data, str)
        self.assertIsInstance(self.request, HttpRequest)
        self._broker = self.SAMBrokerClass(self.request, self.loader)
        self.assertIsInstance(self.broker, SAMSqlConnectionBroker)
        self._broker = self.SAMBrokerClass(self.request, self.loader)
        self.assertIsInstance(self.broker, SAMSqlConnectionBroker)
        logger.info(
            "%s.test_setup() SAMSqlConnectionBroker initialized successfully for testing.", self.formatted_class_name
        )

    def test_immutability(self):
        """Test that any property of any Pydantic broker model are immutable."""
        # each assignment below is to a read-only property or a frozen model's field, which mypy refuses.
        # The test checks that it fails at runtime too.
        with self.assertRaises(AttributeError):
            self.broker.kind = "NewKind"  # type: ignore[misc]
        manifest = self.broker.manifest
        assert manifest is not None
        with self.assertRaises(ValidationError):
            manifest.metadata.name = "NewManifestName"  # type: ignore[misc]
        with self.assertRaises(ValidationError):
            manifest.metadata.annotations = []  # type: ignore[misc,assignment]
        with self.assertRaises(ValidationError):
            manifest.metadata.tags = []  # type: ignore[misc]
        with self.assertRaises(ValidationError):
            manifest.spec.connection.database = "NewDatabaseName"  # type: ignore[misc]

    def test_ready(self):
        """Test that the test setup is correct."""
        self.assertTrue(self.ready)

    def test_sam_broker_initialization(self):
        """Test that the SAMSqlConnection model can be initialized from the manifest data."""
        manifest_metadata = self.loader.manifest_metadata
        manifest_spec = self.loader.manifest_spec
        assert manifest_metadata is not None
        assert manifest_spec is not None
        metadata = {**manifest_metadata}
        logger.info("%s.setUp() loading manifest spec: %s", self.formatted_class_name, manifest_spec)
        SAMSqlConnection(
            apiVersion=self.loader.manifest_api_version,
            kind=self.loader.manifest_kind,
            metadata=SAMConnectionCommonMetadata(**metadata),
            spec=SAMSqlConnectionSpec(**manifest_spec),
        )

    def test_broker_initialization(self):
        """
        Test that the SAMSqlConnectionBroker can be initialized from the request and loader.

        1. broker is an instance of SAMSqlConnectionBroker.
        2. broker.kind is "SqlConnection".
        3. broker.ORMModelClass is SAMSqlConnection.
        """
        broker: SAMSqlConnectionBroker = self.SAMBrokerClass(self.request, self.loader)
        self.assertIsInstance(broker, SAMSqlConnectionBroker)
        self.assertEqual(broker.kind, "SqlConnection")
        self.assertIsNotNone(broker.ORMModelClass)
        self.assertEqual(broker.ORMModelClass.__name__, "SqlConnection")

    def test_initialization_from_class(self):
        """Test that the SAMSqlConnectionBroker can be initialized from SAMBrokerClass."""
        broker: SAMSqlConnectionBroker = self.SAMBrokerClass(self.request, self.loader)
        self.assertIsInstance(broker, SAMSqlConnectionBroker)
        self.assertTrue(broker.ready)

    def test_to_json(self):
        """Test that SAMSqlConnectionBroker can serialize itself to JSON."""
        d = json.loads(json.dumps(self.broker.to_json()))
        self.assertIsInstance(d, dict)

    def test_manifest_initialization(self):
        """Test that the SAMSqlConnectionBroker can be initialized from a manifest."""
        broker = self.SAMBrokerClass(self.request, self.broker.manifest)
        self.assertIsInstance(broker, SAMSqlConnectionBroker)

    def test_manifest_model_initialization(self):
        """Test that the SAMSqlConnection can be initialized from a json dump of the manifest model."""
        manifest = self.broker.manifest
        assert manifest is not None
        static_plugin = SAMSqlConnection(**manifest.model_dump())
        self.assertIsInstance(static_plugin, SAMSqlConnection)

    def test_formatted_class_name(self):
        """Test that the formatted_class_name property returns the correct value."""
        name = self.broker.formatted_class_name
        self.assertIsInstance(name, str)
        self.assertIn("SAMSqlConnectionBroker", name)

    def test_kind_property(self):
        """Test that the kind property returns "SqlConnection"."""
        self.assertEqual(self.broker.kind, "SqlConnection")

    def test_manifest_property(self):
        """Test that the manifest property returns a SAMSqlConnection instance."""
        try:
            manifest = self.broker.manifest
        # pylint: disable=broad-except
        except Exception as e:
            self.fail(f"manifest property raised: {e}")
        self.assertIsInstance(manifest, SAMSqlConnection)

        # we should be able to round-trip the manifest model.
        assert manifest is not None
        SAMSqlConnection(**manifest.model_dump())

    def test_manifest_to_django_orm(self):
        """Test that we can convert the Django plugin spec ORM to a Pydantic manifest spec."""
        orm_dict = self.broker.manifest_to_django_orm()
        self.assertIsInstance(orm_dict, dict)

        # test serializibility
        self.assertIsInstance(json.loads(json.dumps(orm_dict)), dict)

    def test_connection(self):
        """Test that the plugin property returns a StaticPlugin instance."""

        connection = self.broker.connection
        self.assertIsInstance(connection, SqlConnection)
        assert connection is not None
        self.assertTrue(connection.ready)

    def test_is_valid(self):
        """Test that the is_valid property returns True."""
        self.assertTrue(self.broker.is_valid)

    def test_serializer(self):
        """Test that the serializer property returns a valid serializer instance."""
        self.assertEqual(self.broker.SerializerClass.__name__, "SqlConnectionSerializer")

    def test_password_secret(self):
        """Test that the password_secret property returns the correct value."""
        password_secret = self.broker.password_secret
        if password_secret is None:
            logger.info("No password secret set; skipping test_password_secret.")
            return None

        self.assertIsInstance(password_secret, Secret)
        manifest = self.broker.manifest
        assert manifest is not None
        self.assertEqual(password_secret.name, manifest.spec.connection.password)
        self.assertEqual(password_secret.name, self.test_secret_name)
        self.assertEqual(password_secret.get_secret(), self.test_secret_value)

    def test_proxy_password_secret(self):
        """Test that the proxy_password_secret property returns the correct value."""
        proxy_password_secret = self.broker.proxy_password_secret
        if proxy_password_secret is None:
            logger.info("No proxy password secret set; skipping test_proxy_password_secret.")
            return None

        self.assertIsInstance(proxy_password_secret, Secret)
        manifest = self.broker.manifest
        assert manifest is not None
        self.assertEqual(proxy_password_secret.name, manifest.spec.connection.proxyPassword)
        self.assertEqual(proxy_password_secret.name, self.test_proxy_secret_name)
        self.assertEqual(proxy_password_secret.get_secret(), self.test_proxy_secret_value)

    ###########################################################################
    # Brokered Method Tests
    ###########################################################################
    def test_example_manifest(self):
        """Test the example_manifest() generates a valid manifest response."""
        response = self.broker.example_manifest(self.request)
        is_valid_response = self.validate_smarter_journaled_json_response_ok(response)
        self.assertTrue(is_valid_response)
        is_valid_response = self.validate_example_manifest(response)
        self.assertTrue(is_valid_response)

    def test_get(self):
        """Test the get() method returns a valid manifest response."""
        response = self.broker.get(self.request, **self.kwargs)
        is_valid_response = self.validate_smarter_journaled_json_response_ok(response)
        self.assertTrue(is_valid_response)
        is_valid_response = self.validate_get(response)
        self.assertTrue(is_valid_response)

    def test_apply(self):
        """Test the apply() method returns a valid manifest response."""
        response = self.broker.apply(self.request, **self.kwargs)
        is_valid_response = self.validate_smarter_journaled_json_response_ok(response)
        self.assertTrue(is_valid_response)
        is_valid_response = self.validate_apply(response)
        self.assertTrue(is_valid_response)
        manifest = self.broker.manifest
        connection = self.broker.connection
        assert manifest is not None
        assert connection is not None

        # self.broker.manifest.metadata.tags is a list of strings.
        # verify that account.tags (TaggableManager) contains the same tags.
        manifest_tags = set(manifest.metadata.tags or [])
        django_orm_tags = None
        if isinstance(connection.tags, (TaggableManager, _TaggableManager)):
            django_orm_tags = set(connection.tags_list) if connection.tags else set()
        elif isinstance(connection.tags, set):
            django_orm_tags = connection.tags
        elif isinstance(connection.tags, list):
            django_orm_tags = set(connection.tags)
        else:
            self.fail(f"connection.tags is of unexpected type: {type(connection.tags)}. Value: {connection.tags}")
        self.assertEqual(manifest_tags, django_orm_tags)

        # self.broker.manifest.metadata.annotations is a map of keys to string values.
        # verify that plugin.annotations holds the same annotations.
        def sort_annotations(annotations):
            return dict(sorted((annotations or {}).items()))

        manifest_annotations = sort_annotations(manifest.metadata.annotations or [])
        orm_annotations = sort_annotations(connection.annotations or [])
        self.assertEqual(
            manifest_annotations,
            orm_annotations,
            f"SqlConnection annotations do not match manifest annotations. manifest: {manifest_annotations}, orm: {orm_annotations}",
        )

        self.assertEqual(
            manifest.metadata.name,
            getattr(connection, "name", None),
            f"SqlConnection name does not match manifest name. manifest: {manifest.metadata.name}, orm: {connection.name}",
        )
        self.assertEqual(
            manifest.metadata.description or "",
            getattr(connection, "description", "") or "",
            f"SqlConnection description does not match manifest description. manifest: {manifest.metadata.description}, orm: {connection.description}",
        )
        self.assertEqual(
            manifest.metadata.version or "",
            getattr(connection, "version", "") or "",
            f"SqlConnection version does not match manifest version. manifest: {manifest.metadata.version}, orm: {connection.version}",
        )

        # plugin spec fields
        self.assertEqual(manifest.spec.connection.authenticationMethod, connection.authentication_method)
        self.assertEqual(manifest.spec.connection.dbEngine, connection.db_engine)
        self.assertEqual(manifest.spec.connection.database, connection.database)
        self.assertEqual(manifest.spec.connection.hostname, connection.hostname)
        self.assertEqual(manifest.spec.connection.port, connection.port)
        self.assertEqual(manifest.spec.connection.username, connection.username)
        self.assertEqual(
            manifest.spec.connection.password,
            connection.password.name if connection.password else None,
        )
        self.assertEqual(manifest.spec.connection.timeout, connection.timeout)
        self.assertEqual(manifest.spec.connection.useSsl, connection.use_ssl)
        self.assertEqual(manifest.spec.connection.sslCert, connection.ssl_cert)
        self.assertEqual(manifest.spec.connection.sslKey, connection.ssl_key)
        self.assertEqual(manifest.spec.connection.sslCa, connection.ssl_ca)
        self.assertEqual(manifest.spec.connection.proxyHost, connection.proxy_host)
        self.assertEqual(manifest.spec.connection.proxyPort, connection.proxy_port)
        self.assertEqual(manifest.spec.connection.proxyUsername, connection.proxy_username)
        self.assertEqual(
            manifest.spec.connection.proxyPassword,
            connection.proxy_password.name if connection.proxy_password else None,
        )
        self.assertEqual(manifest.spec.connection.sshKnownHosts, connection.ssh_known_hosts)
        self.assertEqual(manifest.spec.connection.poolSize, connection.pool_size)
        self.assertEqual(manifest.spec.connection.maxOverflow, connection.max_overflow)

    def test_describe(self):
        """Test the describe() method returns a valid manifest response."""
        response = self.broker.describe(self.request, **self.kwargs)
        is_valid_response = self.validate_smarter_journaled_json_response_ok(response)
        self.assertTrue(is_valid_response)
        logger.info("Describe response: %s", response.content.decode())

    def test_delete(self):
        pass

    def test_deploy(self):
        """Test that deploy() raises NotImplementedError."""
        with self.assertRaises(SAMBrokerErrorNotImplemented):
            self.broker.deploy(self.request, **self.kwargs)

    def test_undeploy(self):
        """Test that undeploy() raises NotImplementedError."""
        with self.assertRaises(SAMBrokerErrorNotImplemented):
            self.broker.undeploy(self.request, **self.kwargs)

    def test_chat_not_implemented(self):
        """Test that prompt() raises NotImplementedError."""
        with self.assertRaises(SAMBrokerErrorNotImplemented):
            self.broker.prompt(self.request, **self.kwargs)

    def test_logs_returns_ok(self):
        """Test that logs() raises NotImplementedError."""
        with self.assertRaises(SAMBrokerErrorNotImplemented):
            self.broker.logs(self.request, **self.kwargs)
