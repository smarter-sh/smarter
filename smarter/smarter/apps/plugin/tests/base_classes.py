"""Unit test class."""

# pylint: disable=W0104

import json
import os
from logging import getLogger
from typing import Optional

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.plugin.manifest.models.common.connection.model import (
    SAMConnectionCommon,
)
from smarter.apps.plugin.manifest.models.common.plugin.model import SAMPluginCommon
from smarter.apps.plugin.models import PluginMeta
from smarter.common.utils import get_readonly_yaml_file
from smarter.lib.manifest.loader import SAMLoader
from smarter.lib.manifest.models import AbstractSAMBase
from smarter.lib.unittest.base_classes import SmarterTestBase


HERE = os.path.abspath(os.path.dirname(__file__))
logger = getLogger(__name__)


class ManifestTestsMixin(SmarterTestBase):
    """Mixin class for high level SAM pydantic model tests."""

    @property
    def model(self) -> AbstractSAMBase:
        raise NotImplementedError("Subclasses must implement this method")


class TestPluginClassBase(TestAccountMixin):
    """Base class for testing all plugin and connection models."""

    _manifest_path: Optional[str] = None
    _manifest: Optional[dict] = None
    _loader: Optional[SAMLoader] = None
    _model: Optional[AbstractSAMBase] = (
        None  # any of SAMApiConnection, SAMSqlConnection, SAMStaticPlugin, SAMApiPlugin, SAMPluginSql
    )

    def setUp(self):
        """We use different manifest test data depending on the test case."""
        super().setUp()
        self._manifest = None
        self._manifest_path = None
        self._loader = None
        self._model = None

    @property
    def manifest_path(self) -> Optional[str]:
        return self._manifest_path

    @manifest_path.setter
    def manifest_path(self, value: str):
        self._manifest_path = value
        self._manifest = None
        self._loader = None
        self._model = None

    @property
    def manifest(self) -> Optional[dict]:
        if not self._manifest and self.manifest_path:
            self._manifest = get_readonly_yaml_file(self.manifest_path)
            self.assertIsNotNone(self._manifest)
        return self._manifest

    @property
    def loader(self) -> Optional[SAMLoader]:
        # initialize a SAMLoader object with the manifest raw data
        if not self._loader and self.manifest:
            self._loader = SAMLoader(manifest=json.dumps(self.manifest))
            self.assertIsNotNone(self._loader)
        return self._loader

    @property
    def model(self) -> AbstractSAMBase:
        raise NotImplementedError("Subclasses must implement this method")

    def load_manifest(self, filename: str) -> None:
        self.manifest_path = os.path.join(HERE, "mock_data", filename)
        self.assertIsNotNone(self.manifest)


class TestConnectionBase(TestPluginClassBase):
    """Base class for testing connection models."""

    @property
    def model(self) -> SAMConnectionCommon:
        raise NotImplementedError("Subclasses must implement this method")


class TestPluginBase(TestPluginClassBase):
    """Base class for testing connection models."""

    plugin_meta: Optional[PluginMeta] = None
    _connection_manifest_path: Optional[str] = None
    _connection_manifest: Optional[str] = None
    _connection_loader: Optional[SAMLoader] = None
    _connection_model: Optional[SAMConnectionCommon] = None  # any of SAMApiConnection, SAMSqlConnection

    @property
    def model(self) -> SAMPluginCommon:
        raise NotImplementedError("Subclasses must implement this method")

    @property
    def connection_manifest_path(self) -> str:
        raise NotImplementedError("Subclasses must implement this method")

    @property
    def connection_manifest(self) -> dict:
        raise NotImplementedError("Subclasses must implement this method")

    @property
    def connection_loader(self) -> SAMLoader:
        raise NotImplementedError("Subclasses must implement this method")

    @property
    def connection_model(self) -> SAMConnectionCommon:
        raise NotImplementedError("Subclasses must implement this method")
