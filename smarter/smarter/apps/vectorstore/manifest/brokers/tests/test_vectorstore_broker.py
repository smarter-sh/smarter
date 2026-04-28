# pylint: disable=wrong-import-position
"""Test SAMVectorstoreBroker."""

import logging
import os

from django.http import HttpRequest

from smarter.apps.vectorstore.manifest.brokers.vectorstore import SAMVectorstoreBroker
from smarter.apps.vectorstore.manifest.models.vectorstore.metadata import (
    SAMVectorstoreMetadata,
)
from smarter.apps.vectorstore.manifest.models.vectorstore.model import SAMVectorstore
from smarter.apps.vectorstore.manifest.models.vectorstore.spec import (
    SAMVectorstoreSpec,
)
from smarter.lib import json
from smarter.lib.manifest.broker import (
    SAMBrokerErrorNotFound,
    SAMBrokerErrorNotImplemented,
)
from smarter.lib.manifest.loader import SAMLoader
from smarter.lib.manifest.tests.test_broker_base import TestSAMBrokerBaseClass

logger = logging.getLogger(__name__)


class TestSmarterVectorstoreBroker(TestSAMBrokerBaseClass):
    """
    Test the Smarter SAMVectorstoreBroker.
    TestSAMBrokerBaseClass provides common setup for SAM broker tests,
    including SAMLoader and HttpRequest properties.
    """

    def setUp(self):
        """
        test-level setup. Before we delve into the actual unit tests, we need to
        ensure that our test environment is properly configured and that we
        can initialize the precursors for testing the SAMVectorstoreBroker.
        """
        super().setUp()
        self._broker_class = SAMVectorstoreBroker
        self._here = os.path.abspath(os.path.dirname(__file__))
        self._manifest_filespec = self.get_data_full_filepath("vectorstore.yaml")

        logger.debug(
            "%s.setUp() completed test-level setup with manifest\n%s", self.formatted_class_name, self.loader.yaml_data
        )

    @property
    def ready(self) -> bool:
        """Return True if the broker is ready."""
        if not super().ready:
            return False

        self.assertIsInstance(self.loader, SAMLoader)
        self.assertIsInstance(self.loader.json_data, dict)
        self.assertIsInstance(self.loader.yaml_data, str)
        self.assertIsInstance(self.request, HttpRequest)

        return True

    @property
    def SAMBrokerClass(self) -> type[SAMVectorstoreBroker]:
        """Return the SAMVectorstoreBroker class definition for this test."""
        return SAMVectorstoreBroker

    @property
    def broker(self) -> SAMVectorstoreBroker:
        return super().broker  # type: ignore

    def test_setup(self):
        """Verify that setup initialized the broker correctly."""
        self.assertTrue(self.ready)
        self.assertIsNotNone(self.non_admin_user_profile, "Non-admin user profile not initialized in base class setup.")
        self.assertIsInstance(self.loader, SAMLoader)
        self.assertIsInstance(self.loader.json_data, dict)
        self.assertIsInstance(self.loader.yaml_data, str)
        self.assertIsInstance(self.request, HttpRequest)
        self._broker = self.SAMBrokerClass(self.request, self.loader)
        self.assertIsInstance(self.broker, SAMVectorstoreBroker)
        self._broker = self.SAMBrokerClass(self.request, self.loader)
        self.assertIsInstance(self.broker, SAMVectorstoreBroker)
        logger.debug(
            "%s.test_setup() SAMVectorstoreBroker initialized successfully for testing.", self.formatted_class_name
        )

    def test_ready(self):
        """Test that the test setup is ready."""
        self.assertTrue(self.ready)

    def test_is_valid(self):
        """
        Test that the is_valid property returns True.
        """
        self.assertTrue(self.broker.is_valid)

    def test_sam_broker_initialization(self):
        """Test that the SAMVectorstoreBroker initializes correctly."""
        # Verify that our SAM manifest is capable of initializing the SAM Model.
        metadata = {**self.loader.manifest_metadata}
        logger.debug("%s.setUp() loading manifest spec: %s", self.formatted_class_name, self.loader.manifest_spec)
        SAMVectorstore(
            apiVersion=self.loader.manifest_api_version,
            kind=self.loader.manifest_kind,
            metadata=SAMVectorstoreMetadata(**metadata),
            spec=SAMVectorstoreSpec(**self.loader.manifest_spec),
        )

    def test_broker_initialization(self):
        """Test that the broker initializes with required properties."""
        broker: SAMVectorstoreBroker = self.SAMBrokerClass(self.request, self.loader)
        self.assertIsInstance(broker, SAMVectorstoreBroker)
        self.assertEqual(broker.kind, "Vectorstore")
        self.assertIsNotNone(broker.ORMModelClass)
        self.assertEqual(broker.ORMModelClass.__name__, "Vectorstore")

    def test_initialization_from_class(self):
        """Test initialization of SAMVectorstoreBroker from class."""
        self.assertIsInstance(self.loader, SAMLoader)
        broker: SAMVectorstoreBroker = self.SAMBrokerClass(self.request, self.loader)
        self.assertIsInstance(broker, SAMVectorstoreBroker)
        self.assertTrue(broker.ready)

    def test_to_json(self):
        """Test to_json method returns JSON serializable output."""
        d = json.loads(json.dumps(self.broker.to_json()))
        self.assertIsInstance(d, dict)

    def test_manifest_initialization(self):
        """Test that the manifest property can initialize the broker and model."""
        broker = self.SAMBrokerClass(self.request, self.broker.manifest)
        self.assertIsInstance(broker, SAMVectorstoreBroker)

    def test_manifest_model_initialization(self):
        """Test that the manifest property can initialize a SAMVectorstore model."""
        if not isinstance(self.broker.manifest, SAMVectorstore):
            self.fail(f"Broker manifest is not an instance of SAMVectorstore: {type(self.broker.manifest)}")
        sam_vectorstore = SAMVectorstore(**self.broker.manifest.model_dump())
        self.assertIsInstance(sam_vectorstore, SAMVectorstore)

    def test_formatted_class_name(self):
        """Test formatted_class_name returns a string containing SAMVectorstoreBroker."""
        name = self.broker.formatted_class_name
        self.assertIsInstance(name, str)
        self.assertIn("SAMVectorstoreBroker", name)

    def test_kind_property(self):
        """Test kind property returns 'Vectorstore'."""
        self.assertEqual(self.broker.kind, "Vectorstore")

    def test_manifest_property(self):
        """Test manifest property returns a SAMVectorstore or None if not ready."""
        try:
            _ = self.broker.manifest
        # pylint: disable=broad-except
        except Exception as e:
            self.fail(f"manifest property raised: {e}")

    def test_manifest_to_django_orm(self):
        """Test manifest_to_django_orm returns a dict."""
        if self.broker.manifest:
            orm_dict = self.broker.manifest_to_django_orm()
            self.assertIsInstance(orm_dict, dict)

    def test_django_orm_to_manifest_dict(self):
        """Test django_orm_to_manifest_dict returns a dict or raises if manifest is not set."""
        if self.broker.manifest:
            manifest = self.broker.django_orm_to_manifest()
            manifest_dict = manifest.model_dump() if manifest else None
            self.assertIsInstance(manifest_dict, dict)

    def test_example_manifest(self):
        """
        test example_manifest method.
        Verify that it returns a SmarterJournaledJsonResponse with expected structure
        (see user broker test for details)
        """
        response = self.broker.example_manifest(self.request)
        is_valid_response = self.validate_smarter_journaled_json_response_ok(response)
        self.assertTrue(is_valid_response)
        is_valid_response = self.validate_example_manifest(response)
        self.assertTrue(is_valid_response)

    def test_get(self):
        """
        test get method. Verify that it returns a SmarterJournaledJsonResponse with expected structure
        (see user broker test for details)
        """
        response = self.broker.get(self.request, **self.kwargs)
        is_valid_response = self.validate_smarter_journaled_json_response_ok(response)
        self.assertTrue(is_valid_response)
        is_valid_response = self.validate_get(response)
        self.assertTrue(is_valid_response)

    def test_apply(self):
        """
        test apply method. Verify that it returns a SmarterJournaledJsonResponse with expected structure
        (see user broker test for details)
        """
        response = self.broker.apply(self.request, **self.kwargs)
        is_valid_response = self.validate_smarter_journaled_json_response_ok(response)
        self.assertTrue(is_valid_response)
        is_valid_response = self.validate_apply(response)
        self.assertTrue(is_valid_response)

        # metadata fields
        if not isinstance(self.broker, SAMVectorstoreBroker):
            self.fail(f"Broker is not an instance of SAMVectorstoreBroker: {type(self.broker)}")
        if not isinstance(self.broker.manifest, SAMVectorstore):
            self.fail(f"Broker manifest is not an instance of SAMVectorstore: {type(self.broker.manifest)}")
        if not isinstance(self.broker.vectorstore_meta, SAMVectorstoreMetadata):
            self.fail(
                f"Broker vectorstore_meta is not an instance of SAMVectorstoreMetadata: {type(self.broker.vectorstore_meta)}"
            )
        self.assertEqual(self.broker.manifest.metadata.name, self.broker.vectorstore_meta.name)
        self.assertEqual(self.broker.manifest.metadata.version, self.broker.vectorstore_meta.version)
        self.assertEqual(self.broker.manifest.metadata.description, self.broker.vectorstore_meta.description)

        # verify that user_profile.tags (TaggableManager) contains the same tags.
        manifest_tags = set(self.broker.manifest.metadata.tags or [])
        django_orm_tags = set(self.broker.vectorstore_meta.tags_list) if self.broker.vectorstore_meta.tags else set()
        self.assertEqual(manifest_tags, django_orm_tags)

        # self.broker.manifest.metadata.annotations is a list of key-value pairs or None.
        # verify that user_profile.annotations (JSONField) contains the same annotations.
        def sort_annotations(annotations):
            return sorted(annotations, key=lambda d: sorted(d.items()))

        manifest_annotations = sort_annotations(self.broker.manifest.metadata.annotations or [])
        account_annotations = sort_annotations(self.broker.vectorstore_meta.annotations or [])
        self.assertEqual(
            manifest_annotations,
            account_annotations,
            f"Account annotations do not match manifest annotations. manifest: {manifest_annotations}, account: {account_annotations}",
        )

    def test_describe(self):
        """
        Stub: test describe method. Verify that it returns a SmarterJournaledJsonResponse with expected structure
        (see user broker test for details)
        """
        response = self.broker.apply(self.request, **self.kwargs)
        if not isinstance(self.broker.manifest, SAMVectorstore):
            self.fail(f"Broker manifest is not an instance of SAMVectorstore: {type(self.broker.manifest)}")
        kwargs = {
            "name": self.broker.manifest.metadata.name,
        }
        response = self.broker.describe(self.request, kwargs)
        is_valid_response = self.validate_smarter_journaled_json_response_ok(response)
        self.assertTrue(is_valid_response)

    def test_delete(self):
        """Stub: test delete method."""

    def test_deploy(self):
        """
        test deploy method. Verify that it returns a SmarterJournaledJsonResponse with expected structure
        (see user broker test for details)
        """
        with self.assertRaises(SAMBrokerErrorNotImplemented):
            self.broker.deploy(self.request, **self.kwargs)

    def test_undeploy(self):
        """
        test undeploy method. Verify that it returns a SmarterJournaledJsonResponse with expected structure
        (see user broker test for details)
        """
        with self.assertRaises(SAMBrokerErrorNotImplemented):
            self.broker.undeploy(self.request, **self.kwargs)

    def test_chat_not_implemented(self):
        """test chat method raises not implemented."""
        with self.assertRaises(SAMBrokerErrorNotImplemented):
            self.broker.chat(self.request, **self.kwargs)

    def test_delete_secret_not_found(self):
        """
        test delete method raises not found for missing secret.
        """

    def test_describe_secret_not_found(self):
        """
        Test describe method raises not found for missing secret.
        """
        self.broker.user = None
        with self.assertRaises(SAMBrokerErrorNotFound):
            self.broker.describe(self.request, **self.kwargs)

    def test_logs_returns_ok(self):
        """Stub: test logs method returns ok response."""

        with self.assertRaises(SAMBrokerErrorNotImplemented):
            self.broker.logs(self.request, **self.kwargs)
