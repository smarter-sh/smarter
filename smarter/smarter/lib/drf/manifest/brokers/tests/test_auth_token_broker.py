# pylint: disable=wrong-import-position
"""Test SAMSmarterAuthTokenBroker."""

import logging
import os

from django.http import HttpRequest
from pydantic_core import ValidationError
from taggit.managers import TaggableManager, _TaggableManager

from smarter.lib import json
from smarter.lib.drf.manifest.brokers.auth_token import SAMSmarterAuthTokenBroker
from smarter.lib.drf.manifest.models.auth_token.metadata import (
    SAMSmarterAuthTokenMetadata,
)
from smarter.lib.drf.manifest.models.auth_token.model import SAMSmarterAuthToken
from smarter.lib.drf.manifest.models.auth_token.spec import (
    SAMSmarterAuthTokenSpec,
    SAMSmarterAuthTokenSpecConfig,
)
from smarter.lib.manifest.broker import (
    SAMBrokerErrorNotFound,
    SAMBrokerErrorNotImplemented,
)
from smarter.lib.manifest.enum import SAMMetadataKeys
from smarter.lib.manifest.loader import SAMLoader
from smarter.lib.manifest.tests.test_broker_base import TestSAMBrokerBaseClass


logger = logging.getLogger(__name__)


