# pylint: disable=wrong-import-position
"""Test SAMApiConnectionBroker."""

import os

from django.http import HttpRequest
from pydantic_core import ValidationError

from smarter.apps.connection.manifest.brokers.api_connection import (
    SAMApiConnectionBroker,
)
from smarter.apps.connection.manifest.models.api_connection.model import (
    SAMApiConnection,
)
from smarter.apps.connection.models import ApiConnection
from smarter.lib import json, logging
from smarter.lib.manifest.broker import (
    SAMBrokerErrorNotImplemented,
)
from smarter.lib.manifest.loader import SAMLoader

from .base_classes.connection_base import TestSmarterConnectionBrokerBase

logger = logging.getLogger(__name__)


class TestSmarterApiConnectionBroker(TestSmarterConnectionBrokerBase):
    """Test the Smarter SAMApiConnectionBroker."""

    def setUp(self):
        super().setUp()
        self._here = os.path.abspath(os.path.dirname(__file__))
        self._broker_class = SAMApiConnectionBroker
        self._manifest_filespec = self.get_data_full_filepath("api-connection-broker.yaml")

    @property
    def SAMBrokerClass(self) -> type[SAMApiConnectionBroker]:
        return SAMApiConnectionBroker

    @property
    def broker(self) -> SAMApiConnectionBroker:
        return super().broker  # type: ignore

    def apply_manifest(self):
        """Apply the test manifest and verify the response."""
        response = self.broker.apply(self.request, **self.kwargs)
        self.assertTrue(self.validate_smarter_journaled_json_response_ok(response))
        self.assertTrue(self.validate_apply(response))
        return response

    def test_setup(self):
        """Test that the test setup is correct."""
        self.assertTrue(self.ready)
        self.assertIsInstance(self.loader, SAMLoader)
        self.assertIsInstance(self.request, HttpRequest)
        self.assertIsInstance(self.broker, SAMApiConnectionBroker)

    def test_broker_properties(self):
        """Test the broker's class and descriptive properties."""
        self.assertEqual(self.broker.kind, "ApiConnection")
        self.assertIs(self.broker.ORMModelClass, ApiConnection)
        self.assertIs(self.broker.ORMMetaModelClass, ApiConnection)
        self.assertIs(self.broker.SAMModelClass, SAMApiConnection)
        self.assertEqual(self.broker.SerializerClass.__name__, "ApiConnectionSerializer")
        self.assertIn("SAMApiConnectionBroker", self.broker.formatted_class_name)

    def test_manifest(self):
        """Test that the manifest property returns an immutable SAMApiConnection."""
        manifest = self.broker.manifest
        self.assertIsInstance(manifest, SAMApiConnection)
        self.assertEqual(manifest.metadata.name, "test_api_connection")
        with self.assertRaises(ValidationError):
            self.broker.manifest.metadata.name = "NewManifestName"
        self.assertIsInstance(SAMApiConnection(**manifest.model_dump()), SAMApiConnection)

    def test_manifest_initialization(self):
        """Test that the broker can be initialized from a manifest."""
        broker = self.SAMBrokerClass(self.request, self.broker.manifest)
        self.assertIsInstance(broker, SAMApiConnectionBroker)

    def test_to_json(self):
        """Test that the broker can serialize itself to JSON."""
        self.assertIsInstance(json.loads(json.dumps(self.broker.to_json())), dict)

    def test_manifest_to_django_orm(self):
        """Test that the manifest converts to a serializable Django ORM dict."""
        orm_dict = self.broker.manifest_to_django_orm()
        self.assertIsInstance(orm_dict, dict)
        self.assertEqual(orm_dict.get("base_url"), self.broker.manifest.spec.connection.baseUrl)

    def test_secrets(self):
        """Test that the api key and proxy password secrets resolve to the class's Secrets."""
        self.assertEqual(self.broker.api_key_secret.name, self.test_secret_name)
        self.assertEqual(self.broker.proxy_password_secret.name, self.test_proxy_secret_name)

    def test_example_manifest(self):
        """Test the example_manifest() generates a valid manifest response."""
        response = self.broker.example_manifest(self.request)
        self.assertTrue(self.validate_smarter_journaled_json_response_ok(response))
        self.assertTrue(self.validate_example_manifest(response))

    def test_apply_get_describe_delete(self):
        """Test apply(), then get(), describe() and delete() of the applied connection."""
        self.apply_manifest()
        connection = self.broker.connection
        self.assertIsInstance(connection, ApiConnection)
        self.assertEqual(connection.name, self.broker.manifest.metadata.name)
        self.assertEqual(connection.base_url, self.broker.manifest.spec.connection.baseUrl)
        self.assertEqual(connection.timeout, self.broker.manifest.spec.connection.timeout)
        self.assertEqual(connection.proxy_host, self.broker.manifest.spec.connection.proxyHost)
        self.assertEqual(connection.proxy_password.name, self.test_proxy_secret_name)
        self.assertEqual(set(self.broker.manifest.metadata.tags or []), set(connection.tags_list))

        # applying a second time updates the existing connection.
        self.apply_manifest()

        response = self.broker.get(self.request, **self.kwargs)
        self.assertTrue(self.validate_smarter_journaled_json_response_ok(response))
        self.assertTrue(self.validate_get(response))

        response = self.broker.describe(self.request, **self.kwargs)
        self.assertTrue(self.validate_smarter_journaled_json_response_ok(response))
        data = json.loads(response.content.decode())
        self.assertIn("data", data)

        self.assertIsInstance(self.broker.dependencies(), list)

        response = self.broker.delete(self.request, **self.kwargs)
        self.assertTrue(self.validate_smarter_journaled_json_response_ok(response))
        self.assertFalse(
            ApiConnection.objects.filter(name="test_api_connection", user_profile=self.user_profile).exists()
        )

    def test_not_implemented(self):
        """Test that deploy(), undeploy(), prompt() and logs() are not implemented."""
        for method in (self.broker.deploy, self.broker.undeploy, self.broker.prompt, self.broker.logs):
            with self.assertRaises(SAMBrokerErrorNotImplemented):
                method(self.request, **self.kwargs)
