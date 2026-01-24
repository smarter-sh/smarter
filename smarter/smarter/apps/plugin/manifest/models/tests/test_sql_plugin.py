"""
Unit tests for SAMSqlPlugin

mcdaniel jan-2026: TestSqlPluginLegacy should be refactored. it contains a mix
of Pydantic model tests combined with Django ORM model tests,
which really should be (or might already be) in the broker test bank.
"""

import logging
import os
from typing import Optional

from pydantic_core import ValidationError as PydanticValidationError

from smarter.apps.account.manifest.brokers.secret import SAMSecretBroker
from smarter.apps.account.manifest.models.secret.model import SAMSecret
from smarter.apps.account.models import Secret
from smarter.apps.plugin.const import DATA_PATH as PLUGIN_DATA_PATH
from smarter.apps.plugin.manifest.brokers.sql_connection import SAMSqlConnectionBroker
from smarter.apps.plugin.manifest.brokers.sql_plugin import SAMSqlPluginBroker
from smarter.apps.plugin.manifest.models.common.plugin.metadata import (
    SAMPluginCommonMetadata,
)
from smarter.apps.plugin.manifest.models.common.plugin.status import (
    SAMPluginCommonStatus,
)
from smarter.apps.plugin.manifest.models.sql_connection.model import SAMSqlConnection
from smarter.apps.plugin.manifest.models.sql_plugin.model import SAMSqlPlugin
from smarter.apps.plugin.manifest.models.sql_plugin.spec import SAMSqlPluginSpec
from smarter.apps.plugin.models import PluginDataSql, PluginMeta, SqlConnection
from smarter.apps.plugin.plugin.sql import SqlPlugin
from smarter.apps.plugin.tests.base_classes import ManifestTestsMixin, TestPluginBase
from smarter.apps.plugin.tests.mixins import (
    AuthenticatedRequestMixin,
    SqlConnectionTestMixin,
)
from smarter.common.exceptions import SmarterValueError
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.journal.http import SmarterJournaledJsonResponse
from smarter.lib.manifest.broker import SAMBrokerError
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.loader import SAMLoader
from smarter.lib.manifest.tests.test_broker_base import TestSAMBrokerBaseClass

logger = logging.getLogger(__name__)
MANIFEST_PATH_SQL_PLUGIN = os.path.abspath(
    os.path.join(PLUGIN_DATA_PATH, "manifest", "brokers", "tests", "data", "sql-plugin.yaml")
)
"""
Path to the Sql plugin manifest file 'sql-plugin.yaml' which
contains the actual connection parameters for the remote test database.

Note that we're borrowing the sql-connection.yaml file from the
broker tests.
"""
HERE = __name__


