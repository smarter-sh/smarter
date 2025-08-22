"""
Test SAM Plugin manifest using ApiPlugin
Test cases for the PluginDataAPI Manifest.

http://localhost:8000/api/v1/tests/unauthenticated/dict/
http://localhost:8000/api/v1/tests/unauthenticated/list/
http://localhost:8000/api/v1/tests/authenticated/dict/
http://localhost:8000/api/v1/tests/authenticated/list/
"""

import logging
from typing import Optional

from pydantic_core import ValidationError as PydanticValidationError

from smarter.apps.account.manifest.brokers.secret import SAMSecretBroker
from smarter.apps.account.manifest.models.secret.model import SAMSecret
from smarter.apps.account.models import Secret
from smarter.apps.plugin.manifest.brokers.api_connection import SAMApiConnectionBroker
from smarter.apps.plugin.manifest.brokers.api_plugin import SAMApiPluginBroker
from smarter.apps.plugin.manifest.models.api_connection.model import SAMApiConnection
from smarter.apps.plugin.manifest.models.api_plugin.model import SAMApiPlugin
from smarter.apps.plugin.models import ApiConnection, PluginDataApi, PluginMeta
from smarter.apps.plugin.tests.base_classes import ManifestTestsMixin, TestPluginBase
from smarter.apps.plugin.tests.mixins import (
    ApiConnectionTestMixin,
    AuthenticatedRequestMixin,
)
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.journal.enum import SmarterJournalThings
from smarter.lib.journal.http import SmarterJournaledJsonResponse
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.loader import SAMLoader


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PLUGIN_LOGGING) and level >= logging.INFO


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


# pylint: disable=W0223
class TestApiPlugin(TestPluginBase, ManifestTestsMixin, ApiConnectionTestMixin, AuthenticatedRequestMixin):
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
            manifest=self.manifest,
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
            manifest=self.connection_manifest,
        )
        connection_broker.apply(self.request)

        self._loader = None
        self._manifest = None
        self.load_manifest(filename="api-plugin.yaml")
        if not isinstance(self.loader, SAMLoader):
            self.fail("Loader is not an instance of SAMLoader")
        if not isinstance(self._manifest, dict):
            self.fail("Manifest is not a dictionary")

        # 3.) create an Api plugin
        api_plugin_broker = SAMApiPluginBroker(
            self.request,
            loader=self.loader,
            manifest=self.manifest,
        )
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
        except (PluginDataApi.DoesNotExist, ValueError):
            pass

        try:
            connection_broker.delete(self.request)
        except (ApiConnection.DoesNotExist, ValueError):
            pass

        try:
            secret_broker.delete(self.request)
        except (Secret.DoesNotExist, ValueError):
            pass
