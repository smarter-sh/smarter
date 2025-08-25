# pylint: disable=wrong-import-position
"""Test SAMStaticPluginBroker."""

import os
from typing import Optional

from smarter.apps.plugin.manifest.models.static_plugin.model import SAMStaticPlugin

from ..static_plugin import SAMStaticPluginBroker
from .base_classes import TestSAMPluginBrokerBase


# pylint: disable=W0223
class TestSAMStaticPluginBroker(TestSAMPluginBrokerBase):
    """Test SAMStaticPluginBroker"""

    _model: Optional[SAMStaticPlugin] = None
    good_manifest_path: Optional[str] = None

    @property
    def model(self) -> Optional[SAMStaticPlugin]:
        # override to create a pydantic model from the loader
        if not self._model and self.loader:
            self._model = SAMStaticPlugin(**self.loader.pydantic_model_dump())
            self.assertIsNotNone(self._model)
        return self._model

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.good_manifest_path = os.path.join(self.mock_data_path, "static-plugin-good.yaml")
        self.valid_manifest_self_check()

    def test_broker_with_valid_manifest(self):
        """Test valid file path and that we can instantiate without errors"""

        broker = SAMStaticPluginBroker(request=self.request, account=self.account, file_path=self.good_manifest_path)
        self.assertIsInstance(broker, SAMStaticPluginBroker)
