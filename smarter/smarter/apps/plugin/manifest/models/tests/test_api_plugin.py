"""
Test SAM Plugin manifest using ApiPlugin
Test cases for the PluginDataAPI Manifest.

http://localhost:8000/api/v1/tests/unauthenticated/dict/
http://localhost:8000/api/v1/tests/unauthenticated/list/
http://localhost:8000/api/v1/tests/authenticated/dict/
http://localhost:8000/api/v1/tests/authenticated/list/
"""

import logging
import os
from typing import Optional

from pydantic_core import ValidationError as PydanticValidationError

from smarter.apps.account.manifest.brokers.secret import SAMSecretBroker
from smarter.apps.account.manifest.models.secret.model import SAMSecret
from smarter.apps.account.models import Secret
from smarter.apps.plugin.const import DATA_PATH as PLUGIN_DATA_PATH
from smarter.apps.plugin.manifest.brokers.api_connection import SAMApiConnectionBroker
from smarter.apps.plugin.manifest.brokers.api_plugin import SAMApiPluginBroker
from smarter.apps.plugin.manifest.models.api_connection.model import SAMApiConnection
from smarter.apps.plugin.manifest.models.api_plugin.model import SAMApiPlugin
from smarter.apps.plugin.manifest.models.api_plugin.spec import SAMApiPluginSpec
from smarter.apps.plugin.manifest.models.common.plugin.metadata import (
    SAMPluginCommonMetadata,
)
from smarter.apps.plugin.manifest.models.common.plugin.status import (
    SAMPluginCommonStatus,
)
from smarter.apps.plugin.models import ApiConnection, PluginDataApi, PluginMeta
from smarter.apps.plugin.tests.base_classes import ManifestTestsMixin, TestPluginBase
from smarter.apps.plugin.tests.mixins import (
    ApiConnectionTestMixin,
    AuthenticatedRequestMixin,
)
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.journal.enum import SmarterJournalThings
from smarter.lib.journal.http import SmarterJournaledJsonResponse
from smarter.lib.manifest.broker import SAMBrokerError
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.loader import SAMLoader
from smarter.lib.manifest.tests.test_broker_base import TestSAMBrokerBaseClass


logger = logging.getLogger(__name__)
MANIFEST_PATH_API_PLUGIN = os.path.abspath(
    os.path.join(PLUGIN_DATA_PATH, "manifest", "brokers", "tests", "data", "api-plugin.yaml")
)
"""
Path to the Api plugin manifest file 'api-plugin.yaml' which
contains the actual connection parameters for the remote test database.

Note that we're borrowing the sql-connection.yaml file from the
broker tests.
"""
HERE = __name__


