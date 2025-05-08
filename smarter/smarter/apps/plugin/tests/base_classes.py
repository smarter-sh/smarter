"""Unit test class."""

# pylint: disable=W0104

import os
import unittest
from logging import getLogger

from pydantic import ValidationError

from smarter.apps.account.tests.factories import (
    admin_user_factory,
    factory_account_teardown,
    generate_hash_suffix,
    mortal_user_factory,
)
from smarter.apps.plugin.manifest.enum import SAMPluginCommonMetadataClassValues
from smarter.apps.plugin.models import PluginMeta
from smarter.common.api import SmarterApiVersions
from smarter.lib.manifest.loader import SAMLoader
from smarter.lib.manifest.models import AbstractSAMBase
from smarter.lib.unittest.utils import get_readonly_yaml_file

from .factories import plugin_meta_factory


HERE = os.path.abspath(os.path.dirname(__file__))
logger = getLogger(__name__)


class ManifestTestsMixin(unittest.TestCase):
    """Mixin class for high level SAM pydantic model tests."""

    def setUp(self):
        try:
            self.model
        except NotImplementedError:
            self.skipTest("Skipping test because the child class is not fully initialized")
        super().setUp()

    @property
    def model(self) -> AbstractSAMBase:
        raise NotImplementedError("Subclasses must implement this method")

    def test_model_api_version(self):
        """
        Test that the model has the correct API version.
        """
        if not self.model:
            self.skipTest("Skipping test because the model is not initialized")

        self.assertEqual(self.model.apiVersion, SmarterApiVersions.V1)

    def test_model_validation(self):
        """
        Test that the model is valid.
        """
        if not self.model:
            self.skipTest("Skipping test because the model is not initialized")

        try:
            self.model.model_validate()
        except ValidationError as e:
            self.fail(f"Model validation failed: {e}")


class TestBase(unittest.TestCase):
    """Base class for testing all plugin and connection models."""

    _manifest_path: str = None
    _manifest: dict = None
    _loader: SAMLoader = None
    _model: AbstractSAMBase = (
        None  # any of SAMApiConnection, SAMSqlConnection, SAMPluginStatic, SAMPluginApi, SAMPluginSql
    )

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

    @classmethod
    def tearDownClass(cls):
        factory_account_teardown(user=cls.admin_user, account=None, user_profile=cls.user_profile)
        factory_account_teardown(user=cls.non_admin_user, account=cls.account, user_profile=cls.non_admin_user_profile)

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
        raise NotImplementedError("Subclasses must implement this method")

    def load_manifest(self, filename: str) -> None:
        self.manifest_path = os.path.join(HERE, "mock_data", filename)
        self.manifest


class TestConnectionBase(TestBase):
    """Base class for testing connection models."""

    @classmethod
    def setUpClass(cls):
        """
        setup a generic plugin meta data object for the test class.
        This is used to test the connection models.
        """
        super().setUpClass()
        cls.meta_data = plugin_meta_factory(
            plugin_class=SAMPluginCommonMetadataClassValues.SQL.value,
            account=cls.account,
            user_profile=cls.user_profile,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        try:
            cls.meta_data.delete()
        except PluginMeta.DoesNotExist:
            pass

    @property
    def model(self) -> AbstractSAMBase:
        raise NotImplementedError("Subclasses must implement this method")


class TestPluginBase(TestBase):
    """Base class for testing connection models."""

    _connection_manifest_path: str = None
    _connection_manifest: str = None
    _connection_loader: SAMLoader = None
    _connection_model: AbstractSAMBase = None  # any of SAMApiConnection, SAMSqlConnection

    @property
    def model(self) -> AbstractSAMBase:
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
    def connection_model(self) -> AbstractSAMBase:
        raise NotImplementedError("Subclasses must implement this method")
