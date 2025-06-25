# pylint: disable=wrong-import-position
"""Test SAMSqlPluginBroker."""

import os
from typing import Optional

from smarter.apps.plugin.manifest.models.sql_connection.model import SAMSqlConnection
from smarter.apps.plugin.manifest.models.sql_plugin.model import SAMSqlPlugin
from smarter.apps.plugin.tests.mixins import SqlConnectionTestMixin
from smarter.lib.manifest.loader import SAMLoader

from ..sql_plugin import SAMSqlPluginBroker
from .base_classes import TestSAMPluginBrokerBase


class TestSAMSqlPluginBroker(TestSAMPluginBrokerBase, SqlConnectionTestMixin):
    """Test SAMSqlPluginBroker"""

    _model: Optional[SAMSqlPlugin] = None
    good_manifest_path: Optional[str] = None

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
    def model(self) -> Optional[SAMSqlPlugin]:
        # override to create a pydantic model from the loader
        if not self._model and self.loader:
            self._model = SAMSqlPlugin(**self.loader.pydantic_model_dump())
            self.assertIsNotNone(self._model)
        return self._model

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.good_manifest_path = os.path.join(self.mock_data_path, "sql-plugin-good.yaml")
        self.valid_manifest_self_check()

    def test_broker_with_valid_manifest(self):
        """Test valid file path and that we can instantiate without errors"""
        if self.request is None or self.account is None:
            self.fail("Request and account must be set for the broker to work properly.")

        broker = SAMSqlPluginBroker(request=self.request, account=self.account, file_path=self.good_manifest_path)
        self.assertIsInstance(broker, SAMSqlPluginBroker)
