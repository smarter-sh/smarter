"""Test the guard and failure branches of SAMApiConnectionBroker, with its connection, manifest or user replaced."""

import os
from unittest.mock import MagicMock, PropertyMock, patch

from smarter.apps.connection.manifest.brokers import SAMConnectionBrokerError
from smarter.apps.connection.manifest.brokers.api_connection import (
    SAMApiConnectionBroker,
)
from smarter.apps.connection.manifest.brokers.connection_base import (
    SAMConnectionBaseBroker,
)
from smarter.lib.manifest.broker import SAMBrokerErrorNotReady

from .base_classes.connection_base import TestSmarterConnectionBrokerBase


class TestApiConnectionBrokerBranches(TestSmarterConnectionBrokerBase):
    """Test SAMApiConnectionBroker when its connection, manifest or user is missing or fails."""

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

    def patch_property(self, name: str, value) -> PropertyMock:
        patcher = patch.object(SAMApiConnectionBroker, name, new_callable=PropertyMock, return_value=value)
        mock = patcher.start()
        self.addCleanup(patcher.stop)
        return mock

    def test_manifest_from_a_connection_needs_metadata(self):
        broker = self.broker
        broker._manifest = None
        self.patch_property("loader", None)
        self.patch_property("connection", MagicMock())
        with patch.object(SAMApiConnectionBroker, "sam_connection_metadata", return_value=None):
            with self.assertRaises(SAMBrokerErrorNotReady):
                _ = broker.manifest

    def test_manifest_to_django_orm_guards(self):
        """A connection spec that isn't a dict, or a missing user profile, raises."""
        broker = self.broker
        manifest = MagicMock()
        self.patch_property("manifest", manifest)
        with patch.object(SAMConnectionBaseBroker, "manifest_to_django_orm", return_value={}):
            manifest.spec.connection.model_dump.return_value = "not a dict"
            with self.assertRaises(SAMConnectionBrokerError):
                broker.manifest_to_django_orm()
            manifest.spec.connection.model_dump.return_value = {"baseUrl": "https://example.com"}
            with patch.object(SAMApiConnectionBroker, "user_profile", new_callable=PropertyMock, return_value=None):
                with self.assertRaises(SAMConnectionBrokerError):
                    broker.manifest_to_django_orm()

    def test_apply_guards(self):
        broker = self.broker
        with patch.object(
            SAMApiConnectionBroker, "user", new_callable=PropertyMock, return_value=MagicMock(is_staff=False)
        ):
            with self.assertRaises(SAMConnectionBrokerError):
                broker.apply(self.request)
        with (
            patch.object(
                SAMApiConnectionBroker, "user", new_callable=PropertyMock, return_value=MagicMock(is_staff=True)
            ),
            patch.object(SAMApiConnectionBroker, "connection", new_callable=PropertyMock, return_value=None),
        ):
            with self.assertRaises(SAMBrokerErrorNotReady):
                broker.apply(self.request)

    def test_describe_guards(self):
        broker = self.broker
        with patch.object(SAMApiConnectionBroker, "manifest", new_callable=PropertyMock, return_value=None):
            with self.assertRaises(SAMBrokerErrorNotReady):
                broker.describe(self.request)
        manifest = MagicMock()
        manifest.model_dump.side_effect = RuntimeError("bad manifest")
        with patch.object(SAMApiConnectionBroker, "manifest", new_callable=PropertyMock, return_value=manifest):
            with self.assertRaises(SAMConnectionBrokerError):
                broker.describe(self.request)

    def test_no_dependencies_without_a_connection(self):
        self.patch_property("connection", None)
        self.assertEqual(self.broker.dependencies(), [])

    def test_delete_guards(self):
        broker = self.broker
        with patch.object(
            SAMApiConnectionBroker, "user", new_callable=PropertyMock, return_value=MagicMock(is_staff=False)
        ):
            with self.assertRaises(SAMConnectionBrokerError):
                broker.delete(self.request)
        connection = MagicMock()
        connection.delete.side_effect = RuntimeError("database down")
        with (
            patch.object(
                SAMApiConnectionBroker, "user", new_callable=PropertyMock, return_value=MagicMock(is_staff=True)
            ),
            patch.object(SAMApiConnectionBroker, "connection", new_callable=PropertyMock, return_value=connection),
            patch.object(SAMApiConnectionBroker, "verify_no_dependencies"),
        ):
            with self.assertRaises(SAMConnectionBrokerError):
                broker.delete(self.request)