class TestSAMApiPlugin(TestSAMBrokerBaseClass):
    """
    Test SAMApiPlugin Pydantic model.

    .. note::

        TestSAMBrokerBaseClass is generically useful for testing SAM-based
        Pydantic models.
    """

    test_sam_api_plugin_logger_prefix = formatted_text(f"{HERE}.TestSAMApiPlugin()")

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        logger.debug("%s.setUpClass()", cls.test_sam_api_plugin_logger_prefix)
        cls.loader = SAMLoader(file_path=MANIFEST_PATH_API_PLUGIN)

    @classmethod
    def tearDownClass(cls):
        logger.debug("%s.tearDownClass()", cls.test_sam_api_plugin_logger_prefix)
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self._manifest_filespec = MANIFEST_PATH_API_PLUGIN

    def test_model_initialization(self):
        """Test that the SAMApiPlugin model can be initialized with valid data."""
        SAMApiPlugin(
            apiVersion=self.loader.manifest_api_version,
            kind=self.loader.manifest_kind,
            metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
            spec=SAMApiPluginSpec(**self.loader.manifest_spec),
            status=SAMPluginCommonStatus(**self.loader.manifest_status) if self.loader.manifest_status else None,
        )

    def test_apidata_endpoint_required_and_validation(self):
        """Test endpoint is required and validated as a URL endpoint."""
        manifest_spec = dict(self.loader.manifest_spec)
        if "apiData" in manifest_spec:
            manifest_spec["apiData"] = dict(manifest_spec["apiData"])
            manifest_spec["apiData"]["endpoint"] = "/v1/test"
        model = SAMApiPlugin(
            apiVersion=self.loader.manifest_api_version,
            kind=self.loader.manifest_kind,
            metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
            spec=SAMApiPluginSpec(**manifest_spec),
        )
        # the validator should have added a trailing slash
        self.assertEqual(model.spec.apiData.endpoint, "/v1/test/")

        # Remove endpoint
        manifest_spec["apiData"].pop("endpoint", None)
        with self.assertRaises(Exception):
            SAMApiPlugin(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                spec=SAMApiPluginSpec(**manifest_spec),
            )

        # Invalid endpoint
        manifest_spec["apiData"]["endpoint"] = "not a valid endpoint"
        with self.assertRaises(Exception):
            SAMApiPlugin(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                spec=SAMApiPluginSpec(**manifest_spec),
            )

    def test_apidata_method_default_and_validation(self):
        """Test method defaults to GET and validates allowed values."""
        manifest_spec = dict(self.loader.manifest_spec)
        if "apiData" in manifest_spec:
            manifest_spec["apiData"] = dict(manifest_spec["apiData"])
            manifest_spec["apiData"].pop("method", None)
        model = SAMApiPlugin(
            apiVersion=self.loader.manifest_api_version,
            kind=self.loader.manifest_kind,
            metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
            spec=SAMApiPluginSpec(**manifest_spec),
        )
        self.assertEqual(model.spec.apiData.method, "GET")

        # Valid method
        manifest_spec["apiData"]["method"] = "POST"
        model = SAMApiPlugin(
            apiVersion=self.loader.manifest_api_version,
            kind=self.loader.manifest_kind,
            metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
            spec=SAMApiPluginSpec(**manifest_spec),
        )
        self.assertEqual(model.spec.apiData.method, "POST")

        # Invalid method
        manifest_spec["apiData"]["method"] = "FOO"
        with self.assertRaises(Exception):
            SAMApiPlugin(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                spec=SAMApiPluginSpec(**manifest_spec),
            )

    def test_apidata_url_params(self):
        """Test urlParams: present, None, wrong type, valid/invalid UrlParam."""
        manifest_spec = dict(self.loader.manifest_spec)
        if "apiData" in manifest_spec:
            manifest_spec["apiData"] = dict(manifest_spec["apiData"])
            manifest_spec["apiData"]["urlParams"] = [{"key": "city", "value": "SF"}]
            model = SAMApiPlugin(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                spec=SAMApiPluginSpec(**manifest_spec),
            )
            self.assertIsInstance(model.spec.apiData.urlParams, list)

            manifest_spec["apiData"]["urlParams"] = None
            model = SAMApiPlugin(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                spec=SAMApiPluginSpec(**manifest_spec),
            )
            self.assertIsNone(model.spec.apiData.urlParams)

            manifest_spec["apiData"]["urlParams"] = "notalist"
            with self.assertRaises(Exception):
                SAMApiPlugin(
                    apiVersion=self.loader.manifest_api_version,
                    kind=self.loader.manifest_kind,
                    metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                    spec=SAMApiPluginSpec(**manifest_spec),
                )

            manifest_spec["apiData"]["urlParams"] = [{"value": "SF"}]
            with self.assertRaises(Exception):
                SAMApiPlugin(
                    apiVersion=self.loader.manifest_api_version,
                    kind=self.loader.manifest_kind,
                    metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                    spec=SAMApiPluginSpec(**manifest_spec),
                )

    def test_apidata_headers(self):
        """Test headers: present, None, wrong type, valid/invalid RequestHeader."""
        manifest_spec = dict(self.loader.manifest_spec)
        if "apiData" in manifest_spec:
            manifest_spec["apiData"] = dict(manifest_spec["apiData"])
            manifest_spec["apiData"]["headers"] = [{"name": "Authorization", "value": "Bearer token"}]
            model = SAMApiPlugin(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                spec=SAMApiPluginSpec(**manifest_spec),
            )
            self.assertIsInstance(model.spec.apiData.headers, list)

            manifest_spec["apiData"]["headers"] = None
            model = SAMApiPlugin(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                spec=SAMApiPluginSpec(**manifest_spec),
            )
            self.assertIsNone(model.spec.apiData.headers)

            manifest_spec["apiData"]["headers"] = "notalist"
            with self.assertRaises(Exception):
                SAMApiPlugin(
                    apiVersion=self.loader.manifest_api_version,
                    kind=self.loader.manifest_kind,
                    metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                    spec=SAMApiPluginSpec(**manifest_spec),
                )

            manifest_spec["apiData"]["headers"] = [{"value": "Bearer token"}]
            with self.assertRaises(Exception):
                SAMApiPlugin(
                    apiVersion=self.loader.manifest_api_version,
                    kind=self.loader.manifest_kind,
                    metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                    spec=SAMApiPluginSpec(**manifest_spec),
                )

    def test_apidata_body(self):
        """Test body: present, None, wrong type."""
        manifest_spec = dict(self.loader.manifest_spec)
        if "apiData" in manifest_spec:
            manifest_spec["apiData"] = dict(manifest_spec["apiData"])
            manifest_spec["apiData"]["body"] = {"foo": "bar"}
            model = SAMApiPlugin(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                spec=SAMApiPluginSpec(**manifest_spec),
            )
            self.assertIsInstance(model.spec.apiData.body, dict)

            manifest_spec["apiData"]["body"] = [1, 2, 3]
            model = SAMApiPlugin(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                spec=SAMApiPluginSpec(**manifest_spec),
            )
            self.assertIsInstance(model.spec.apiData.body, list)

            manifest_spec["apiData"]["body"] = None
            model = SAMApiPlugin(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                spec=SAMApiPluginSpec(**manifest_spec),
            )
            self.assertIsNone(model.spec.apiData.body)

            manifest_spec["apiData"]["body"] = "notjson"
            with self.assertRaises(Exception):
                SAMApiPlugin(
                    apiVersion=self.loader.manifest_api_version,
                    kind=self.loader.manifest_kind,
                    metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                    spec=SAMApiPluginSpec(**manifest_spec),
                )

    def test_missing_required_fields(self):
        """Test that missing required fields raises ValidationError."""
        with self.assertRaises(PydanticValidationError):
            SAMApiPlugin()  # type: ignore

    def test_invalid_field_types(self):
        """Test that wrong types for fields raises ValidationError."""
        with self.assertRaises(Exception):
            SAMApiPlugin(
                apiVersion=123,  # type: ignore
                kind=456,  # type: ignore
                metadata=self.loader.manifest_metadata,  # type: ignore
                spec=self.loader.manifest_spec,  # type: ignore
            )

    def test_alternative_initialization(self):
        """
        Test that the SAMApiPlugin model can be initialized using a single dict.
        """
        data = {
            "apiVersion": self.loader.manifest_api_version,
            "kind": self.loader.manifest_kind,
            "metadata": self.loader.manifest_metadata,
            "spec": self.loader.manifest_spec,
        }
        SAMApiPlugin(**data)

    def test_immutability(self):
        """Test that the SAMApiPlugin model is immutable after creation."""

        model = SAMApiPlugin(
            apiVersion=self.loader.manifest_api_version,
            kind=self.loader.manifest_kind,
            metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
            spec=SAMApiPluginSpec(**self.loader.manifest_spec),
        )
        with self.assertRaises(PydanticValidationError):
            model.kind = "NewKind"

    def test_optional_status_field(self):
        """Test that status is optional and can be omitted."""
        model = SAMApiPlugin(
            apiVersion=self.loader.manifest_api_version,
            kind=self.loader.manifest_kind,
            metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
            spec=SAMApiPluginSpec(**self.loader.manifest_spec),
        )
        self.assertIsNone(model.status)

    def test_invalid_spec_structure(self):
        """Test that invalid spec structure raises ValidationError."""
        with self.assertRaises(Exception):
            SAMApiPlugin(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                spec={"not": "a valid spec"},  # type: ignore
            )

    def test_invalid_metadata_structure(self):
        """Test that invalid metadata structure raises ValidationError."""
        with self.assertRaises(Exception):
            SAMApiPlugin(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata={"not": "a valid metadata"},  # type: ignore
                spec=SAMApiPluginSpec(**self.loader.manifest_spec),
            )

    def test_empty_parameters(self):
        """Test that empty parameters list is valid if allowed by spec."""
        manifest_spec = dict(self.loader.manifest_spec)
        if "apiData" in manifest_spec:
            manifest_spec["apiData"] = dict(manifest_spec["apiData"])
            manifest_spec["apiData"]["parameters"] = []
        model = SAMApiPlugin(
            apiVersion=self.loader.manifest_api_version,
            kind=self.loader.manifest_kind,
            metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
            spec=SAMApiPluginSpec(**manifest_spec),
        )
        self.assertEqual(model.spec.apiData.parameters, [])

    def test_parameter_missing_required_field(self):
        """Test that parameter missing required field raises ValidationError."""
        manifest_spec = dict(self.loader.manifest_spec)
        if "apiData" in manifest_spec:
            manifest_spec["apiData"] = dict(manifest_spec["apiData"])
            param = dict(manifest_spec["apiData"]["parameters"][0])
            if "type" in param:
                del param["type"]
            manifest_spec["apiData"]["parameters"] = [param]
        with self.assertRaises(Exception):
            SAMApiPlugin(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                spec=SAMApiPluginSpec(**manifest_spec),
            )

    def test_parameter_wrong_type(self):
        """Test that parameter with wrong type value raises ValidationError."""
        manifest_spec = dict(self.loader.manifest_spec)
        if "apiData" in manifest_spec:
            manifest_spec["apiData"] = dict(manifest_spec["apiData"])
            param = dict(manifest_spec["apiData"]["parameters"][0])
            param["type"] = 123  # should be str
            manifest_spec["apiData"]["parameters"] = [param]
        with self.assertRaises(Exception):
            SAMApiPlugin(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                spec=SAMApiPluginSpec(**manifest_spec),
            )

    def test_repr_and_str(self):
        """Test that model __repr__ and __str__ do not raise and include class name."""
        model = SAMApiPlugin(
            apiVersion=self.loader.manifest_api_version,
            kind=self.loader.manifest_kind,
            metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
            spec=SAMApiPluginSpec(**self.loader.manifest_spec),
        )
        self.assertIn("SAMApiPlugin", repr(model))
        self.assertIn("SAMApiPlugin", str(model))

    def test_apidata_parameters_various_cases(self):
        """Test parameters: present, None, empty, wrong type, invalid Parameter."""
        manifest_spec = dict(self.loader.manifest_spec)
        if "apiData" in manifest_spec:
            manifest_spec["apiData"] = dict(manifest_spec["apiData"])
            # Valid list
            manifest_spec["apiData"]["parameters"] = [
                {
                    "name": "foo",
                    "type": "string",
                    "description": "desc",
                }
            ]
            model = SAMApiPlugin(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                spec=SAMApiPluginSpec(**manifest_spec),
            )
            self.assertIsInstance(model.spec.apiData.parameters, list)

            # None
            manifest_spec["apiData"]["parameters"] = None
            model = SAMApiPlugin(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                spec=SAMApiPluginSpec(**manifest_spec),
            )
            self.assertIsNone(model.spec.apiData.parameters)

            # Empty list
            manifest_spec["apiData"]["parameters"] = []
            model = SAMApiPlugin(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                spec=SAMApiPluginSpec(**manifest_spec),
            )
            self.assertEqual(model.spec.apiData.parameters, [])

            # Wrong type
            manifest_spec["apiData"]["parameters"] = "notalist"
            with self.assertRaises(Exception):
                SAMApiPlugin(
                    apiVersion=self.loader.manifest_api_version,
                    kind=self.loader.manifest_kind,
                    metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                    spec=SAMApiPluginSpec(**manifest_spec),
                )

            # Invalid Parameter object (missing 'type')
            manifest_spec["apiData"]["parameters"] = [{"name": "foo"}]
            with self.assertRaises(Exception):
                SAMApiPlugin(
                    apiVersion=self.loader.manifest_api_version,
                    kind=self.loader.manifest_kind,
                    metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                    spec=SAMApiPluginSpec(**manifest_spec),
                )

    def test_apidata_testvalues_various_cases(self):
        """Test testValues: present, None, wrong type, valid/invalid TestValue."""
        manifest_spec = dict(self.loader.manifest_spec)
        if "apiData" in manifest_spec:
            manifest_spec["apiData"] = dict(manifest_spec["apiData"])
            # Valid list
            manifest_spec["apiData"]["testValues"] = [{"name": "foo", "value": 1}]
            model = SAMApiPlugin(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                spec=SAMApiPluginSpec(**manifest_spec),
            )
            self.assertIsInstance(model.spec.apiData.testValues, list)

            # None
            manifest_spec["apiData"]["testValues"] = None
            model = SAMApiPlugin(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                spec=SAMApiPluginSpec(**manifest_spec),
            )
            self.assertIsNone(model.spec.apiData.testValues)

            # Wrong type
            manifest_spec["apiData"]["testValues"] = "notalist"
            with self.assertRaises(Exception):
                SAMApiPlugin(
                    apiVersion=self.loader.manifest_api_version,
                    kind=self.loader.manifest_kind,
                    metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                    spec=SAMApiPluginSpec(**manifest_spec),
                )

            # Invalid TestValue object (missing 'name')
            manifest_spec["apiData"]["testValues"] = [{"value": 1}]
            with self.assertRaises(Exception):
                SAMApiPlugin(
                    apiVersion=self.loader.manifest_api_version,
                    kind=self.loader.manifest_kind,
                    metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                    spec=SAMApiPluginSpec(**manifest_spec),
                )

    def test_apidata_limit_default_and_validation(self):
        """Test limit: default, custom, below minimum, wrong type."""
        manifest_spec = dict(self.loader.manifest_spec)
        if "apiData" in manifest_spec:
            manifest_spec["apiData"] = dict(manifest_spec["apiData"])
            # Remove limit for default
            manifest_spec["apiData"].pop("limit", None)
            model = SAMApiPlugin(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                spec=SAMApiPluginSpec(**manifest_spec),
            )
            self.assertEqual(model.spec.apiData.limit, 100)

            # Custom valid limit
            manifest_spec["apiData"]["limit"] = 10
            model = SAMApiPlugin(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                spec=SAMApiPluginSpec(**manifest_spec),
            )
            self.assertEqual(model.spec.apiData.limit, 10)

            # Invalid: limit <= 0
            manifest_spec["apiData"]["limit"] = 0
            with self.assertRaises(Exception):
                SAMApiPlugin(
                    apiVersion=self.loader.manifest_api_version,
                    kind=self.loader.manifest_kind,
                    metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                    spec=SAMApiPluginSpec(**manifest_spec),
                )

            # Wrong type
            manifest_spec["apiData"]["limit"] = "notanint"
            with self.assertRaises(Exception):
                SAMApiPlugin(
                    apiVersion=self.loader.manifest_api_version,
                    kind=self.loader.manifest_kind,
                    metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                    spec=SAMApiPluginSpec(**manifest_spec),
                )


