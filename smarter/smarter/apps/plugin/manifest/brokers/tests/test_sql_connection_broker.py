# pylint: disable=wrong-import-position
"""Test SAMSqlConnectionBroker."""

import os

from smarter.apps.plugin.manifest.brokers.sql_connection import SAMSqlConnectionBroker
from smarter.apps.plugin.manifest.models.sql_connection.model import SAMSqlConnection

from .base_classes import TestSAMConnectionBrokerBase


class TestSAMSqlConnectionBroker(TestSAMConnectionBrokerBase):
    """Test SAMSqlConnectionBroker"""

    _model: SAMSqlConnection = None
    good_manifest_path: str = None

    @property
    def model(self) -> SAMSqlConnection:
        # override to create a pydantic model from the loader
        if not self._model and self.loader:
            self._model = SAMSqlConnection(**self.loader.pydantic_model_dump())
            self.assertIsNotNone(self._model)
        return self._model

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.good_manifest_path = os.path.join(self.mock_data_path, "sql-connection-good.yaml")
        self.valid_manifest_self_check()

    def test_broker_with_valid_manifest(self):
        """Test valid file path and that we can instantiate without errors"""

        SAMSqlConnectionBroker(request=self.request, account=self.account, file_path=self.good_manifest_path)
