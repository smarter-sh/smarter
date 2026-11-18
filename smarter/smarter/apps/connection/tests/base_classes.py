"""Unit test class."""

# pylint: disable=W0104

import os
from typing import Optional

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.connection.manifest.models.common.connection.model import (
    SAMConnectionCommon,
)
from smarter.common.exceptions import SmarterValueError
from smarter.common.utils import get_readonly_yaml_file
from smarter.lib import json, logging
from smarter.lib.manifest.models import AbstractSAMBase
from smarter.lib.manifest.parsing import parse_manifest
from smarter.lib.typing import SmarterDictType
from smarter.lib.unittest.base_classes import SmarterTestBase

HERE = os.path.abspath(os.path.dirname(__file__))

logger = logging.getLogger(__name__)


class ManifestTestsMixin(SmarterTestBase):
    """Mixin class for high level SAM pydantic model tests."""

    @property
    def model(self) -> AbstractSAMBase:
        raise NotImplementedError("Subclasses must implement this method")


class TestConnectionBase(TestAccountMixin):
    """Base class for testing all connection models."""

    _manifest_path: Optional[str] = None
    _manifest: Optional[SmarterDictType] = None
    _manifest_data: Optional[SmarterDictType] = None
    _model: Optional[AbstractSAMBase] = None  # any of SAMApiConnection, SAMSqlConnection

    def setUp(self):
        """We use different manifest test data depending on the test case."""
        super().setUp()
        self._manifest = None
        self._manifest_path = None
        self._manifest_data = None
        self._model = None

    @property
    def manifest_path(self) -> Optional[str]:
        return self._manifest_path

    @manifest_path.setter
    def manifest_path(self, value: str):
        self._manifest_path = value
        self._manifest = None
        self._manifest_data = None
        self._model = None

    @property
    def manifest(self) -> Optional[SmarterDictType]:
        if not self._manifest and self.manifest_path:
            logger.info("%s.manifest Loading manifest from %s", self.formatted_class_name, self.manifest_path)
            self._manifest = get_readonly_yaml_file(self.manifest_path)
            self.assertIsNotNone(self._manifest)
        return self._manifest

    @property
    def manifest_data(self) -> Optional[SmarterDictType]:
        # a copy of the manifest, as a dict
        if not self._manifest_data:
            if not self.manifest:
                raise SmarterValueError(f"{self.__class__.__name__}.manifest_data() called but manifest is None")
            logger.info("%s.manifest_data copying the manifest", self.formatted_class_name)
            self._manifest_data = parse_manifest(json.dumps(self.manifest))
            self.assertIsNotNone(self._manifest_data)
        return self._manifest_data

    @property
    def model(self) -> SAMConnectionCommon:
        raise NotImplementedError("Subclasses must implement this method")

    def load_manifest(self, filename: str) -> None:
        self.manifest_path = os.path.join(HERE, "mock_data", filename)
        self.assertIsNotNone(self.manifest)
