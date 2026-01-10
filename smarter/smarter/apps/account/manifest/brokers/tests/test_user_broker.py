# pylint: disable=wrong-import-position
"""Test SAMUserBroker."""

import datetime
import logging
import os

from django.http import HttpRequest
from taggit.managers import TaggableManager

from smarter.apps.account.manifest.brokers.user import SAMUserBroker
from smarter.apps.account.manifest.models.user.model import SAMUser
from smarter.lib import json
from smarter.lib.manifest.broker import (
    SAMBrokerErrorNotFound,
    SAMBrokerErrorNotImplemented,
)
from smarter.lib.manifest.enum import SAMMetadataKeys
from smarter.lib.manifest.loader import SAMLoader
from smarter.lib.manifest.tests.test_broker_base import TestSAMBrokerBaseClass


logger = logging.getLogger(__name__)


class TestSmarterUserBroker(TestSAMBrokerBaseClass):
    """
    Test the Smarter SAMUserBroker.
    TestSAMBrokerBaseClass provides common setup for SAM broker tests,
    including SAMLoader and HttpRequest properties.
    """

    def setUp(self):
        """test-level setup."""
        super().setUp()
        self._broker_class = SAMUserBroker
        self._here = os.path.abspath(os.path.dirname(__file__))
        self._manifest_filespec = self.get_data_full_filepath("user.yaml")

        if not self.ready:
            raise RuntimeError(f"{self.formatted_class_name}.setUp() not in a ready state")

    @property
    def ready(self) -> bool:
        """Return True if the broker is ready."""
        if not super().ready:
            return False

        self.assertIsInstance(
            self.loader, SAMLoader
        )  # SAM manifest loader utility for loading and validating raw YAML/JSON manifest files
        self.assertIsInstance(self.loader.json_data, dict)  # YAML manifest filem, converted to json dict
        self.assertIsInstance(self.loader.yaml_data, str)  # validated YAML string
        self.assertIsInstance(
            self.request, HttpRequest
        )  # authenticated Django HttpRequest object with valid yaml manifest in the body

        return True

    @property
    def SAMBrokerClass(self) -> type[SAMUserBroker]:
        """Return the SAMUserBroker class definition for this test."""
        return SAMUserBroker

    @property
    def broker(self) -> SAMUserBroker:
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
        self.assertIsInstance(
            self.loader, SAMLoader
        )  # SAM manifest loader utility for loading and validating raw YAML/JSON manifest files
        self.assertIsInstance(self.loader.json_data, dict)  # YAML manifest filem, converted to json dict
        self.assertIsInstance(self.loader.yaml_data, str)  # validated YAML string
        self.assertIsInstance(
            self.request, HttpRequest
        )  # authenticated Django HttpRequest object with valid yaml manifest in the body

        # THIS IS WHAT WE ARE TESTING IN THIS CLASS.
        # ----------------------------------------------------------
        self._broker = self.SAMBrokerClass(self.request, self.loader)
        self.assertIsInstance(self.broker, SAMUserBroker)

        # THIS IS WHAT WE ARE TESTING IN THIS CLASS.
        # ----------------------------------------------------------
        self._broker = self.SAMBrokerClass(self.request, self.loader)
        self.assertIsInstance(self.broker, SAMUserBroker)

        logger.info("%s.test_setup() SAMUserBroker initialized successfully for testing.", self.formatted_class_name)

    def test_is_valid(self):
        """
        Test that the is_valid property returns True.
        """
        self.assertTrue(self.broker.is_valid)

    def test_broker_initialization(self):
        """Test that the broker initializes with required properties."""
        broker: SAMUserBroker = self.SAMBrokerClass(self.request, self.loader)
        self.assertIsInstance(broker, SAMUserBroker)
        self.assertEqual(broker.kind, "User")
        self.assertIsNotNone(broker.ORMModelClass)
        self.assertEqual(broker.ORMModelClass.__name__, "User")

    def test_account_contact_property(self):
        """Test account_contact property returns correct AccountContact or None."""
        broker: SAMUserBroker = self.SAMBrokerClass(self.request, self.loader)

        # Should be None if user is not authenticated or not set
        # pylint: disable=protected-access
        broker._account_contact = None
        self.broker.brokered_user = None

        self.assertIsNone(broker.account_contact)
        self.assertIsNone(broker.brokered_user_profile)

        self.broker.brokered_user = self.admin_user
        if hasattr(self.admin_user, "is_authenticated") and self.admin_user.is_authenticated:
            # If test DB is set up, this may return an AccountContact or None
            # We just check that it does not raise
            try:
                _ = broker.account_contact
            # pylint: disable=broad-except
            except Exception as e:
                self.fail(f"account_contact property raised: {e}")

    def test_initialization_from_class(self):
        """Test initialization of SAMUserBroker from class."""
        broker: SAMUserBroker = self.SAMBrokerClass(self.request, self.loader)
        self.assertIsInstance(broker, SAMUserBroker)
        self.assertTrue(broker.ready)

    def test_to_json(self):
        """Test to_json method returns JSON serializable output."""
        # ensure that the broker to_json() method returns
        # JSON serializable output.
        d = json.loads(json.dumps(self.broker.to_json()))
        self.assertIsInstance(d, dict)

    def test_manifest_initialization(self):
        """Test that the manifest property can initialize the broker and model."""
        # ensure that the broker manifest property can correctly
        # initialize the same broker class.
        broker = self.SAMBrokerClass(self.request, self.broker.manifest)
        self.assertIsInstance(broker, SAMUserBroker)

    def test_manifest_model_initialization(self):
        """Test that the manifest property can initialize a SAMUser model."""
        # verify that the manifest property
        # can correctly initialize a SAMUser Pydantic model.
        sam_user = SAMUser(**self.broker.manifest.model_dump())
        self.assertIsInstance(sam_user, SAMUser)

    def test_username_property(self):
        """Test username property returns the correct username or None."""

        self.broker.brokered_user = None
        # this will reinitialize from either the manifest or the ORM object
        self.assertIsNotNone(self.broker.username)

        self.broker.brokered_user = self.admin_user
        self.assertEqual(self.broker.username, getattr(self.admin_user, "username", None))

    def test_formatted_class_name(self):
        """Test formatted_class_name returns a string containing SAMUserBroker."""
        name = self.broker.formatted_class_name
        self.assertIsInstance(name, str)
        self.assertIn("SAMUserBroker", name)

    def test_kind_property(self):
        """Test kind property returns 'User'."""
        self.assertEqual(self.broker.kind, "User")

    def test_manifest_property(self):
        """Test manifest property returns a SAMUser or None if not ready."""
        # Should not raise, may return None if not all required fields are set
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
        {
            "data": {
                "apiVersion": "smarter.sh/v1",
                "kind": "User",
                "metadata": {
                "name": "test_admin_user_c7f0d65632f0faf2",
                "description": "no description",
                "version": "1.0.0",
                "tags": [],
                "annotations": [],
                "username": "test_admin_user_c7f0d65632f0faf2"
                },
                "spec": {
                "config": {
                    "firstName": "TestAdminFirstName_c7f0d65632f0faf2",
                    "lastName": "TestAdminLastName_c7f0d65632f0faf2",
                    "email": "test-admin-c7f0d65632f0faf2@mail.com",
                    "isStaff": true,
                    "isActive": true
                }
                }
            },
            "message": "User example manifest successfully generated",
            "api": "smarter.sh/v1",
            "thing": "User",
            "metadata": {
                "command": "example_manifest"
            }
        }
        """
        response = self.broker.example_manifest(self.request)
        is_valid_response = self.validate_smarter_journaled_json_response_ok(response)
        self.assertTrue(is_valid_response)

        is_valid_response = self.validate_example_manifest(response)
        self.assertTrue(is_valid_response)

    def test_get(self):
        """
        test get method. Verify that it returns a SmarterJournaledJsonResponse with expected structure:
            {
            "data": {
                "apiVersion": "smarter.sh/v1",
                "kind": "User",
                "metadata": {
                "count": 1
                },
                "kwargs": {},
                "data": {
                    "titles": [],
                    "items": []
                }
            },
            "message": "Users got successfully",
            "api": "smarter.sh/v1",
            "thing": "User",
            "metadata": {
                "command": "get"
            }
            }

        """
        response = self.broker.get(self.request, **self.kwargs)
        is_valid_response = self.validate_smarter_journaled_json_response_ok(response)
        self.assertTrue(is_valid_response)

        is_valid_response = self.validate_get(response)
        self.assertTrue(is_valid_response)

    def test_apply(self):
        """
        test apply method. Verify that it returns a SmarterJournaledJsonResponse with expected structure:
            {
            "data": {
                "ready": true,
                "url": "http://testserver/unknown/",
                "session_key": "74658c7e8820b4ec985c505c30ababa1b573ffe375d680f2277b369a400a38b1",
                "data": {
                    "apiVersion": "smarter.sh/v1",
                    "kind": "User",
                    "metadata": {
                        "description": "an example user manifest for the Smarter API User",
                        "name": "example_user",
                        "username": "example_user",
                        "version": "1.0.0",
                        "tags": [],
                        "annotations": []
                    },
                    "spec": {
                        "config": {
                        "email": "joe@mail.com",
                        "firstName": "John",
                        "isActive": true,
                        "isStaff": false,
                        "lastName": "Doe"
                        }
                    }
                },
                "message": "User test_admin_user_f7dc06d61589c9c7 applied successfully",
                "api": "smarter.sh/v1",
                "thing": "User",
                "metadata": {
                "command": "apply"
                }
            }
            }
        """
        kwargs = {
            "name": self.broker.manifest.metadata.name,
        }
        response = self.broker.apply(self.request, kwargs)
        is_valid_response = self.validate_smarter_journaled_json_response_ok(response)
        self.assertTrue(is_valid_response)

        is_valid_response = self.validate_apply(response)
        self.assertTrue(is_valid_response)

        # User fields
        self.assertEqual(
            self.broker.manifest.spec.config.firstName,
            self.broker.brokered_user.first_name,
            f"firstName does not match manifest: {self.broker.manifest.spec.config.firstName}, user: {self.broker.brokered_user.first_name}",
        )
        self.assertEqual(
            self.broker.manifest.spec.config.lastName,
            self.broker.brokered_user.last_name,
            f"lastName does not match manifest: {self.broker.manifest.spec.config.lastName}, user: {self.broker.brokered_user.last_name}",
        )
        self.assertEqual(
            self.broker.manifest.spec.config.email,
            self.broker.brokered_user.email,
            f"email does not match manifest: {self.broker.manifest.spec.config.email}, user: {self.broker.brokered_user.email}",
        )
        self.assertEqual(
            self.broker.manifest.spec.config.isStaff,
            self.broker.brokered_user.is_staff,
            f"isStaff does not match manifest: {self.broker.manifest.spec.config.isStaff}, user: {self.broker.brokered_user.is_staff}",
        )
        self.assertEqual(
            self.broker.manifest.spec.config.isActive,
            self.broker.brokered_user.is_active,
            f"isActive does not match manifest: {self.broker.manifest.spec.config.isActive}, user: {self.broker.brokered_user.is_active}",
        )

        # UserProfile fields
        self.assertEqual(
            self.broker.manifest.metadata.name,
            self.broker.brokered_user_profile.name,
            f"name does not match manifest: {self.broker.manifest.metadata.name}, user_profile: {self.broker.brokered_user_profile.name}",
        )
        self.assertEqual(
            self.broker.manifest.metadata.description,
            self.broker.brokered_user_profile.description,
            f"description does not match manifest: {self.broker.manifest.metadata.description}, user_profile: {self.broker.brokered_user_profile.description}",
        )
        self.assertEqual(
            self.broker.manifest.metadata.version,
            self.broker.brokered_user_profile.version,
            f"version does not match manifest: {self.broker.manifest.metadata.version}, user_profile: {self.broker.brokered_user_profile.version}",
        )

        # self.broker.manifest.metadata.tags is a list of strings.
        # verify that user_profile.tags (TaggableManager) contains the same tags.
        manifest_tags = set(self.broker.manifest.metadata.tags or [])
        django_orm_tags = None
        if isinstance(self.broker.brokered_user_profile.tags, TaggableManager):
            django_orm_tags = (
                set(self.broker.brokered_user_profile.tags.names()) if self.broker.brokered_user_profile.tags else set()
            )
        elif isinstance(self.broker.brokered_user_profile.tags, set):
            django_orm_tags = self.broker.brokered_user_profile.tags
        else:
            self.fail(f"user_profile.tags is of unexpected type: {type(self.broker.brokered_user_profile.tags)}")

        self.assertEqual(manifest_tags, django_orm_tags)

        # self.broker.manifest.metadata.annotations is a list of key-value pairs or None.
        # verify that user_profile.annotations (JSONField) contains the same annotations.
        def normalize_annotation_value(val):
            if isinstance(val, datetime.datetime):
                # Always output in UTC ISO format with 'Z' if tzinfo is set
                if val.tzinfo is not None:
                    return val.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
                return val.isoformat()
            elif isinstance(val, datetime.date):
                return val.isoformat()
            return val

        def normalize_annotations(annotations):
            normed = []
            for d in annotations or []:
                normed.append({k: normalize_annotation_value(v) for k, v in d.items()})
            return sorted(normed, key=lambda d: sorted(d.items()))

        manifest_annotations = normalize_annotations(self.broker.manifest.metadata.annotations)
        orm_annotations = normalize_annotations(self.broker.brokered_user_profile.annotations)
        self.assertEqual(
            manifest_annotations,
            orm_annotations,
            f"Account annotations do not match manifest annotations. manifest: {manifest_annotations}, account: {orm_annotations}",
        )

    def test_describe(self):
        """
        Stub: test describe method. Verify that it returns a SmarterJournaledJsonResponse with expected structure:
            {
            "data": {
                "apiVersion": "smarter.sh/v1",
                "kind": "User",
                "metadata": {
                "name": "test_admin_user_ec61fb424a68796a",
                "description": "no description",
                "version": "1.0.0",
                "tags": [],
                "annotations": [],
                "username": "test_admin_user_ec61fb424a68796a"
                },
                "spec": {
                "config": {
                    "firstName": "TestAdminFirstName_ec61fb424a68796a",
                    "lastName": "TestAdminLastName_ec61fb424a68796a",
                    "email": "test-admin-ec61fb424a68796a@mail.com",
                    "isStaff": true,
                    "isActive": true
                }
                }
            },
            "message": "User test_admin_user_ec61fb424a68796a described successfully",
            "api": "smarter.sh/v1",
            "thing": "User",
            "metadata": {
                "command": "describe"
            }
            }

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
        test deploy method. Verify that it returns a SmarterJournaledJsonResponse with expected structure:
            {
                "message": "User test_admin_user_ec61fb424a68796a deployed successfully",
                "api": "smarter.sh/v1",
                "thing": "User",
                "metadata": {
                    "command": "deploy"
                }
            }
        """
        response = self.broker.deploy(self.request, **self.kwargs)
        is_valid_response = self.validate_smarter_journaled_json_response_ok(response)
        self.assertTrue(is_valid_response)

        logger.info("Deploy response: %s", response.content.decode())

    def test_undeploy(self):
        """
        test undeploy method. Verify that it returns a SmarterJournaledJsonResponse with expected structure:
            {
                "message": "User test_admin_user_ec61fb424a68796a undeployed successfully",
                "api": "smarter.sh/v1",
                "thing": "User",
                "metadata": {
                    "command": "undeploy"
                }
            }
        """
        response = self.broker.undeploy(self.request, **self.kwargs)
        is_valid_response = self.validate_smarter_journaled_json_response_ok(response)
        self.assertTrue(is_valid_response)

        logger.info("Undeploy response: %s", response.content.decode())

    def test_chat_not_implemented(self):
        """test chat method raises not implemented."""

        with self.assertRaises(SAMBrokerErrorNotImplemented):
            self.broker.chat(self.request, **self.kwargs)

    def test_delete_user_not_found(self):
        """
        test delete method raises not found for missing user.

        """
        self.request._body = None
        self._broker = self.SAMBrokerClass(self.request)
        with self.assertRaises(SAMBrokerErrorNotFound):
            self.broker.delete(self.request, {"name": "nonexistent-user"})

    def test_describe_user_not_found(self):
        """
        Test describe method raises not found for missing user.
        """
        self.request._body = None
        self._broker = self.SAMBrokerClass(self.request)
        with self.assertRaises(SAMBrokerErrorNotFound):
            self.broker.describe(self.request, {"name": "nonexistent-user"})

    def test_logs_returns_ok(self):
        """Stub: test logs method returns ok response."""
        response = self.broker.logs(self.request, **self.kwargs)
        is_valid_response = self.validate_smarter_journaled_json_response_ok(response)
        self.assertTrue(is_valid_response)