# pylint: disable=W0223
class TestApiPluginLegacy(TestPluginBase, ManifestTestsMixin, ApiConnectionTestMixin, AuthenticatedRequestMixin):
    """Test SAM manifest using ApiPlugin"""

    _secret_model: Optional[SAMSecret] = None
    _api_plugin_model: Optional[SAMApiPlugin] = None
    _api_connection_model: Optional[SAMApiConnection] = None
    plugin_meta: Optional[PluginMeta] = None

    @property
    def secret_model(self) -> Optional[SAMSecret]:
        # override to create a SAMSecret pydantic model from the loader
        if not self._secret_model and self.loader:
            self._secret_model = SAMSecret(**self.loader.pydantic_model_dump())
            self.assertIsNotNone(self._secret_model)
        return self._secret_model

    @property
    def api_connection_model(self) -> Optional[SAMApiConnection]:
        # override to create a SAMApiPlugin pydantic model from the loader
        if not self._api_connection_model and self.loader:
            self._api_connection_model = SAMApiConnection(**self.loader.pydantic_model_dump())
            self.assertIsNotNone(self._api_connection_model)
        return self._api_connection_model

    @property
    def api_plugin_model(self) -> Optional[SAMApiPlugin]:
        # override to create a SAMApiPlugin pydantic model from the loader
        if not self._api_plugin_model and self.loader:
            self._api_plugin_model = SAMApiPlugin(**self.loader.pydantic_model_dump())
            self.assertIsNotNone(self._api_plugin_model)
        return self._api_plugin_model

    def test_00_api_connection_mixin(self):
        """Test the ApiConnection itself, lest we get ahead of ourselves"""
        self.assertIsInstance(self.connection_django_model, ApiConnection)
        self.assertIsInstance(self.connection_model, SAMApiConnection)
        self.assertIsInstance(self.connection_loader, SAMLoader)
        self.assertIsInstance(self.connection_manifest, dict)
        self.assertIsInstance(self.connection_manifest_path, str)

        self.assertEqual(self.connection_model.kind, SmarterJournalThings.API_CONNECTION.value)

    def test_validate_api_connection_invalid_value(self):
        """Test that the timeout validator raises an error for negative values."""
        self.load_manifest(filename="api-plugin.yaml")
        if not isinstance(self._manifest, dict):
            self.fail("Manifest is not a dictionary")

        invalid_connection_string = "this $couldn't possibly be a valid connection name"
        self._manifest["spec"]["connection"] = invalid_connection_string
        self._loader = None
        self._api_plugin_model = None
        with self.assertRaises(SAMValidationError) as context:
            print(self.api_plugin_model)
        self.assertIn(
            "Smarter API Manifest validation error",
            str(context.exception),
        )

    def test_validate_api_invalid_parameter_value(self):
        """Test for invalid parameters passed."""
        self.load_manifest(filename="api-plugin.yaml")
        if not isinstance(self._manifest, dict):
            self.fail("Manifest is not a dictionary")

        logger.warning("FIX NOTE: WRITE THIS UNIT TEST!!!!")

    def test_validate_api_api_parameters_invalid_type(self):
        """Test that the parameters validator raises an error for invalid parameter types."""
        self.load_manifest(filename="api-plugin.yaml")
        if not isinstance(self._manifest, dict):
            self.fail("Manifest is not a dictionary")

        invalid_parameters = [
            {
                "name": "limit",
                "description": "The maximum number of results to return.",
            },
        ]

        self._manifest["spec"]["apiData"]["parameters"] = invalid_parameters
        self._loader = None
        self._api_plugin_model = None
        with self.assertRaises(PydanticValidationError) as context:
            # spec.apiData.parameters.0.type
            #   Field required [type=missing, input_value={'name': 'limit', 'descri... of results to return.'}, input_type=dict]
            print(self.api_plugin_model)
        self.assertIn(
            "Field required [type=missing, input_value={'name': 'limit'",
            str(context.exception),
        )

    def test_validate_api_parameters_missing_required(self):
        """Test that the parameters validator raises an error for missing required parameters."""
        self.load_manifest(filename="api-plugin.yaml")
        if not isinstance(self._manifest, dict):
            self.fail("Manifest is not a dictionary")

        self._manifest["spec"]["apiData"] = {
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
        self._api_plugin_model = None
        with self.assertRaises(PydanticValidationError) as context:
            # spec.apiData.parameters.0.default
            print(self.api_plugin_model)
        self.assertIn(
            "validation error",
            str(context.exception),
        )
        self.assertIn(
            "Field required",
            str(context.exception),
        )

    def test_django_orm(self):
        """
        Test that the Django model can be initialized from the Pydantic model.

        FIX NOTE: WE HAVE TO LOAD THIS VIA THE BROKER, IN PART
        BC THE FUNCTION CALL PARAMETERS HAVE TO BE REFORMATTED
        FROM LIST TO DICT.
        """
        # 1.) create a secret for the Api connection
        self._loader = None
        self._manifest = None
        self.load_manifest(filename="secret-smarter.yaml")
        if not isinstance(self.loader, SAMLoader):
            self.fail("Loader is not an instance of SAMLoader")
        if not isinstance(self._manifest, dict):
            self.fail("Manifest is not a dictionary")

        if self.secret_model is None:
            self.fail("Secret model is None, did you load the manifest?")

        secret_broker = SAMSecretBroker(
            self.request,
            loader=self.loader,
            manifest=self.secret_model,
        )
        secret_broker.apply(self.request)
        if not isinstance(secret_broker.secret, Secret):
            self.fail("secret is not an instance of SAMSecret")

        # 2.) create an Api connection
        self._loader = None
        self._manifest = None
        self.load_manifest(filename="api-connection.yaml")
        if not isinstance(self.loader, SAMLoader):
            self.fail("Loader is not an instance of SAMLoader")
        if not isinstance(self._manifest, dict):
            self.fail("Manifest is not a dictionary")

        if self.api_connection_model is None:
            self.fail("ApiConnection model is None, did you load the manifest?")

        connection_broker = SAMApiConnectionBroker(
            self.request,
            loader=self.connection_loader,
            manifest=self.connection_model,
        )
        connection_broker.apply(self.request)

        # 3.) create an Api plugin
        self._loader = None
        self._manifest = None
        self.load_manifest(filename="api-plugin.yaml")
        if not isinstance(self.loader, SAMLoader):
            self.fail("Loader is not an instance of SAMLoader")
        if not isinstance(self._manifest, dict):
            self.fail("Manifest is not a dictionary")

        api_plugin_broker = SAMApiPluginBroker(self.request, loader=self.loader, manifest=self.api_plugin_model)
        api_plugin_broker.apply(self.request)
        self.plugin_meta = api_plugin_broker.plugin_meta

        if not isinstance(self.plugin_meta, PluginMeta):
            self.fail("plugin_meta is not an instance of PluginMeta")
        if self.api_plugin_model is None:
            self.fail("ApiPlugin model is None, did you load the manifest?")

        # 4.) try to save it
        self.plugin_meta.save()

        response = api_plugin_broker.describe(self.request)
        self.assertIsInstance(response, SmarterJournaledJsonResponse)
        self.assertEqual(response.status_code, 200)

        # ---------------------------------------------------------------------
        # tear down the test data
        # ---------------------------------------------------------------------
        try:
            api_plugin_broker.delete(self.request)
        except (PluginDataApi.DoesNotExist, ValueError, SAMBrokerError):
            pass

        try:
            connection_broker.delete(self.request)
        except (ApiConnection.DoesNotExist, ValueError, SAMBrokerError):
            pass

        try:
            secret_broker.delete(self.request)
        except (Secret.DoesNotExist, ValueError, SAMBrokerError):
            pass
