"""Test PluginDataSqlConnection class"""

import hashlib
import os
import random
import unittest

import yaml
from django.conf import settings
from django.db.backends.base.base import BaseDatabaseWrapper

from smarter.apps.account.models import Account, UserProfile
from smarter.apps.plugin.manifest.enum import SAMPluginMetadataClassValues
from smarter.apps.plugin.manifest.models.sql_connection.const import (
    MANIFEST_KIND as SQL_CONNECTION_KIND,
)
from smarter.apps.plugin.manifest.models.sql_connection.model import (
    SAMPluginDataSqlConnection,
)
from smarter.apps.plugin.models import PluginDataSqlConnection, PluginMeta
from smarter.lib.django.user import User
from smarter.lib.manifest.enum import SAMApiVersions
from smarter.lib.manifest.loader import SAMLoader


HERE = os.path.abspath(os.path.dirname(__file__))


class TestPluginDataSqlConnection(unittest.TestCase):
    """Test PluginDataSqlConnection class"""

    def setUp(self):
        """Set up test fixtures."""

        # set user, account, user_profile
        # ---------------------------------------------------------------------
        hashed_slug = hashlib.sha256(str(random.getrandbits(256)).encode("utf-8")).hexdigest()[:16]
        username = f"test_{hashed_slug}"
        self.user = User.objects.create(username=username, password="12345")
        self.account = Account.objects.create(company_name=f"Test_{hashed_slug}", phone_number="123-456-789")
        self.user_profile = UserProfile.objects.create(user=self.user, account=self.account, is_test=True)

        self.meta_data = PluginMeta(
            account=self.account,
            name="Test Plugin",
            description="Test Plugin Description",
            plugin_class=SAMPluginMetadataClassValues.SQL.value,
            version="1.0.0",
            author=self.user_profile,
        )
        self.meta_data.save()

        # setup an instance of PluginDataSqlConnection() - a Django model
        # ---------------------------------------------------------------------
        # 1. load the yaml manifest file
        config_path = os.path.join(HERE, "mock_data/sql-connection.yaml")
        with open(config_path, encoding="utf-8") as file:
            manifest = yaml.safe_load(file)

        # 2. initialize a SAMLoader object with the manifest raw data
        self.loader = SAMLoader(api_version=SAMApiVersions.V1.value, manifest=manifest)

        # 3. create a SAMPluginDataSqlConnection pydantic model from the loader
        self.model = SAMPluginDataSqlConnection(
            apiVersion=self.loader.manifest_api_version,
            kind=self.loader.manifest_kind,
            metadata=self.loader.manifest_metadata,
            spec=self.loader.manifest_spec,
            status=self.loader.manifest_status,
        )

    def tearDown(self):
        """Tear down test fixtures."""
        try:
            self.meta_data.delete()
        except PluginMeta.DoesNotExist:
            pass
        try:
            self.user_profile.delete()
        except UserProfile.DoesNotExist:
            pass
        try:
            self.user.delete()
        except User.DoesNotExist:
            pass
        try:
            self.account.delete()
        except Account.DoesNotExist:
            pass

    def properties_factory(self) -> dict:
        return {
            "properties": {
                "location": {"type": "string", "description": "The city and state, e.g., San Francisco, CA"},
                "unit": {
                    "type": "string",
                    "enum": ["Celsius", "Fahrenheit"],
                    "description": "The temperature unit to use. Infer this from the user's location.",
                },
            },
        }

    def test_manifest(self):
        """Test that the Loader can load the manifest."""
        self.assertEqual(self.loader.manifest_api_version, SAMApiVersions.V1.value)
        self.assertEqual(self.loader.manifest_kind, SQL_CONNECTION_KIND)
        self.assertIsNotNone(self.loader.manifest_metadata)
        self.assertIsNotNone(self.loader.manifest_spec)

    def test_model(self):
        """Test that the Pydantic model populates from the manifest."""
        self.assertIsNotNone(self.model)
        self.assertEqual(self.model.apiVersion, SAMApiVersions.V1.value)
        self.assertEqual(self.model.kind, SQL_CONNECTION_KIND)
        self.assertIsNotNone(self.model.metadata)
        self.assertIsNotNone(self.model.spec)

    def test_django_model(self):
        """Test that the Django model can be initialized from the Pydantic model."""
        model_dump = self.model.spec.connection.model_dump()

        model_dump["account"] = self.account
        model_dump["name"] = self.model.metadata.name
        django_model = PluginDataSqlConnection(**model_dump)
        django_model.save()

        self.assertIsNotNone(django_model)
        self.assertEqual(django_model.account, self.account)
        self.assertEqual(django_model.name, self.model.metadata.name)
        self.assertEqual(django_model.db_engine, self.model.spec.connection.db_engine)
        self.assertEqual(django_model.database, self.model.spec.connection.database)
        self.assertEqual(django_model.hostname, self.model.spec.connection.hostname)
        self.assertEqual(django_model.port, self.model.spec.connection.port)
        self.assertEqual(django_model.username, self.model.spec.connection.username)
        self.assertEqual(django_model.password, self.model.spec.connection.password)

        django_model.delete()

    def test_plugin_datasql_connection_methods(self):
        """use the local dev db settings to Test the Django model properties and built-in functions."""

        cnx = PluginDataSqlConnection(
            account=self.account,
            name="Local Development Database",
            db_engine=settings.DATABASES["default"]["ENGINE"],
            database=settings.DATABASES["default"]["NAME"],
            hostname=settings.DATABASES["default"]["HOST"],
            port=settings.DATABASES["default"]["PORT"],
            username=settings.DATABASES["default"]["USER"],
            password=settings.DATABASES["default"]["PASSWORD"],
        )
        cnx.save()

        self.assertTrue(cnx.validate())

        connection = cnx.connect()
        self.assertIsInstance(connection, BaseDatabaseWrapper)

        result = cnx.execute_query(sql="SELECT count(*) FROM auth_user")
        self.assertIsInstance(result[0][0], int)
