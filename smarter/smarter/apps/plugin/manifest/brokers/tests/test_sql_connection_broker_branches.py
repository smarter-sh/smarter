"""Test the guard and failure branches of SAMSqlConnectionBroker, with its connection, manifest or user replaced."""

import os
from unittest.mock import MagicMock, PropertyMock, patch

from smarter.apps.connection.manifest.brokers import SAMConnectionBrokerError
from smarter.apps.connection.manifest.brokers.sql_connection import (
    SAMSqlConnectionBroker,
)
from smarter.lib.manifest.broker import (
    SAMBrokerErrorNotImplemented,
    SAMBrokerErrorNotReady,
)

from .base_classes.connection_base import TestSmarterConnectionBrokerBase

MODULE = "smarter.apps.connection.manifest.brokers.sql_connection"


class TestSqlConnectionBrokerBranches(TestSmarterConnectionBrokerBase):
    """Test SAMSqlConnectionBroker when its connection, manifest, name or user is missing or fails."""

    def setUp(self):
        super().setUp()
        self._here = os.path.abspath(os.path.dirname(__file__))
        self._broker_class = SAMSqlConnectionBroker
        self._manifest_filespec = self.get_data_full_filepath("sql-connection.yaml")

    @property
    def SAMBrokerClass(self) -> type[SAMSqlConnectionBroker]:
        return SAMSqlConnectionBroker

    @property
    def broker(self) -> SAMSqlConnectionBroker:
        return super().broker  # type: ignore

    def patch_property(self, name: str, value) -> PropertyMock:
        patcher = patch.object(SAMSqlConnectionBroker, name, new_callable=PropertyMock, return_value=value)
        mock = patcher.start()
        self.addCleanup(patcher.stop)
        return mock

    def test_manifest_from_a_connection_needs_metadata_and_status(self):
        broker = self.broker
        self.patch_property("loader", None)
        self.patch_property("connection", MagicMock())
        for metadata, status in ((None, MagicMock()), (MagicMock(), None)):
            with self.subTest(metadata=metadata, status=status):
                broker._manifest = None
                with (
                    patch.object(SAMSqlConnectionBroker, "sam_connection_metadata", return_value=metadata),
                    patch.object(SAMSqlConnectionBroker, "sam_connection_status", return_value=status),
                ):
                    with self.assertRaises(SAMBrokerErrorNotImplemented):
                        _ = broker.manifest

    def test_proxy_password_secret_is_cached_or_found(self):
        broker = self.broker
        cached = MagicMock()
        broker._proxy_password_secret = cached
        self.assertIs(broker.proxy_password_secret, cached)
        broker._proxy_password_secret = None
        found = MagicMock()
        with patch(f"{MODULE}.Secret.objects.get", return_value=found):
            self.assertIs(broker.proxy_password_secret, found)

    def test_connection_without_a_name(self):
        broker = self.broker
        broker._connection = None
        self.patch_property("name", None)
        with patch.object(SAMSqlConnectionBroker, "to_snake_case", return_value=None):
            self.assertIsNone(broker.connection)

    def test_connection_not_found_without_a_manifest(self):
        broker = self.broker
        broker._connection = None
        broker._manifest = None
        self.patch_property("name", f"no_such_connection_{self.hash_suffix}")
        self.assertIsNone(broker.connection)

    def test_is_valid(self):
        """A missing, invalid, or manifest-less connection is not valid."""
        broker = self.broker
        with patch.object(SAMSqlConnectionBroker, "connection", new_callable=PropertyMock, return_value=None):
            self.assertFalse(broker.is_valid)
        connection = MagicMock()
        with patch.object(SAMSqlConnectionBroker, "connection", new_callable=PropertyMock, return_value=connection):
            connection.validate.side_effect = RuntimeError("cannot connect")
            self.assertFalse(broker.is_valid)
            connection.validate.side_effect = None
            connection.validate.return_value = True
            with patch.object(SAMSqlConnectionBroker, "manifest", new_callable=PropertyMock, return_value=None):
                self.assertFalse(broker.is_valid)

    def test_get_requires_a_name(self):
        broker = self.broker
        self.patch_property("name", None)
        with self.assertRaises(SAMBrokerErrorNotReady):
            broker.get(self.request)

    def test_get_serialization_failure(self):
        broker = self.broker
        connections = MagicMock()
        connections.with_read_permission_for.return_value = [MagicMock()]
        serializer_class = MagicMock(side_effect=[MagicMock(), RuntimeError("bad")])
        self.patch_property("SerializerClass", serializer_class)
        with (
            patch(f"{MODULE}.SqlConnection.objects.filter", return_value=connections),
            patch.object(SAMSqlConnectionBroker, "get_model_titles", return_value=[]),
        ):
            with self.assertRaises(SAMConnectionBrokerError):
                broker.get(self.request, name="any")

    def test_apply_without_a_connection(self):
        broker = self.broker
        self.patch_property("connection", None)
        with self.assertRaises(SAMBrokerErrorNotReady):
            broker.apply(self.request)

    def test_describe_guards(self):
        broker = self.broker
        with patch.object(SAMSqlConnectionBroker, "user", new_callable=PropertyMock, return_value=None):
            with self.assertRaises(SAMBrokerErrorNotReady):
                broker.describe(self.request, name=broker.name)
        with patch.object(SAMSqlConnectionBroker, "manifest", new_callable=PropertyMock, return_value=None):
            with self.assertRaises(SAMBrokerErrorNotReady):
                broker.describe(self.request, name=broker.name)

    def test_no_dependencies_without_a_connection(self):
        self.patch_property("connection", None)
        self.assertEqual(self.broker.dependencies(), [])

    def test_delete_failures(self):
        broker = self.broker
        with patch.object(SAMSqlConnectionBroker, "verify_no_dependencies"):
            connection = MagicMock()
            connection.delete.side_effect = RuntimeError("database down")
            with patch.object(SAMSqlConnectionBroker, "connection", new_callable=PropertyMock, return_value=connection):
                with self.assertRaises(SAMConnectionBrokerError):
                    broker.delete(self.request)
            with patch.object(SAMSqlConnectionBroker, "connection", new_callable=PropertyMock, return_value=None):
                with self.assertRaises(SAMBrokerErrorNotReady):
                    broker.delete(self.request)
