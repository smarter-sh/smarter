"""Unit test class."""

# pylint: disable=W0104

import copy
import os
from typing import Any, Optional

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.connection.manifest.models.common.connection.model import (
    SAMConnectionCommon,
)
from smarter.apps.plugin.manifest.models.common.plugin.model import SAMPluginCommon
from smarter.apps.plugin.manifest.models.static_plugin.model import SAMStaticPlugin
from smarter.apps.plugin.models import PluginMeta
from smarter.apps.plugin.plugin.static import StaticPlugin
from smarter.common.exceptions import SmarterValueError
from smarter.common.utils import get_readonly_yaml_file
from smarter.lib import json, logging
from smarter.lib.manifest.loader import SAMLoader
from smarter.lib.manifest.models import AbstractSAMBase
from smarter.lib.unittest.base_classes import SmarterTestBase

HERE = os.path.abspath(os.path.dirname(__file__))
DATA_PATH = os.path.join(HERE, "data")
STATIC_PLUGIN_NAME = "test_plugin_app_static_plugin"
"""The name of the StaticPlugin in ./data/static-plugin.yaml."""

logger = logging.getLogger(__name__)


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
            logger.info("%s.manifest Loading manifest from %s", self.formatted_class_name, self.manifest_path)
            self._manifest = get_readonly_yaml_file(self.manifest_path)
            self.assertIsNotNone(self._manifest)
        return self._manifest

    @property
    def loader(self) -> Optional[SAMLoader]:
        # initialize a SAMLoader object with the manifest raw data
        if not self._loader:
            if not self.manifest:
                raise SmarterValueError(f"{self.__class__.__name__}.loader() called but manifest is None")
            logger.info("%s.loader initializing SAMLoader from manifest data", self.formatted_class_name)
            self._loader = SAMLoader(manifest=json.dumps(self.manifest))
            self.assertIsNotNone(self._loader)
        return self._loader

    @property
    def model(self) -> AbstractSAMBase:
        raise NotImplementedError("Subclasses must implement this method")

    def load_manifest(self, filename: str) -> None:
        self.manifest_path = os.path.join(HERE, "mock_data", filename)
        self.assertIsNotNone(self.manifest)


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


def get_data_path(filename: str) -> str:
    """
    Return the full path of a file in ./data.

    :param filename: The name of a file in ./data.
    :type filename: str
    :returns: The file's full path.
    :rtype: str
    """
    return os.path.join(DATA_PATH, filename)


def get_test_data(filename: str) -> Any:
    """
    Return the parsed contents of a yaml file in ./data.

    :param filename: The name of a yaml file in ./data.
    :type filename: str
    :returns: The file's parsed contents.
    :rtype: Any
    """
    return get_readonly_yaml_file(get_data_path(filename))


class PluginAppTestBase(TestAccountMixin):
    """
    Base class for the plugin app's high level tests.

    In addition to the TestAccountMixin account, admin user and non-admin
    user, it creates ``static_plugin``, a StaticPlugin owned by the admin
    user's profile, from ./data/static-plugin.yaml. Every plugin owned by
    the account is deleted in tearDownClass().

    Tests that create, modify or delete plugins use :meth:`new_static_plugin`
    to create throwaway plugins, which are deleted when the test ends.
    """

    static_plugin_yaml: dict
    static_plugin: StaticPlugin

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.static_plugin_yaml = get_test_data("static-plugin.yaml")
        cls.static_plugin = StaticPlugin(
            manifest=cls.static_manifest(STATIC_PLUGIN_NAME), user_profile=cls.user_profile
        )

    @classmethod
    def tearDownClass(cls):
        try:
            PluginMeta.objects.filter(user_profile__account=cls.account).delete()
        # pylint: disable=W0718
        except Exception as e:
            logger.warning("%s.tearDownClass() cleanup failed: %s", cls.__name__, e)
        finally:
            super().tearDownClass()

    @classmethod
    def static_manifest(cls, name: str) -> SAMStaticPlugin:
        """
        Return a StaticPlugin Pydantic manifest based on ./data/static-plugin.yaml.

        :param name: The plugin's name.
        :type name: str
        :returns: The manifest.
        :rtype: SAMStaticPlugin
        """
        data = copy.deepcopy(cls.static_plugin_yaml)
        data["metadata"]["name"] = name
        return SAMStaticPlugin(**data)

    def new_static_plugin(self, name: str, user_profile=None) -> StaticPlugin:
        """
        Create a throwaway StaticPlugin, which is deleted when the test ends.

        :param name: The plugin's name.
        :type name: str
        :param user_profile: The plugin's owner. Defaults to the admin user's profile.
        :type user_profile: Optional[UserProfile]
        :returns: The new plugin.
        :rtype: StaticPlugin
        """
        user_profile = user_profile or self.user_profile
        plugin = StaticPlugin(manifest=self.static_manifest(name), user_profile=user_profile)
        self.assertTrue(plugin.ready)
        self.addCleanup(self.delete_plugin_by_name, name, user_profile)
        return plugin

    @staticmethod
    def delete_plugin_by_name(name: str, user_profile=None) -> None:
        """
        Delete a plugin, if it exists.

        :param name: The plugin's name.
        :type name: str
        :param user_profile: The plugin's owner. Defaults to any owner.
        :type user_profile: Optional[UserProfile]
        """
        qs = PluginMeta.objects.filter(name=name)
        if user_profile is not None:
            qs = qs.filter(user_profile=user_profile)
        qs.delete()
