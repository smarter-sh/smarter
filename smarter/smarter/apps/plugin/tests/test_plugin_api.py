"""
Test SAM Plugin manifest using PluginApi
Test cases for the PluginDataAPI Manifest.

http://localhost:8000/api/v1/tests/unauthenticated/dict/
http://localhost:8000/api/v1/tests/unauthenticated/list/
http://localhost:8000/api/v1/tests/authenticated/dict/
http://localhost:8000/api/v1/tests/authenticated/list/
"""

import os

from smarter.apps.plugin.manifest.controller import PluginController
from smarter.apps.plugin.manifest.models.api_connection.model import SAMApiConnection
from smarter.apps.plugin.manifest.models.plugin_api.model import SAMPluginApi
from smarter.apps.plugin.models import ApiConnection
from smarter.lib.journal.enum import SmarterJournalThings
from smarter.lib.manifest.loader import SAMLoader
from smarter.lib.unittest.utils import get_readonly_yaml_file

from .base_classes import ManifestTestsMixin, TestPluginBase
from .factories import secret_factory


HERE = os.path.abspath(os.path.dirname(__file__))


# pylint: disable=too-many-instance-attributes
class TestPluginApi(TestPluginBase, ManifestTestsMixin):
    """Test SAM manifest using PluginApi"""

    _model: SAMPluginApi = None
    connection_loader: SAMLoader
    connection_manifest_path: str = None
    connection_manifest: dict = None
    connection_model: SAMApiConnection
    connection_django_model: ApiConnection = None

    @property
    def model(self) -> SAMPluginApi:
        # override to create a SAMPluginApi pydantic model from the loader
        if not self._model and self.loader:
            self._model = SAMPluginApi(**self.loader.pydantic_model_dump())
        return self._model

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        super().setUpClass()

        # setup an instance of ApiConnection() - a Django model
        # ---------------------------------------------------------------------
        # 1.) create an ApiConnection manifest
        connection_manifest_filename = "api-connection.yaml"
        connection_manifest_path = os.path.join(HERE, "mock_data", connection_manifest_filename)
        connection_manifest = get_readonly_yaml_file(connection_manifest_path)
        connection_loader = SAMLoader(manifest=connection_manifest)
        connection_model = SAMApiConnection(**connection_loader.pydantic_model_dump())

        # 2.) transform the manifest for a django model
        # ---------------------------------------------------------------------
        connection_model_dump = connection_model.spec.connection.model_dump()
        connection_model_dump["account"] = cls.account
        connection_model_dump["name"] = connection_model.metadata.name
        connection_model_dump["description"] = connection_model.metadata.description

        if connection_model.spec.connection.api_key:
            clear_api_key = connection_model_dump.pop("api_key")
            secret_name = f"test_secret_{cls.hash_suffix}"
            secret = secret_factory(user_profile=cls.user_profile, name=secret_name, value=clear_api_key)
            connection_model_dump["api_key"] = secret

        if connection_model.spec.connection.proxy_password:
            clear_proxy_password = connection_model_dump.pop("proxy_password")
            proxy_secret_name = f"test_proxy_secret_{cls.hash_suffix}"
            proxy_secret = secret_factory(
                user_profile=cls.user_profile, name=proxy_secret_name, value=clear_proxy_password
            )
            connection_model_dump["proxy_password"] = proxy_secret

        # 2.) initialize all of our class variables
        # ---------------------------------------------------------------------
        cls.connection_loader = connection_loader
        cls.connection_manifest_path = connection_manifest_path
        cls.connection_manifest = connection_manifest
        cls.connection_model = connection_model
        cls.connection_django_model = ApiConnection(**connection_model_dump)
        cls.connection_django_model.save()

    @classmethod
    def tearDownClass(cls):
        """Tear down test fixtures."""
        super().tearDownClass()

        try:
            cls.connection_django_model.delete()
        except (ApiConnection.DoesNotExist, ValueError):
            pass

        cls.connection_loader = None
        cls.connection_manifest_path = None
        cls.connection_manifest = None
        cls.connection_model = None

    def test_api_connection(self):
        """Test the ApiConnection itself, lest we get ahead of ourselves"""
        self.assertIsInstance(self.connection_django_model, ApiConnection)
        self.assertIsInstance(self.connection_model, SAMApiConnection)
        self.assertIsInstance(self.connection_loader, SAMLoader)
        self.assertIsInstance(self.connection_manifest, dict)
        self.assertIsInstance(self.connection_manifest_path, str)

        self.assertEqual(self.connection_model.kind, SmarterJournalThings.API_CONNECTION.value)
