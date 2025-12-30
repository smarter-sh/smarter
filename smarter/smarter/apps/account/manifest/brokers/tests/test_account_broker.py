# pylint: disable=wrong-import-position
"""Test SAMAccountBroker."""

import logging
import os

from django.http import HttpRequest
from pydantic_core import ValidationError

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

    def test_immutability(self):
        """Test that the broker instance is immutable after initialization."""

        with self.assertRaises(AttributeError):
            self.broker.kind = "NewKind"

        with self.assertRaises(ValidationError):
            self.broker.manifest.metadata.name = "NewManifestName"

        with self.assertRaises(ValidationError):
            self.broker.manifest.metadata.annotations = []

        with self.assertRaises(ValidationError):
            self.broker.manifest.metadata.tags = []

        # test any field in spec.config
        with self.assertRaises(ValidationError):
            self.broker.manifest.spec.config.companyName = "New Company Name"

        # test any field in status
        with self.assertRaises(ValidationError):
            self.broker.manifest.status.adminAccount = None

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

        # self.broker.manifest.metadata.tags is a list of strings.
        # verify that account.tags (TaggableManager) contains the same tags.
        manifest_tags = set(self.broker.manifest.metadata.tags or [])
        django_orm_tags = set(self.broker.account.tags.names()) if self.broker.account.tags else set()
        self.assertEqual(manifest_tags, django_orm_tags)

        # self.broker.manifest.metadata.annotations is a list of key-value pairs or None.
        # verify that account.annotations (JSONField) contains the same annotations.
        def sort_annotations(annotations):
            return sorted(annotations, key=lambda d: sorted(d.items()))

        manifest_annotations = sort_annotations(self.broker.manifest.metadata.annotations or [])
        account_annotations = sort_annotations(self.broker.account.annotations or [])
        self.assertEqual(
            manifest_annotations,
            account_annotations,
            f"Account annotations do not match manifest annotations. manifest: {manifest_annotations}, account: {account_annotations}",
        )

        self.assertEqual(
            self.broker.manifest.metadata.name,
            self.broker.account.name,
            f"Account name does not match manifest name. manifest: {self.broker.manifest.metadata.name}, account: {self.broker.account.name}",
        )
        self.assertEqual(
            self.broker.manifest.spec.config.companyName,
            self.broker.account.company_name,
            f"Account company_name does not match manifest companyName. manifest: {self.broker.manifest.spec.config.companyName}, account: {self.broker.account.company_name}",
        )
        self.assertEqual(
            self.broker.manifest.spec.config.address1 or "",
            self.broker.account.address1 or "",
            f"Account address1 does not match manifest address1. manifest: {self.broker.manifest.spec.config.address1}, account: {self.broker.account.address1}",
        )
        self.assertEqual(
            self.broker.manifest.spec.config.address2 or "",
            self.broker.account.address2 or "",
            f"Account address2 does not match manifest address2. manifest: {self.broker.manifest.spec.config.address2}, account: {self.broker.account.address2}",
        )
        self.assertEqual(
            self.broker.manifest.spec.config.city or "",
            self.broker.account.city or "",
            f"Account city does not match manifest city. manifest: {self.broker.manifest.spec.config.city}, account: {self.broker.account.city}",
        )
        self.assertEqual(
            self.broker.manifest.spec.config.state or "",
            self.broker.account.state or "",
            f"Account state does not match manifest state. manifest: {self.broker.manifest.spec.config.state}, account: {self.broker.account.state}",
        )
        self.assertEqual(
            self.broker.manifest.spec.config.postalCode or "",
            self.broker.account.postal_code or "",
            f"Account postal_code does not match manifest postalCode. manifest: {self.broker.manifest.spec.config.postalCode}, account: {self.broker.account.postal_code}",
        )
        self.assertEqual(
            self.broker.manifest.spec.config.country or "",
            self.broker.account.country or "",
            f"Account country does not match manifest country. manifest: {self.broker.manifest.spec.config.country}, account: {self.broker.account.country}",
        )
        self.assertEqual(
            self.broker.manifest.spec.config.phoneNumber or "",
            self.broker.account.phone_number or "",
            f"Account phone_number does not match manifest phoneNumber. manifest: {self.broker.manifest.spec.config.phoneNumber}, account: {self.broker.account.phone_number}",
        )
        self.assertEqual(
            self.broker.manifest.spec.config.timezone or "",
            self.broker.account.timezone or "",
            f"Account timezone does not match manifest timezone. manifest: {self.broker.manifest.spec.config.timezone}, account: {self.broker.account.timezone}",
        )
        self.assertEqual(
            self.broker.manifest.spec.config.currency or "",
            self.broker.account.currency or "",
            f"Account currency does not match manifest currency. manifest: {self.broker.manifest.spec.config.currency}, account: {self.broker.account.currency}",
        )
        self.assertEqual(
            self.broker.manifest.spec.config.language or "",
            self.broker.account.language or "",
            f"Account language does not match manifest language. manifest: {self.broker.manifest.spec.config.language}, account: {self.broker.account.language}",
        )

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

    def test_invalid_timezone(self):
        """Test that applying a manifest with an invalid timezone raises an error."""
        # Modify the manifest to have an invalid timezone

        with self.assertRaises(ValidationError):
            self.broker.manifest.spec.config.timezone = "Invalid/Timezone"

    def test_invalid_currency(self):
        """Test that applying a manifest with an invalid currency raises an error."""
        # Modify the manifest to have an invalid currency

        with self.assertRaises(ValidationError):
            self.broker.manifest.spec.config.currency = "INVALID"

    def test_invalid_language(self):
        """Test that applying a manifest with an invalid language raises an error."""
        # Modify the manifest to have an invalid language

        with self.assertRaises(ValidationError):
            self.broker.manifest.spec.config.language = "xx-XX"

    def test_invalid_country(self):
        """Test that applying a manifest with an invalid country raises an error."""
        # Modify the manifest to have an invalid country

        with self.assertRaises(ValidationError):
            self.broker.manifest.spec.config.country = "XX"