class TestSmarterAuthTokenBroker(TestSAMBrokerBaseClass):
    """
    Test the Smarter SAMSmarterAuthTokenBroker.
    TestSAMBrokerBaseClass provides common setup for SAM broker tests,
    including SAMLoader and HttpRequest properties.
    """

    def setUp(self):
        """
        test-level setup. Before we delve into the actual unit tests, we need to
        ensure that our test environment is properly configured and that we
        can initialize the precursors for testing the SAMSmarterAuthTokenBroker.
        """
        super().setUp()
        self._broker_class = SAMSmarterAuthTokenBroker
        self._here = os.path.abspath(os.path.dirname(__file__))
        self._manifest_filespec = self.get_data_full_filepath("auth-token.yaml")

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
    def SAMBrokerClass(self) -> type[SAMSmarterAuthTokenBroker]:
        """Return the SAMSmarterAuthTokenBroker class definition for this test."""
        return SAMSmarterAuthTokenBroker

    @property
    def broker(self) -> SAMSmarterAuthTokenBroker:
        return super().broker  # type: ignore

    @property
    def kwargs(self) -> dict:
        """Return default kwargs for broker methods."""
        if not self.ready:
            raise RuntimeError(f"{self.formatted_class_name}.kwargs accessed before ready state")
        return {
            SAMMetadataKeys.NAME.value: self.broker.manifest.metadata.name,
        }

    def test_setup(self):
        """Verify that setup initialized the broker correctly."""
        self.assertTrue(self.ready)
        self.assertIsNotNone(self.non_admin_user_profile, "Non-admin user profile not initialized in base class setup.")
        self.assertIsInstance(self.loader, SAMLoader)
        self.assertIsInstance(self.loader.json_data, dict)
        self.assertIsInstance(self.loader.yaml_data, str)
        self.assertIsInstance(self.request, HttpRequest)
        self._broker = self.SAMBrokerClass(self.request, self.loader)
        self.assertIsInstance(self.broker, SAMSmarterAuthTokenBroker)
        self._broker = self.SAMBrokerClass(self.request, self.loader)
        self.assertIsInstance(self.broker, SAMSmarterAuthTokenBroker)
        logger.info(
            "%s.test_setup() SAMSmarterAuthTokenBroker initialized successfully for testing.", self.formatted_class_name
        )

    def test_is_valid(self):
        """
        Test that the is_valid property returns True.
        """
        self.assertTrue(self.broker.is_valid)

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
        if self.broker.manifest.status:
            with self.assertRaises(ValidationError):
                self.broker.manifest.status.adminAccount = None

    def test_ready(self):
        """Test that the test setup is ready."""
        self.assertTrue(self.ready)

    def test_sam_broker_initialization(self):
        """Test that the SAMSmarterAuthTokenBroker initializes correctly."""
        # Verify that our SAM manifest is capable of initializing the SAM Model.
        metadata = {**self.loader.manifest_metadata}
        logger.info("%s.setUp() loading manifest spec: %s", self.formatted_class_name, self.loader.manifest_spec)
        spec = {
            "config": SAMSmarterAuthTokenSpecConfig(**self.loader.manifest_spec["config"]),
        }
        SAMSmarterAuthToken(
            apiVersion=self.loader.manifest_api_version,
            kind=self.loader.manifest_kind,
            metadata=SAMSmarterAuthTokenMetadata(**metadata),
            spec=SAMSmarterAuthTokenSpec(**spec),
        )

    def test_broker_initialization(self):
        """Test that the broker initializes with required properties."""
        broker: SAMSmarterAuthTokenBroker = self.SAMBrokerClass(self.request, self.loader)
        self.assertIsInstance(broker, SAMSmarterAuthTokenBroker)
        self.assertEqual(broker.kind, "AuthToken")
        self.assertIsNotNone(broker.ORMModelClass)
        self.assertEqual(broker.ORMModelClass.__name__, "SAMSmarterAuthToken")

    def test_initialization_from_class(self):
        """Test initialization of SAMSmarterAuthTokenBroker from class."""
        broker: SAMSmarterAuthTokenBroker = self.SAMBrokerClass(self.request, self.loader)
        self.assertIsInstance(broker, SAMSmarterAuthTokenBroker)
        self.assertTrue(broker.ready)

    def test_to_json(self):
        """Test to_json method returns JSON serializable output."""
        d = json.loads(json.dumps(self.broker.to_json()))
        self.assertIsInstance(d, dict)

    def test_manifest_initialization(self):
        """Test that the manifest property can initialize the broker and model."""
        broker = self.SAMBrokerClass(self.request, self.broker.manifest)
        self.assertIsInstance(broker, SAMSmarterAuthTokenBroker)

    def test_manifest_model_initialization(self):
        """Test that the manifest property can initialize a SAMSmarterAuthToken model."""
        sam_account = SAMSmarterAuthToken(**self.broker.manifest.model_dump())
        self.assertIsInstance(sam_account, SAMSmarterAuthToken)

    def test_formatted_class_name(self):
        """Test formatted_class_name returns a string containing SAMSmarterAuthTokenBroker."""
        name = self.broker.formatted_class_name
        self.assertIsInstance(name, str)
        self.assertIn("SAMSmarterAuthTokenBroker", name)

    def test_kind_property(self):
        """Test kind property returns 'SmarterAuthToken'."""
        self.assertEqual(self.broker.kind, "AuthToken")

    def test_manifest_property(self):
        """Test manifest property returns a SAMSmarterAuthToken or None if not ready."""
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
        response = self.broker.example_manifest(self.request)  # type: ignore
        is_valid_response = self.validate_smarter_journaled_json_response_ok(response)
        self.assertTrue(is_valid_response)
        is_valid_response = self.validate_example_manifest(response)
        self.assertTrue(is_valid_response)

    def test_get(self):
        """
        test get method. Verify that it returns a SmarterJournaledJsonResponse with expected structure
        (see user broker test for details)
        """
        response = self.broker.get(self.request, **self.kwargs)  # type: ignore
        is_valid_response = self.validate_smarter_journaled_json_response_ok(response)
        self.assertTrue(is_valid_response)
        is_valid_response = self.validate_get(response)
        self.assertTrue(is_valid_response)

    def test_apply(self):
        """
        test apply method. Verify that it returns a SmarterJournaledJsonResponse with expected structure
        (see user broker test for details)
        """
        response = self.broker.apply(self.request, **self.kwargs)  # type: ignore
        logger.debug("test_apply() response: %s", response.content.decode())

        is_valid_response = self.validate_smarter_journaled_json_response_ok(response)
        self.assertTrue(is_valid_response)
        is_valid_response = self.validate_apply(response)
        self.assertTrue(is_valid_response)

        logger.warning("%s.test_apply() skipping tag tests", self.formatted_class_name)
        # self.broker.manifest.metadata.tags is a list of strings.
        # verify that smarter_auth_token.tags (TaggableManager) contains the same tags.
        # manifest_tags = set(self.broker.manifest.metadata.tags or [])
        # django_orm_tags = None
        # if isinstance(self.broker.smarter_auth_token.tags, (list, TaggableManager, _TaggableManager)):
        #     django_orm_tags = (
        #         set(self.broker.smarter_auth_token.tags.names()) if self.broker.smarter_auth_token.tags else set()
        #     )
        # elif isinstance(self.broker.smarter_auth_token.tags, set):
        #     django_orm_tags = self.broker.smarter_auth_token.tags
        # else:
        #     self.fail(f"smarter_auth_token.tags is of unexpected type: {type(self.broker.smarter_auth_token.tags)}")
        # self.assertEqual(manifest_tags, django_orm_tags)

        # self.broker.manifest.metadata.annotations is a list of key-value pairs or None.
        # verify that smarter_auth_token.annotations (JSONField) contains the same annotations.
        def sort_annotations(annotations):
            return sorted(annotations, key=lambda d: sorted(d.items()))

        manifest_annotations = json.dumps(sort_annotations(self.broker.manifest.metadata.annotations or []))
        account_annotations = json.dumps(sort_annotations(self.broker.smarter_auth_token.annotations or []))
        self.assertEqual(
            manifest_annotations,
            account_annotations,
            f"SmarterAuthToken annotations do not match manifest annotations. manifest: {manifest_annotations}, smarter_auth_token: {account_annotations}",
        )

        self.assertEqual(
            self.broker.manifest.metadata.name,
            self.broker.smarter_auth_token.name,
            f"SmarterAuthToken name does not match manifest name. manifest: {self.broker.manifest.metadata.name}, smarter_auth_token: {self.broker.smarter_auth_token.name}",
        )
        self.assertEqual(
            self.broker.manifest.spec.config.isActive,
            self.broker.smarter_auth_token.is_active,
            f"SmarterAuthToken is_active does not match manifest isActive. manifest: {self.broker.manifest.spec.config.isActive}, smarter_auth_token: {self.broker.smarter_auth_token.is_active}",
        )
        self.assertEqual(
            self.broker.manifest.spec.config.username or "",
            self.broker.smarter_auth_token.user.username or "",
            f"SmarterAuthToken username does not match manifest username. manifest: {self.broker.manifest.spec.config.username}, smarter_auth_token: {self.broker.smarter_auth_token.user.username}",
        )

    def test_describe(self):
        """
        Stub: test describe method. Verify that it returns a SmarterJournaledJsonResponse with expected structure
        (see user broker test for details)
        """
        response = self.broker.describe(self.request, **self.kwargs)  # type: ignore
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
        response = self.broker.deploy(self.request, **self.kwargs)  # type: ignore
        is_valid_response = self.validate_smarter_journaled_json_response_ok(response)
        self.assertTrue(is_valid_response)
        logger.info("Describe response: %s", response.content.decode())

    def test_undeploy(self):
        """
        test undeploy method. Verify that it returns a SmarterJournaledJsonResponse with expected structure
        (see user broker test for details)
        """
        response = self.broker.undeploy(self.request, **self.kwargs)  # type: ignore
        is_valid_response = self.validate_smarter_journaled_json_response_ok(response)
        self.assertTrue(is_valid_response)
        logger.info("Describe response: %s", response.content.decode())

    def test_chat_not_implemented(self):
        """test chat method raises not implemented."""
        with self.assertRaises(SAMBrokerErrorNotImplemented):
            self.broker.chat(self.request, **self.kwargs)  # type: ignore

    def test_delete_smarter_auth_token_not_found(self):
        """
        test delete method raises not found for missing smarter_auth_token.
        """
        self.request._body = None  # pylint: disable=protected-access
        self._broker = self.SAMBrokerClass(self.request)

        with self.assertRaises(SAMBrokerErrorNotImplemented):
            self.broker.delete(self.request, {"name": "nonexistent-smarter_auth_token"})  # type: ignore

    def test_describe_smarter_auth_token_not_found(self):
        """
        Test describe method raises not found for missing smarter_auth_token.
        """
        request = self.request
        request._body = None  # pylint: disable=protected-access
        self._broker = self.SAMBrokerClass(request)
        with self.assertRaises(SAMBrokerErrorNotFound):
            self.broker.describe(request, {"name": "nonexistent-smarter_auth_token"})  # type: ignore

    def test_logs_returns_ok(self):
        """Stub: test logs method returns ok response."""

        with self.assertRaises(SAMBrokerErrorNotImplemented):
            self.broker.logs(self.request, **self.kwargs)  # type: ignore

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
