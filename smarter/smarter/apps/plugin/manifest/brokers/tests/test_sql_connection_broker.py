# pylint: disable=wrong-import-position
"""Test SAMSqlConnectionBroker."""


import logging
import os

from django.http import HttpRequest
from pydantic_core import ValidationError
from taggit.managers import TaggableManager, _TaggableManager

from smarter.apps.account.models import Secret
from smarter.apps.plugin.manifest.brokers.sql_connection import SAMSqlConnectionBroker
from smarter.apps.plugin.manifest.models.common.connection.metadata import (
    SAMConnectionCommonMetadata,
)
from smarter.apps.plugin.manifest.models.sql_connection.model import SAMSqlConnection
from smarter.apps.plugin.manifest.models.sql_connection.spec import SAMSqlConnectionSpec
from smarter.apps.plugin.models import SqlConnection
from smarter.lib import json
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
        """
        Test that any property of any Pydantic broker model are immutable.
        """
        with self.assertRaises(AttributeError):
            self.broker.kind = "NewKind"
        with self.assertRaises(ValidationError):
            self.broker.manifest.metadata.name = "NewManifestName"
        with self.assertRaises(ValidationError):
            self.broker.manifest.metadata.annotations = []
        with self.assertRaises(ValidationError):
            self.broker.manifest.metadata.tags = []
        with self.assertRaises(ValidationError):
            self.broker.manifest.spec.connection.database = "NewDatabaseName"

    def test_ready(self):
        """
        Test that the test setup is correct.
        """
        self.assertTrue(self.ready)

    def test_sam_broker_initialization(self):
        """
        Test that the SAMSqlConnection model can be initialized from the manifest data.
        """
        metadata = {**self.loader.manifest_metadata}
        logger.info("%s.setUp() loading manifest spec: %s", self.formatted_class_name, self.loader.manifest_spec)
        SAMSqlConnection(
            apiVersion=self.loader.manifest_api_version,
            kind=self.loader.manifest_kind,
            metadata=SAMConnectionCommonMetadata(**metadata),
            spec=SAMSqlConnectionSpec(**self.loader.manifest_spec),
        )

    def test_broker_initialization(self):
        """
        Test that the SAMSqlConnectionBroker can be initialized from the request and loader.
        1. broker is an instance of SAMSqlConnectionBroker.
        2. broker.kind is "SqlConnection".
        3. broker.model_class is SAMSqlConnection.
        """
        broker: SAMSqlConnectionBroker = self.SAMBrokerClass(self.request, self.loader)
        self.assertIsInstance(broker, SAMSqlConnectionBroker)
        self.assertEqual(broker.kind, "SqlConnection")
        self.assertIsNotNone(broker.model_class)
        self.assertEqual(broker.model_class.__name__, "SqlConnection")

    def test_initialization_from_class(self):
        """
        Test that the SAMSqlConnectionBroker can be initialized from SAMBrokerClass.
        """
        broker: SAMSqlConnectionBroker = self.SAMBrokerClass(self.request, self.loader)
        self.assertIsInstance(broker, SAMSqlConnectionBroker)
        self.assertTrue(broker.ready)

    def test_to_json(self):
        """
        Test that SAMSqlConnectionBroker can serialize itself to JSON.
        """
        d = json.loads(json.dumps(self.broker.to_json()))
        self.assertIsInstance(d, dict)

    def test_manifest_initialization(self):
        """
        Test that the SAMSqlConnectionBroker can be initialized from a manifest.
        """
        broker = self.SAMBrokerClass(self.request, self.broker.manifest)
        self.assertIsInstance(broker, SAMSqlConnectionBroker)

    def test_manifest_model_initialization(self):
        """
        Test that the SAMSqlConnection can be initialized from
        a json dump of the manifest model.
        """
        static_plugin = SAMSqlConnection(**self.broker.manifest.model_dump())
        self.assertIsInstance(static_plugin, SAMSqlConnection)

    def test_formatted_class_name(self):
        """
        Test that the formatted_class_name property returns the correct value.
        """
        name = self.broker.formatted_class_name
        self.assertIsInstance(name, str)
        self.assertIn("SAMSqlConnectionBroker", name)

    def test_kind_property(self):
        """
        Test that the kind property returns "SqlConnection".
        """
        self.assertEqual(self.broker.kind, "SqlConnection")

    def test_manifest_property(self):
        """
        Test that the manifest property returns a SAMSqlConnection instance.
        """
        try:
            manifest = self.broker.manifest
        # pylint: disable=broad-except
        except Exception as e:
            self.fail(f"manifest property raised: {e}")
        self.assertIsInstance(manifest, SAMSqlConnection)

        # we should be able to round-trip the manifest model.
        SAMSqlConnection(**self.broker.manifest.model_dump())

    def test_manifest_to_django_orm(self):
        """
        Test that we can convert the Django plugin spec ORM
        to a Pydantic manifest spec.
        """
        orm_dict = self.broker.manifest_to_django_orm()
        self.assertIsInstance(orm_dict, dict)

        # test serializibility
        self.assertIsInstance(json.loads(json.dumps(orm_dict)), dict)

    def test_connection(self):
        """
        Test that the plugin property returns a StaticPlugin instance.
        """

        connection = self.broker.connection
        self.assertIsInstance(connection, SqlConnection)
        self.assertTrue(connection.ready)

    def test_is_valid(self):
        """
        Test that the is_valid property returns True.
        """
        self.assertTrue(self.broker.is_valid)

    def test_serializer(self):
        """
        Test that the serializer property returns a valid serializer instance.
        """
        self.assertEqual(self.broker.serializer.__name__, "SqlConnectionSerializer")

    def test_password_secret(self):
        """
        Test that the password_secret property returns the correct value.
        """
        password_secret = self.broker.password_secret
        if password_secret is None:
            logger.info("No password secret set; skipping test_password_secret.")
            return None

        self.assertIsInstance(password_secret, Secret)
        self.assertEqual(password_secret.name, self.broker.manifest.spec.connection.password)
        self.assertEqual(password_secret.name, self.test_secret_name)
        self.assertEqual(password_secret.get_secret(), self.test_secret_value)

    def test_proxy_password_secret(self):
        """
        Test that the proxy_password_secret property returns the correct value.
        """
        proxy_password_secret = self.broker.proxy_password_secret
        if proxy_password_secret is None:
            logger.info("No proxy password secret set; skipping test_proxy_password_secret.")
            return None

        self.assertIsInstance(proxy_password_secret, Secret)
        self.assertEqual(proxy_password_secret.name, self.broker.manifest.spec.connection.proxyPassword)
        self.assertEqual(proxy_password_secret.name, self.test_proxy_secret_name)
        self.assertEqual(proxy_password_secret.get_secret(), self.test_proxy_secret_value)

    ###########################################################################
    # Brokered Method Tests
    ###########################################################################
    def test_example_manifest(self):
        """
        Test the example_manifest() generates a valid manifest response.
        """
        response = self.broker.example_manifest(self.request)
        is_valid_response = self.validate_smarter_journaled_json_response_ok(response)
        self.assertTrue(is_valid_response)
        is_valid_response = self.validate_example_manifest(response)
        self.assertTrue(is_valid_response)

    def test_get(self):
        """
        Test the get() method returns a valid manifest response.
        """
        response = self.broker.get(self.request, **self.kwargs)
        is_valid_response = self.validate_smarter_journaled_json_response_ok(response)
        self.assertTrue(is_valid_response)
        is_valid_response = self.validate_get(response)
        self.assertTrue(is_valid_response)

    def test_apply(self):
        """
        Test the apply() method returns a valid manifest response.
        """
        response = self.broker.apply(self.request, **self.kwargs)
        is_valid_response = self.validate_smarter_journaled_json_response_ok(response)
        self.assertTrue(is_valid_response)
        is_valid_response = self.validate_apply(response)
        self.assertTrue(is_valid_response)

        # self.broker.manifest.metadata.tags is a list of strings.
        # verify that account.tags (TaggableManager) contains the same tags.
        manifest_tags = set(self.broker.manifest.metadata.tags or [])
        django_orm_tags = None
        if isinstance(self.broker.connection.tags, (TaggableManager, _TaggableManager)):
            django_orm_tags = set(self.broker.connection.tags.names()) if self.broker.connection.tags else set()
        elif isinstance(self.broker.connection.tags, set):
            django_orm_tags = self.broker.connection.tags
        elif isinstance(self.broker.connection.tags, list):
            django_orm_tags = set(self.broker.connection.tags)
        else:
            self.fail(
                f"connection.tags is of unexpected type: {type(self.broker.connection.tags)}. Value: {self.broker.connection.tags}"
            )
        self.assertEqual(manifest_tags, django_orm_tags)

        # self.broker.manifest.metadata.annotations is a list of key-value pairs or None.
        # verify that plugin.annotations (JSONField) contains the same annotations.
        def sort_annotations(annotations):
            return sorted(annotations, key=lambda d: sorted(d.items()))

        manifest_annotations = sort_annotations(self.broker.manifest.metadata.annotations or [])
        orm_annotations = sort_annotations(self.broker.connection.annotations or [])
        self.assertEqual(
            manifest_annotations,
            orm_annotations,
            f"SqlConnection annotations do not match manifest annotations. manifest: {manifest_annotations}, orm: {orm_annotations}",
        )

        self.assertEqual(
            self.broker.manifest.metadata.name,
            getattr(self.broker.connection, "name", None),
            f"SqlConnection name does not match manifest name. manifest: {self.broker.manifest.metadata.name}, orm: {self.broker.connection.name}",
        )
        self.assertEqual(
            self.broker.manifest.metadata.description or "",
            getattr(self.broker.connection, "description", "") or "",
            f"SqlConnection description does not match manifest description. manifest: {self.broker.manifest.metadata.description}, orm: {self.broker.connection.description}",
        )
        self.assertEqual(
            self.broker.manifest.metadata.version or "",
            getattr(self.broker.connection, "version", "") or "",
            f"SqlConnection version does not match manifest version. manifest: {self.broker.manifest.metadata.version}, orm: {self.broker.connection.version}",
        )

        # plugin spec fields
        self.assertEqual(
            self.broker.manifest.spec.connection.authenticationMethod, self.broker.connection.authentication_method
        )
        self.assertEqual(self.broker.manifest.spec.connection.dbEngine, self.broker.connection.db_engine)
        self.assertEqual(self.broker.manifest.spec.connection.database, self.broker.connection.database)
        self.assertEqual(self.broker.manifest.spec.connection.hostname, self.broker.connection.hostname)
        self.assertEqual(self.broker.manifest.spec.connection.port, self.broker.connection.port)
        self.assertEqual(self.broker.manifest.spec.connection.username, self.broker.connection.username)
        self.assertEqual(
            self.broker.manifest.spec.connection.password,
            self.broker.connection.password.name if self.broker.connection.password else None,
        )
        self.assertEqual(self.broker.manifest.spec.connection.timeout, self.broker.connection.timeout)
        self.assertEqual(self.broker.manifest.spec.connection.useSsl, self.broker.connection.use_ssl)
        self.assertEqual(self.broker.manifest.spec.connection.sslCert, self.broker.connection.ssl_cert)
        self.assertEqual(self.broker.manifest.spec.connection.sslKey, self.broker.connection.ssl_key)
        self.assertEqual(self.broker.manifest.spec.connection.sslCa, self.broker.connection.ssl_ca)
        self.assertEqual(self.broker.manifest.spec.connection.proxyHost, self.broker.connection.proxy_host)
        self.assertEqual(self.broker.manifest.spec.connection.proxyPort, self.broker.connection.proxy_port)
        self.assertEqual(self.broker.manifest.spec.connection.proxyUsername, self.broker.connection.proxy_username)
        self.assertEqual(
            self.broker.manifest.spec.connection.proxyPassword,
            self.broker.connection.proxy_password.name if self.broker.connection.proxy_password else None,
        )
        self.assertEqual(self.broker.manifest.spec.connection.sshKnownHosts, self.broker.connection.ssh_known_hosts)
        self.assertEqual(self.broker.manifest.spec.connection.poolSize, self.broker.connection.pool_size)
        self.assertEqual(self.broker.manifest.spec.connection.maxOverflow, self.broker.connection.max_overflow)

    def test_describe(self):
        """
        Test the describe() method returns a valid manifest response.
        """
        response = self.broker.describe(self.request, **self.kwargs)
        is_valid_response = self.validate_smarter_journaled_json_response_ok(response)
        self.assertTrue(is_valid_response)
        logger.info("Describe response: %s", response.content.decode())

    def test_delete(self):
        pass

    def test_deploy(self):
        """
        Test that deploy() raises NotImplementedError.
        """
        with self.assertRaises(SAMBrokerErrorNotImplemented):
            self.broker.deploy(self.request, **self.kwargs)

    def test_undeploy(self):
        """
        Test that undeploy() raises NotImplementedError.
        """
        with self.assertRaises(SAMBrokerErrorNotImplemented):
            self.broker.undeploy(self.request, **self.kwargs)

    def test_chat_not_implemented(self):
        """
        Test that chat() raises NotImplementedError.
        """
        with self.assertRaises(SAMBrokerErrorNotImplemented):
            self.broker.chat(self.request, **self.kwargs)

    def test_logs_returns_ok(self):
        """
        Test that logs() raises NotImplementedError.
        """
        with self.assertRaises(SAMBrokerErrorNotImplemented):
            self.broker.logs(self.request, **self.kwargs)
