# pylint: disable=wrong-import-position
"""Test SAMApiConnectionBroker."""

import os

from smarter.apps.plugin.manifest.brokers.api_connection import SAMApiConnectionBroker
from smarter.apps.plugin.manifest.models.api_connection.model import SAMApiConnection

from .base_classes import TestSAMConnectionBrokerBase


class TestSAMApiConnectionBroker(TestSAMConnectionBrokerBase):
    """Test SAMApiConnectionBroker"""

    _model: SAMApiConnection = None
    good_manifest_path: str = None

    @property
    def model(self) -> SAMApiConnection:
        # override to create a pydantic model from the loader
        if not self._model and self.loader:
            self._model = SAMApiConnection(**self.loader.pydantic_model_dump())
            self.assertIsNotNone(self._model)
        return self._model

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.good_manifest_path = os.path.join(self.mock_data_path, "api-connection-good.yaml")
        self.valid_manifest_self_check()

    def test_broker_with_valid_manifest(self):
        """Test valid file path and that we can instantiate without errors"""

        SAMApiConnectionBroker(request=self.request, account=self.account, file_path=self.good_manifest_path)
