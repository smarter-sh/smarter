# pylint: disable=wrong-import-position
"""Test SAMApiPluginBroker."""

import os

from smarter.apps.plugin.manifest.models.api_plugin.model import SAMApiPlugin
from smarter.apps.plugin.manifest.models.sql_connection.model import SAMSqlConnection
from smarter.apps.plugin.tests.mixins import SqlConnectionTestMixin
from smarter.lib.manifest.loader import SAMLoader

from ..api_plugin import SAMApiPluginBroker
from .base_classes import TestSAMPluginBrokerBase


class TestSAMApiPluginBroker(TestSAMPluginBrokerBase, SqlConnectionTestMixin):
    """Test SAMApiPluginBroker"""

    _model: SAMApiPlugin = None
    good_manifest_path: str = None

    @property
    def connection_loader(self) -> SAMLoader:
        """Provide connection_loader from SqlConnectionTestMixin."""
        return self.__class__.connection_loader

    @property
    def connection_manifest(self) -> dict:
        """Provide connection_manifest from SqlConnectionTestMixin."""
        return self.__class__.connection_manifest

    @property
    def connection_manifest_path(self) -> str:
        """Provide connection_manifest_path from SqlConnectionTestMixin."""
        return self.__class__.connection_manifest_path

    @property
    def connection_model(self) -> SAMSqlConnection:
        """Provide connection_model from SqlConnectionTestMixin."""
        return self.__class__.connection_model

    @property
    def model(self) -> SAMApiPlugin:
        # override to create a pydantic model from the loader
        if not self._model and self.loader:
            self._model = SAMApiPlugin(**self.loader.pydantic_model_dump())
            self.assertIsNotNone(self._model)
        return self._model

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.good_manifest_path = os.path.join(self.mock_data_path, "api-plugin-good.yaml")
        self.valid_manifest_self_check()

    def test_broker_with_valid_manifest(self):
        """Test valid file path and that we can instantiate without errors"""

        broker = SAMApiPluginBroker(request=self.request, account=self.account, file_path=self.good_manifest_path)
        self.assertIsInstance(broker, SAMApiPluginBroker)
