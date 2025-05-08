"""Unit test class."""

# pylint: disable=W0104

import os
import unittest
from logging import getLogger

from smarter.apps.account.tests.factories import (
    admin_user_factory,
    admin_user_teardown,
    generate_hash_suffix,
    mortal_user_factory,
)
from smarter.apps.plugin.manifest.enum import SAMPluginMetadataClassValues
from smarter.apps.plugin.models import PluginMeta
from smarter.lib.manifest.loader import SAMLoader
from smarter.lib.manifest.models import AbstractSAMBase
from smarter.lib.unittest.utils import get_readonly_yaml_file

from .factories import plugin_meta_factory


HERE = os.path.abspath(os.path.dirname(__file__))
logger = getLogger(__name__)


class TestConnectionBase(unittest.TestCase):
    """Base class for testing connection models."""

    _manifest_path: str = None
    _manifest: str = None
    _loader: SAMLoader = None
    _model: AbstractSAMBase = None  # either SAMApiConnection or SAMSqlConnection

    @classmethod
    def setUpClass(cls):
        """
        Set up the test class with a single account, and admin and non-admin users.
        using the class setup so that we retain the same user_profile for each test,
        which is needed so that the django Secret model can be queried.
        """
        cls.hash_suffix = generate_hash_suffix()
        cls.admin_user, cls.account, cls.user_profile = admin_user_factory()
        cls.non_admin_user, _, cls.non_admin_user_profile = mortal_user_factory(account=cls.account)
        cls.meta_data = plugin_meta_factory(
            plugin_class=SAMPluginMetadataClassValues.SQL.value, account=cls.account, user_profile=cls.user_profile
        )

    @classmethod
    def tearDownClass(cls):
        admin_user_teardown(user=cls.admin_user, account=None, user_profile=cls.user_profile)
        admin_user_teardown(user=cls.non_admin_user, account=cls.account, user_profile=cls.non_admin_user_profile)
        try:
            cls.meta_data.delete()
        except PluginMeta.DoesNotExist:
            pass

    def setUp(self):
        """We use different manifest test data depending on the test case."""
        self._manifest = None
        self._manifest_path = None
        self._loader = None
        self._model = None

    @property
    def manifest_path(self) -> str:
        return self._manifest_path

    @manifest_path.setter
    def manifest_path(self, value: str):
        self._manifest_path = value
        self._manifest = None
        self._loader = None
        self._model = None

    @property
    def manifest(self) -> dict:
        if not self._manifest and self.manifest_path:
            self._manifest = get_readonly_yaml_file(self.manifest_path)
        return self._manifest

    @property
    def loader(self) -> SAMLoader:
        # initialize a SAMLoader object with the manifest raw data
        if not self._loader and self.manifest:
            self._loader = SAMLoader(manifest=self.manifest)
        return self._loader

    @property
    def model(self) -> AbstractSAMBase:
        # create a pydantic model from the loader
        raise NotImplementedError("Subclasses must implement this method")

    def load_manifest(self, filename: str) -> None:
        self.manifest_path = os.path.join(HERE, "mock_data", filename)
        self.manifest