class TestSAMSqlPlugin(TestSAMBrokerBaseClass):
    """
    Test SAMSqlPlugin Pydantic model.

    .. note::

        TestSAMBrokerBaseClass is generically useful for testing SAM-based
        Pydantic models.
    """

    test_sam_sql_plugin_logger_prefix = formatted_text(f"{HERE}.TestSAMSqlPlugin()")

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        logger.debug("%s.setUpClass()", cls.test_sam_sql_plugin_logger_prefix)
        cls.loader = SAMLoader(file_path=MANIFEST_PATH_SQL_PLUGIN)

    @classmethod
    def tearDownClass(cls):
        logger.debug("%s.tearDownClass()", cls.test_sam_sql_plugin_logger_prefix)
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self._manifest_filespec = MANIFEST_PATH_SQL_PLUGIN

    def test_model_initialization(self):
        """Test that the SAMSqlPlugin model can be initialized with valid data."""
        SAMSqlPlugin(
            apiVersion=self.loader.manifest_api_version,
            kind=self.loader.manifest_kind,
            metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
            spec=SAMSqlPluginSpec(**self.loader.manifest_spec),
            status=(
                SAMPluginCommonStatus(**self.loader.manifest_status)
                if self.loader and self.loader.manifest_status
                else None
            ),
        )

    def test_missing_required_fields(self):
        """Test that missing required fields raises ValidationError."""
        with self.assertRaises(PydanticValidationError):
            SAMSqlPlugin()  # type: ignore

    def test_invalid_field_types(self):
        """Test that wrong types for fields raises ValidationError."""
        with self.assertRaises(Exception):
            SAMSqlPlugin(
                apiVersion=123,  # type: ignore
                kind=456,  # type: ignore
                metadata=self.loader.manifest_metadata,  # type: ignore
                spec=self.loader.manifest_spec,  # type: ignore
            )

    def test_alternative_initialization(self):
        """
        Test that the SAMSqlPlugin model can be initialized using a single dict.
        """
        data = {
            "apiVersion": self.loader.manifest_api_version,
            "kind": self.loader.manifest_kind,
            "metadata": self.loader.manifest_metadata,
            "spec": self.loader.manifest_spec,
        }
        SAMSqlPlugin(**data)

    def test_immutability(self):
        """Test that the SAMSqlPlugin model is immutable after creation."""
        model = SAMSqlPlugin(
            apiVersion=self.loader.manifest_api_version,
            kind=self.loader.manifest_kind,
            metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
            spec=SAMSqlPluginSpec(**self.loader.manifest_spec),
        )
        with self.assertRaises(PydanticValidationError):
            model.kind = "NewKind"

    def test_optional_status_field(self):
        """Test that status is optional and can be omitted."""
        model = SAMSqlPlugin(
            apiVersion=self.loader.manifest_api_version,
            kind=self.loader.manifest_kind,
            metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
            spec=SAMSqlPluginSpec(**self.loader.manifest_spec),
        )
        self.assertIsNone(model.status)

    def test_invalid_spec_structure(self):
        """Test that invalid spec structure raises ValidationError."""
        with self.assertRaises(Exception):
            SAMSqlPlugin(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                spec={"not": "a valid spec"},  # type: ignore
            )

    def test_invalid_metadata_structure(self):
        """Test that invalid metadata structure raises ValidationError."""
        with self.assertRaises(Exception):
            SAMSqlPlugin(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata={"not": "a valid metadata"},  # type: ignore
                spec=SAMSqlPluginSpec(**self.loader.manifest_spec),
            )

    def test_empty_parameters(self):
        """Test that empty parameters list is valid if allowed by spec."""
        manifest_spec = dict(self.loader.manifest_spec)
        if "sqlData" in manifest_spec:
            manifest_spec["sqlData"] = dict(manifest_spec["sqlData"])
            manifest_spec["sqlData"]["parameters"] = []
        model = SAMSqlPlugin(
            apiVersion=self.loader.manifest_api_version,
            kind=self.loader.manifest_kind,
            metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
            spec=SAMSqlPluginSpec(**manifest_spec),
        )
        self.assertEqual(model.spec.sqlData.parameters, [])

    def test_parameter_missing_required_field(self):
        """Test that parameter missing required field raises ValidationError."""
        manifest_spec = dict(self.loader.manifest_spec)
        if "sqlData" in manifest_spec:
            manifest_spec["sqlData"] = dict(manifest_spec["sqlData"])
            param = dict(manifest_spec["sqlData"]["parameters"][0])
            if "type" in param:
                del param["type"]
            manifest_spec["sqlData"]["parameters"] = [param]
        with self.assertRaises(Exception):
            SAMSqlPlugin(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                spec=SAMSqlPluginSpec(**manifest_spec),
            )

    def test_parameter_wrong_type(self):
        """Test that parameter with wrong type value raises ValidationError."""
        manifest_spec = dict(self.loader.manifest_spec)
        if "sqlData" in manifest_spec:
            manifest_spec["sqlData"] = dict(manifest_spec["sqlData"])
            param = dict(manifest_spec["sqlData"]["parameters"][0])
            param["type"] = 123  # should be str
            manifest_spec["sqlData"]["parameters"] = [param]
        with self.assertRaises(Exception):
            SAMSqlPlugin(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                spec=SAMSqlPluginSpec(**manifest_spec),
            )

    def test_sql_query_required(self):
        """Test that sqlQuery is required in sqlData."""
        manifest_spec = dict(self.loader.manifest_spec)
        if "sqlData" in manifest_spec:
            manifest_spec["sqlData"] = dict(manifest_spec["sqlData"])
            if "sqlQuery" in manifest_spec["sqlData"]:
                del manifest_spec["sqlData"]["sqlQuery"]
        with self.assertRaises(Exception):
            SAMSqlPlugin(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                spec=SAMSqlPluginSpec(**manifest_spec),
            )

    def test_repr_and_str(self):
        """Test that model __repr__ and __str__ do not raise and include class name."""
        model = SAMSqlPlugin(
            apiVersion=self.loader.manifest_api_version,
            kind=self.loader.manifest_kind,
            metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
            spec=SAMSqlPluginSpec(**self.loader.manifest_spec),
        )
        self.assertIn("SAMSqlPlugin", repr(model))
        self.assertIn("SAMSqlPlugin", str(model))

    def test_sqldata_sqlquery_required_and_type(self):
        """Test that sqlQuery is required and must be a string."""
        manifest_spec = dict(self.loader.manifest_spec)
        if "sqlData" in manifest_spec:
            manifest_spec["sqlData"] = dict(manifest_spec["sqlData"])
            manifest_spec["sqlData"]["sqlQuery"] = "SELECT 42;"
        model = SAMSqlPlugin(
            apiVersion=self.loader.manifest_api_version,
            kind=self.loader.manifest_kind,
            metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
            spec=SAMSqlPluginSpec(**manifest_spec),
        )
        self.assertEqual(model.spec.sqlData.sqlQuery, "SELECT 42;")

        # Remove sqlQuery
        manifest_spec["sqlData"].pop("sqlQuery", None)
        with self.assertRaises(Exception):
            SAMSqlPlugin(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                spec=SAMSqlPluginSpec(**manifest_spec),
            )

        # Wrong type
        manifest_spec["sqlData"]["sqlQuery"] = 12345
        with self.assertRaises(Exception):
            SAMSqlPlugin(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                spec=SAMSqlPluginSpec(**manifest_spec),
            )

    def test_sqldata_parameters_various_cases(self):
        """Test parameters: present, None, empty, wrong type, invalid Parameter."""
        manifest_spec = dict(self.loader.manifest_spec)
        if "sqlData" in manifest_spec:
            manifest_spec["sqlData"] = dict(manifest_spec["sqlData"])
            # Valid list
            manifest_spec["sqlData"]["parameters"] = [
                {
                    "name": "foo",
                    "type": "string",
                    "description": "desc",
                }
            ]
            model = SAMSqlPlugin(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                spec=SAMSqlPluginSpec(**manifest_spec),
            )
            self.assertIsInstance(model.spec.sqlData.parameters, list)

            # None
            manifest_spec["sqlData"]["parameters"] = None
            model = SAMSqlPlugin(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                spec=SAMSqlPluginSpec(**manifest_spec),
            )
            self.assertIsNone(model.spec.sqlData.parameters)

            # Empty list
            manifest_spec["sqlData"]["parameters"] = []
            model = SAMSqlPlugin(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                spec=SAMSqlPluginSpec(**manifest_spec),
            )
            self.assertEqual(model.spec.sqlData.parameters, [])

            # Wrong type
            manifest_spec["sqlData"]["parameters"] = "notalist"
            with self.assertRaises(Exception):
                SAMSqlPlugin(
                    apiVersion=self.loader.manifest_api_version,
                    kind=self.loader.manifest_kind,
                    metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                    spec=SAMSqlPluginSpec(**manifest_spec),
                )

            # Invalid Parameter object (missing 'type')
            manifest_spec["sqlData"]["parameters"] = [{"name": "foo"}]
            with self.assertRaises(Exception):
                SAMSqlPlugin(
                    apiVersion=self.loader.manifest_api_version,
                    kind=self.loader.manifest_kind,
                    metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                    spec=SAMSqlPluginSpec(**manifest_spec),
                )

    def test_sqldata_testvalues_various_cases(self):
        """Test testValues: present, None, wrong type, valid/invalid TestValue."""
        manifest_spec = dict(self.loader.manifest_spec)
        if "sqlData" in manifest_spec:
            manifest_spec["sqlData"] = dict(manifest_spec["sqlData"])
            # Valid list
            manifest_spec["sqlData"]["testValues"] = [{"name": "foo", "value": 1}]
            model = SAMSqlPlugin(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                spec=SAMSqlPluginSpec(**manifest_spec),
            )
            self.assertIsInstance(model.spec.sqlData.testValues, list)

            # None
            manifest_spec["sqlData"]["testValues"] = None
            model = SAMSqlPlugin(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                spec=SAMSqlPluginSpec(**manifest_spec),
            )
            self.assertIsNone(model.spec.sqlData.testValues)

            # Wrong type
            manifest_spec["sqlData"]["testValues"] = "notalist"
            with self.assertRaises(Exception):
                SAMSqlPlugin(
                    apiVersion=self.loader.manifest_api_version,
                    kind=self.loader.manifest_kind,
                    metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                    spec=SAMSqlPluginSpec(**manifest_spec),
                )

            # Invalid TestValue object (missing 'name')
            manifest_spec["sqlData"]["testValues"] = [{"value": 1}]
            with self.assertRaises(Exception):
                SAMSqlPlugin(
                    apiVersion=self.loader.manifest_api_version,
                    kind=self.loader.manifest_kind,
                    metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                    spec=SAMSqlPluginSpec(**manifest_spec),
                )

    def test_sqldata_limit_default_and_validation(self):
        """Test limit: default, custom, below minimum, wrong type."""
        manifest_spec = dict(self.loader.manifest_spec)
        if "sqlData" in manifest_spec:
            manifest_spec["sqlData"] = dict(manifest_spec["sqlData"])
            # Remove limit for default
            manifest_spec["sqlData"].pop("limit", None)
            model = SAMSqlPlugin(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                spec=SAMSqlPluginSpec(**manifest_spec),
            )
            self.assertEqual(model.spec.sqlData.limit, 100)

            # Custom valid limit
            manifest_spec["sqlData"]["limit"] = 10
            model = SAMSqlPlugin(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                spec=SAMSqlPluginSpec(**manifest_spec),
            )
            self.assertEqual(model.spec.sqlData.limit, 10)

            # Invalid: limit <= 0
            manifest_spec["sqlData"]["limit"] = 0
            with self.assertRaises(Exception):
                SAMSqlPlugin(
                    apiVersion=self.loader.manifest_api_version,
                    kind=self.loader.manifest_kind,
                    metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                    spec=SAMSqlPluginSpec(**manifest_spec),
                )

            # Wrong type
            manifest_spec["sqlData"]["limit"] = "notanint"
            with self.assertRaises(Exception):
                SAMSqlPlugin(
                    apiVersion=self.loader.manifest_api_version,
                    kind=self.loader.manifest_kind,
                    metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                    spec=SAMSqlPluginSpec(**manifest_spec),
                )


