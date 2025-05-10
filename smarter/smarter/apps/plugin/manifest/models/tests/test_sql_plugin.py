"""
Test SAM Plugin manifest using ApiPlugin
Test cases for the PluginDataAPI Manifest.

http://localhost:8000/api/v1/tests/unauthenticated/dict/
http://localhost:8000/api/v1/tests/unauthenticated/list/
http://localhost:8000/api/v1/tests/authenticated/dict/
http://localhost:8000/api/v1/tests/authenticated/list/
"""

import os

from pydantic_core import ValidationError

from smarter.apps.plugin.manifest.enum import SAMPluginCommonMetadataClassValues

# from smarter.apps.plugin.manifest.controller import PluginController
from smarter.apps.plugin.manifest.models.sql_connection.model import SAMSqlConnection
from smarter.apps.plugin.manifest.models.sql_plugin.model import SAMSqlPlugin
from smarter.apps.plugin.models import PluginDataSql, PluginMeta, SqlConnection
from smarter.apps.plugin.tests.base_classes import ManifestTestsMixin, TestPluginBase
from smarter.apps.plugin.tests.mixins import SqlConnectionTestMixin
from smarter.common.exceptions import SmarterValueError
from smarter.common.utils import camel_to_snake_dict
from smarter.lib.journal.enum import SmarterJournalThings
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.loader import SAMLoader


HERE = os.path.abspath(os.path.dirname(__file__))


