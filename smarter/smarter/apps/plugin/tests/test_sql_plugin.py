"""
Test SAM Plugin manifest using PluginApi
Test cases for the PluginDataAPI Manifest.

http://localhost:8000/api/v1/tests/unauthenticated/dict/
http://localhost:8000/api/v1/tests/unauthenticated/list/
http://localhost:8000/api/v1/tests/authenticated/dict/
http://localhost:8000/api/v1/tests/authenticated/list/
"""

import os

from pydantic_core import ValidationError

# from smarter.apps.plugin.manifest.controller import PluginController
from smarter.apps.plugin.manifest.models.sql_connection.model import SAMSqlConnection
from smarter.apps.plugin.manifest.models.sql_plugin.model import SAMSqlPlugin
from smarter.apps.plugin.models import SqlConnection
from smarter.lib.journal.enum import SmarterJournalThings
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.loader import SAMLoader
from smarter.lib.unittest.utils import get_readonly_yaml_file

from .base_classes import ManifestTestsMixin, TestPluginBase
from .factories import secret_factory


HERE = os.path.abspath(os.path.dirname(__file__))


# pylint: disable=too-many-instance-attributes
class TestSqlPlugin(TestPluginBase, ManifestTestsMixin):
    """Test SAM manifest using PluginApi"""

    _model: SAMSqlPlugin = None
    connection_loader: SAMLoader
    connection_manifest_path: str = None
    connection_manifest: dict = None
    connection_model: SAMSqlConnection
    connection_django_model: SqlConnection = None

    @property
    def model(self) -> SAMSqlPlugin:
        # override to create a SAMSqlPlugin pydantic model from the loader
        if not self._model and self.loader:
            self._model = SAMSqlPlugin(**self.loader.pydantic_model_dump())
        return self._model

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        super().setUpClass()

        # setup an instance of SqlConnection() - a Django model
        # ---------------------------------------------------------------------
        # 1.) create an SqlConnection manifest
        connection_manifest_filename = "sql-connection.yaml"
        connection_manifest_path = os.path.join(HERE, "mock_data", connection_manifest_filename)
        connection_manifest = get_readonly_yaml_file(connection_manifest_path)
        connection_loader = SAMLoader(manifest=connection_manifest)
        connection_model = SAMSqlConnection(**connection_loader.pydantic_model_dump())

        # 2.) transform the manifest for a django model
        # ---------------------------------------------------------------------
        connection_model_dump = connection_model.spec.connection.model_dump()
        connection_model_dump["account"] = cls.account
        connection_model_dump["name"] = connection_model.metadata.name
        connection_model_dump["description"] = connection_model.metadata.description

        if connection_model.spec.connection.password:
            clear_password = connection_model_dump.pop("password")
            secret_name = f"test_secret_{cls.hash_suffix}"
            secret = secret_factory(user_profile=cls.user_profile, name=secret_name, value=clear_password)
            connection_model_dump["password"] = secret

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
        cls.connection_django_model = SqlConnection(**connection_model_dump)
        cls.connection_django_model.save()

    @classmethod
    def tearDownClass(cls):
        """Tear down test fixtures."""
        super().tearDownClass()

        try:
            cls.connection_django_model.delete()
        except (SqlConnection.DoesNotExist, ValueError):
            pass

        cls.connection_loader = None
        cls.connection_manifest_path = None
        cls.connection_manifest = None
        cls.connection_model = None

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