# pylint: disable=W0223
class TestSqlPluginLegacy(TestPluginBase, ManifestTestsMixin, SqlConnectionTestMixin, AuthenticatedRequestMixin):
    """
    Test SAM manifest using ApiPlugin. This contains a mixture of
    Pydantic model tests and Django ORM model tests which should
    be refactored into separate test classes and moved to the broker
    test bank.

    The tests themselves are pretty good, it's just poorly organized.
    """

    _secret_model: Optional[SAMSecret] = None
    _sql_plugin_model: Optional[SAMSqlPlugin] = None
    _sql_connection_model: Optional[SAMSqlConnection] = None
    plugin_meta: Optional[PluginMeta] = None

    @property
    def secret_model(self) -> Optional[SAMSecret]:
        # override to create a SAMSecret pydantic model from the loader
        if not self._secret_model and self.loader:
            self._secret_model = SAMSecret(**self.loader.pydantic_model_dump())
            self.assertIsNotNone(self._secret_model)
        return self._secret_model

    @property
    def sql_connection_model(self) -> Optional[SAMSqlConnection]:
        # override to create a SAMSqlPlugin pydantic model from the loader
        # sep-2025 mcdaniel: WHY IS THIS NEEDED?
        if not isinstance(self.connection_model, SAMSqlConnection):
            raise SmarterValueError(
                f"connection_model is not an instance of SAMSqlConnection: {type(self.connection_model)} {self.connection_model}"
            )
        return self.connection_model

    @property
    def sql_plugin_model(self) -> Optional[SAMSqlPlugin]:
        # override to create a SAMSqlPlugin pydantic model from the loader
        if not self._sql_plugin_model and self.loader:
            self._sql_plugin_model = SAMSqlPlugin(**self.loader.pydantic_model_dump())
            self.assertIsNotNone(self._sql_plugin_model)
        return self._sql_plugin_model

    def test_00_sql_connection_mixin(self):
        """Test the SqlConnection itself, lest we get ahead of ourselves"""
        self.assertIsInstance(
            self.sql_connection_model,
            SAMSqlConnection,
            f"sql_connection_model is not an instance of SAMSqlConnection: {type(self.sql_connection_model)} {self.sql_connection_model}",
        )

    def test_validate_api_connection_invalid_value(self):
        """Test that the timeout validator raises an error for negative values."""
        self.load_manifest(filename="sql-plugin.yaml")
        if not isinstance(self._manifest, dict):
            self.fail("Manifest is not a dictionary")

        invalid_connection_string = "this $couldn't possibly be a valid connection name"
        self._manifest["spec"]["connection"] = invalid_connection_string
        self._loader = None
        self._sql_plugin_model = None
        with self.assertRaises(SAMValidationError) as context:
            print(self.sql_plugin_model)
        self.assertIn(
            "must be a valid cleanstring with no illegal characters",
            str(context.exception),
        )

    def test_validate_api_sql_query_invalid_value(self):
        """Test that the sqlQuery validator raises an error for invalid SQL syntax."""
        self.load_manifest(filename="sql-plugin.yaml")
        if not isinstance(self._manifest, dict):
            self.fail("Manifest is not a dictionary")

        invalid_sql_query = None
        self._manifest["spec"]["sqlData"]["sqlQuery"] = invalid_sql_query
        self._loader = None
        self._sql_plugin_model = None
        with self.assertRaises(PydanticValidationError) as context:
            # spec.sqlData.sqlQuery
            print(self.sql_plugin_model)
        self.assertIn(
            "Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]",
            str(context.exception),
        )

    def test_validate_api_sql_parameters_invalid_type(self):
        """Test that the parameters validator raises an error for invalid parameter types."""
        self.load_manifest(filename="sql-plugin.yaml")
        if not isinstance(self._manifest, dict):
            self.fail("Manifest is not a dictionary")

        invalid_parameters = [
            {
                "name": "limit",
                "description": "The maximum number of results to return.",
            },
        ]

        self._manifest["spec"]["sqlData"]["parameters"] = invalid_parameters
        self._loader = None
        self._sql_plugin_model = None
        with self.assertRaises(PydanticValidationError) as context:
            # spec.sqlData.parameters.0.type
            #   Field required [type=missing, input_value={'name': 'limit', 'descri... of results to return.'}, input_type=dict]
            print(self.sql_plugin_model)
        self.assertIn(
            "Field required [type=missing, input_value={'name': 'limit'",
            str(context.exception),
        )

    def test_validate_api_sql_parameters_missing_required(self):
        """Test that the parameters validator raises an error for missing required parameters."""

        # create the secret
        self._loader = None
        self._manifest = None
        self.load_manifest(filename="secret-smarter.yaml")
        secret_broker = SAMSecretBroker(
            self.request,
            loader=self.loader,
            manifest=self.secret_model,
        )
        secret_broker.apply(self.request)

        # create the connection
        self._loader = None
        self._manifest = None
        self.load_manifest(filename="sql-connection.yaml")
        connection_broker = SAMSqlConnectionBroker(
            self.request,
            loader=self.connection_loader,
            manifest=self.sql_connection_model,
        )
        connection_broker.apply(self.request)

        # create the plugin
        self._loader = None
        self._manifest = None
        self.load_manifest(filename="sql-plugin.yaml")
        if not isinstance(self._manifest, dict):
            self.fail("Manifest is not a dictionary")

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

        sam_sql_plugin = SAMSqlPlugin(**self._manifest)

        self._sql_plugin_model = None
        with self.assertRaises(SmarterValueError) as context:
            SqlPlugin(manifest=sam_sql_plugin, user_profile=self.user_profile)
        self.assertIn(
            "Placeholder 'username' is not defined in parameter",
            str(context.exception),
        )
