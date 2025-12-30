# pylint: disable=wrong-import-position
"""Test SAMAccountBroker."""

import logging
import os

from django.http import HttpRequest

from smarter.apps.account.manifest.brokers.account import SAMAccountBroker
from smarter.apps.account.manifest.models.account.metadata import SAMAccountMetadata
from smarter.apps.account.manifest.models.account.model import SAMAccount
from smarter.apps.account.manifest.models.account.spec import (
    SAMAccountSpec,
    SAMAccountSpecConfig,
)
from smarter.lib import json
from smarter.lib.manifest.broker import (
    SAMBrokerErrorNotFound,
    SAMBrokerErrorNotImplemented,
)
from smarter.lib.manifest.loader import SAMLoader
from smarter.lib.manifest.tests.test_broker_base import TestSAMBrokerBaseClass


logger = logging.getLogger(__name__)


class TestSmarterAccountBroker(TestSAMBrokerBaseClass):
    """
    Test the Smarter SAMAccountBroker.
    TestSAMBrokerBaseClass provides common setup for SAM broker tests,
    including SAMLoader and HttpRequest properties.
    """

    def setUp(self):
        """
        test-level setup. Before we delve into the actual unit tests, we need to
        ensure that our test environment is properly configured and that we
        can initialize the precursors for testing the SAMAccountBroker.
        """
        super().setUp()
        self._broker_class = SAMAccountBroker
        self._here = os.path.abspath(os.path.dirname(__file__))
        self._manifest_filespec = self.get_data_full_filepath("account.yaml")

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
    def SAMBrokerClass(self) -> type[SAMAccountBroker]:
        """Return the SAMAccountBroker class definition for this test."""
        return SAMAccountBroker

    @property
    def broker(self) -> SAMAccountBroker:
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
        self.assertIsInstance(self.broker, SAMAccountBroker)
        self._broker = self.SAMBrokerClass(self.request, self.loader)
        self.assertIsInstance(self.broker, SAMAccountBroker)
        logger.info("%s.test_setup() SAMAccountBroker initialized successfully for testing.", self.formatted_class_name)

    def test_ready(self):
        """Test that the test setup is ready."""
        self.assertTrue(self.ready)

    def test_sam_broker_initialization(self):
        """Test that the SAMAccountBroker initializes correctly."""
        # Verify that our SAM manifest is capable of initializing the SAM Model.
        metadata = {**self.loader.manifest_metadata}
        logger.info("%s.setUp() loading manifest spec: %s", self.formatted_class_name, self.loader.manifest_spec)
        spec = {
            "config": SAMAccountSpecConfig(**self.loader.manifest_spec["config"]),
        }
        SAMAccount(
            apiVersion=self.loader.manifest_api_version,
            kind=self.loader.manifest_kind,
            metadata=SAMAccountMetadata(**metadata),
            spec=SAMAccountSpec(**spec),
        )

    def test_broker_initialization(self):
        """Test that the broker initializes with required properties."""
        broker: SAMAccountBroker = self.SAMBrokerClass(self.request, self.loader)
        self.assertIsInstance(broker, SAMAccountBroker)
        self.assertEqual(broker.kind, "Account")
        self.assertIsNotNone(broker.model_class)
        self.assertEqual(broker.model_class.__name__, "Account")

    def test_initialization_from_class(self):
        """Test initialization of SAMAccountBroker from class."""
        broker: SAMAccountBroker = self.SAMBrokerClass(self.request, self.loader)
        self.assertIsInstance(broker, SAMAccountBroker)
        self.assertTrue(broker.ready)

    def test_to_json(self):
        """Test to_json method returns JSON serializable output."""
        d = json.loads(json.dumps(self.broker.to_json()))
        self.assertIsInstance(d, dict)

    def test_manifest_initialization(self):
        """Test that the manifest property can initialize the broker and model."""
        broker = self.SAMBrokerClass(self.request, self.broker.manifest)
        self.assertIsInstance(broker, SAMAccountBroker)

    def test_manifest_model_initialization(self):
        """Test that the manifest property can initialize a SAMAccount model."""
        sam_account = SAMAccount(**self.broker.manifest.model_dump())
        self.assertIsInstance(sam_account, SAMAccount)

    def test_formatted_class_name(self):
        """Test formatted_class_name returns a string containing SAMAccountBroker."""
        name = self.broker.formatted_class_name
        self.assertIsInstance(name, str)
        self.assertIn("SAMAccountBroker", name)

    def test_kind_property(self):
        """Test kind property returns 'Account'."""
        self.assertEqual(self.broker.kind, "Account")

    def test_manifest_property(self):
        """Test manifest property returns a SAMAccount or None if not ready."""
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
            manifest_dict = self.broker.django_orm_to_manifest_dict()
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

    def test_describe(self):
        """
        Stub: test describe method. Verify that it returns a SmarterJournaledJsonResponse with expected structure
        (see user broker test for details)
        """
        response = self.broker.describe(self.request, **self.kwargs)
        is_valid_response = self.validate_smarter_journaled_json_response_ok(response)
        self.assertTrue(is_valid_response)
        logger.info("Describe response: %s", response.content.decode())

    def test_delete(self):
        """Stub: test delete method."""
        pass

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

    def test_delete_account_not_found(self):
        """
        test delete method raises not found for missing account.
        """
        self.broker.user = None

        with self.assertRaises(SAMBrokerErrorNotImplemented):
            self.broker.delete(self.request, **self.kwargs)

    def test_describe_account_not_found(self):
        """
        Test describe method raises not found for missing account.
        """
        self.broker.user = None
        with self.assertRaises(SAMBrokerErrorNotFound):
            self.broker.describe(self.request, **self.kwargs)

    def test_logs_returns_ok(self):
        """Stub: test logs method returns ok response."""
        response = self.broker.logs(self.request, **self.kwargs)
        is_valid_response = self.validate_smarter_journaled_json_response_ok(response)
        self.assertTrue(is_valid_response)