class TestSqlPlugin(TestPluginBase, ManifestTestsMixin, SqlConnectionTestMixin):
    """Test SAM manifest using ApiPlugin"""

    _model: SAMSqlPlugin = None
    plugin_meta: PluginMeta = None

    @property
    def connection_loader(self) -> SAMLoader:
        """Provide connection_loader from SqlConnectionTestMixin."""
        return self.__class__.connection_loader

    @property
    def connection_manifest(self) -> dict:
        """Provide connection_manifest from SqlConnectionTestMixin."""
        return self.__class__.connection_manifest

    @property
    def connection_manifest_path(self) -> str:
        """Provide connection_manifest_path from SqlConnectionTestMixin."""
        return self.__class__.connection_manifest_path

    @property
    def connection_model(self) -> SAMSqlConnection:
        """Provide connection_model from SqlConnectionTestMixin."""
        return self.__class__.connection_model

    @property
    def model(self) -> SAMSqlPlugin:
        # override to create a SAMSqlPlugin pydantic model from the loader
        if not self._model and self.loader:
            self._model = SAMSqlPlugin(**self.loader.pydantic_model_dump())
            self.assertIsNotNone(self._model)
        return self._model

    @classmethod
    def tearDownClass(cls):
        """Tear down test fixtures."""
        super().tearDownClass()

        try:
            cls.connection_django_model.delete()
        except (SqlConnection.DoesNotExist, ValueError):
            pass

    def tearDown(self):
        """Tear down test fixtures."""
        super().tearDown()

        try:
            self.plugin_meta.delete()
        except (SqlConnection.DoesNotExist, AttributeError, ValueError):
            pass

    def test_sql_connection(self):
        """Test the SqlConnection itself, lest we get ahead of ourselves"""
        self.assertIsInstance(self.connection_django_model, SqlConnection)
        self.assertIsInstance(self.connection_model, SAMSqlConnection)
        self.assertIsInstance(self.connection_loader, SAMLoader)
        self.assertIsInstance(self.connection_manifest, dict)
        self.assertIsInstance(self.connection_manifest_path, str)

        self.assertEqual(self.connection_model.kind, SmarterJournalThings.SQL_CONNECTION.value)

    def test_validate_api_connection_invalid_value(self):
        """Test that the timeout validator raises an error for negative values."""
        self.load_manifest(filename="sql-plugin.yaml")

        invalid_connection_string = "this $couldn't possibly be a valid connection name"
        self._manifest["spec"]["connection"] = invalid_connection_string
        self._loader = None
        self._model = None
        with self.assertRaises(SAMValidationError) as context:
            print(self.model)
        self.assertIn(
            "connection must be a valid cleanstring with no illegal characters",
            str(context.exception),
        )

    def test_validate_api_sql_query_invalid_value(self):
        """Test that the sqlQuery validator raises an error for invalid SQL syntax."""
        self.load_manifest(filename="sql-plugin.yaml")

        invalid_sql_query = None
        self._manifest["spec"]["sqlData"]["sqlQuery"] = invalid_sql_query
        self._loader = None
        self._model = None
        with self.assertRaises(ValidationError) as context:
            # spec.sqlData.sqlQuery
            print(self.model)
        self.assertIn(
            "Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]",
            str(context.exception),
        )

    def test_validate_api_sql_parameters_invalid_type(self):
        """Test that the parameters validator raises an error for invalid parameter types."""
        self.load_manifest(filename="sql-plugin.yaml")

        invalid_parameters = [
            {
                "name": "limit",
                "description": "The maximum number of results to return.",
            },
        ]

        self._manifest["spec"]["sqlData"]["parameters"] = invalid_parameters
        self._loader = None
        self._model = None
        with self.assertRaises(ValidationError) as context:
            # spec.sqlData.parameters.0.type
            #   Field required [type=missing, input_value={'name': 'limit', 'descri... of results to return.'}, input_type=dict]
            print(self.model)
        self.assertIn(
            "Field required [type=missing, input_value={'name': 'limit'",
            str(context.exception),
        )

    def test_validate_api_sql_parameters_missing_required(self):
        """Test that the parameters validator raises an error for missing required parameters."""
        self.load_manifest(filename="sql-plugin.yaml")

        self._manifest["spec"]["sqlData"] = {
            "sqlQuery": "SELECT * FROM auth_user WHERE username = '{username}';",
            "parameters": [
                {
                    "name": "bad_parameter",
                    "type": "integer",
                    "description": "The maximum number of results to return.",
                    "default": 10,
                },
            ],
        }
        self._loader = None
        self._model = None
        with self.assertRaises(ValidationError) as context:
            # spec.sqlData.parameters.0.default
            print(self.model)
        self.assertIn(
            "Input should be a valid string [type=string_type, input_value=10, input_type=int]",
            str(context.exception),
        )

    def test_django_orm(self):
        """Test that the Django model can be initialized from the Pydantic model."""
        self.load_manifest(filename="sql-plugin.yaml")

        self.plugin_meta = PluginMeta(
            account=self.account,
            name=self.model.metadata.name,
            description=self.model.metadata.description,
            plugin_class=SAMPluginCommonMetadataClassValues.SQL.value,
            author=self.user_profile,
            version="1.0.0",
        )
        self.plugin_meta.save()

        model_dump = self.model.spec.sqlData.model_dump()
        model_dump["connection"] = self.connection_django_model
        model_dump["plugin"] = self.plugin_meta
        model_dump = camel_to_snake_dict(model_dump)

        django_model = PluginDataSql(**model_dump)
        django_model.save()

        self.assertIsNotNone(django_model)
        self.assertIsInstance(django_model, PluginDataSql)

        self.assertEqual(django_model.plugin.account, self.account)
        self.assertEqual(django_model.plugin.name, self.model.metadata.name)
        self.assertEqual(django_model.plugin.description, self.model.metadata.description)
        self.assertEqual(django_model.plugin.plugin_class, SAMPluginCommonMetadataClassValues.SQL.value)

        self.assertEqual(django_model.connection, self.connection_django_model)

        pydantic_parameters = [param.model_dump() for param in self.model.spec.sqlData.parameters or []]
        django_parameters = django_model.parameters or []
        self.assertEqual(pydantic_parameters, django_parameters)

        self.assertEqual(django_model.sql_query, self.model.spec.sqlData.sqlQuery)
        self.assertEqual(django_model.limit, self.model.spec.sqlData.limit)

        pydantic_test_values = [param.model_dump() for param in self.model.spec.sqlData.testValues or []]
        django_test_values = django_model.test_values or []
        self.assertEqual(pydantic_test_values, django_test_values)

        # try some invalid values
        # ---------------------------------------------------------------------
        django_model.parameters = "this isn't even json, let alone a valid Pydantic model"
        with self.assertRaises(SmarterValueError) as context:
            django_model.save()
        self.assertIn(
            "parameters must be a list of dictionaries but got: <class 'str'>",
            str(context.exception),
        )

        # this should work
        django_model.parameters = [
            {
                "name": "username",
                "type": "string",
                "description": "The username to query.",
                "required": True,
                "default": "admin",
            }
        ]
        django_model.save()

        django_model.parameters = [
            {
                # "name": "username",
                "type": "string",
                "description": "The username to query.",
                "required": True,
                "default": "admin",
            }
        ]
        with self.assertRaises(SmarterValueError) as context:
            django_model.save()
        self.assertIn(
            "Invalid parameter structure",
            str(context.exception),
        )
        self.assertIn(
            "Field required [type=missing, input_value",
            str(context.exception),
        )

        # this works.
        # FIX NOTE: TO DISCUSS.
        django_model.parameters = [
            {
                "name": "username",
                "type": "string",
                "description": "The username to query.",
                "required": True,
                "default": "admin",
                "well": "how did i get here?",  # not part of the Pydantic model
            }
        ]
        django_model.save()

        django_model.parameters = [
            {
                "name": "username",
                "type": "string",
                "description": "The username to query.",
                "required": True,
                "default": "admin",
            }
        ]
        django_model.test_values = [
            {
                "name": "not_the_username",
                "value": "blah",
            }
        ]
        with self.assertRaises(SmarterValueError) as context:
            django_model.save()
        self.assertIn(
            "Test value for parameter 'username' is missing",
            str(context.exception),
        )

        django_model.parameters = None
        with self.assertRaises(SmarterValueError) as context:
            django_model.save()
        self.assertIn(
            "Placeholder 'username' is not defined in parameters",
            str(context.exception),
        )

        # this should work
        django_model.parameters = None
        django_model.sql_query = "SELECT * FROM auth_user;"
        django_model.save()

        try:
            django_model.delete()
        except (PluginDataSql.DoesNotExist, ValueError):
            pass
