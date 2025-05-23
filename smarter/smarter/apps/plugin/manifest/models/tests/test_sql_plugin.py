"""
Test SAM Plugin manifest using ApiPlugin
Test cases for the PluginDataAPI Manifest.

http://localhost:8000/api/v1/tests/unauthenticated/dict/
http://localhost:8000/api/v1/tests/unauthenticated/list/
http://localhost:8000/api/v1/tests/authenticated/dict/
http://localhost:8000/api/v1/tests/authenticated/list/
"""

import json
from logging import getLogger

from django.core.exceptions import ValidationError as DjangoValidationError
from pydantic_core import ValidationError as PydanticValidationError

from smarter.apps.plugin.manifest.enum import SAMPluginCommonMetadataClassValues
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


logger = getLogger(__name__)


class TestSqlPlugin(TestPluginBase, ManifestTestsMixin, SqlConnectionTestMixin):
    """Test SAM manifest using ApiPlugin"""

    _model: SAMSqlPlugin = None
    plugin_meta: PluginMeta = None

    @property
    def model(self) -> SAMSqlPlugin:
        # override to create a SAMSqlPlugin pydantic model from the loader
        if not self._model and self.loader:
            self._model = SAMSqlPlugin(**self.loader.pydantic_model_dump())
            self.assertIsNotNone(self._model)
        return self._model

    def test_00_sql_connection_mixin(self):
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
            "must be a valid cleanstring with no illegal characters",
            str(context.exception),
        )

    def test_validate_api_sql_query_invalid_value(self):
        """Test that the sqlQuery validator raises an error for invalid SQL syntax."""
        self.load_manifest(filename="sql-plugin.yaml")

        invalid_sql_query = None
        self._manifest["spec"]["sqlData"]["sqlQuery"] = invalid_sql_query
        self._loader = None
        self._model = None
        with self.assertRaises(PydanticValidationError) as context:
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
        with self.assertRaises(PydanticValidationError) as context:
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
        with self.assertRaises(PydanticValidationError) as context:
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

        model_dump_orig = self.model.spec.sqlData.model_dump()
        model_dump = model_dump_orig.copy()

        self.assertIsNotNone(self.connection_django_model, "connection_django_model is None")

        model_dump["connection"] = self.connection_django_model
        model_dump["plugin"] = self.plugin_meta
        model_dump["description"] = self.model.metadata.description
        model_dump = camel_to_snake_dict(model_dump)

        django_model = PluginDataSql(**model_dump)
        try:
            django_model.save()
        except DjangoValidationError as e:
            logger.error(
                "django core ValidationError: %s\nmodel dump: %s", str(e), json.dumps(model_dump_orig, indent=4)
            )

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
