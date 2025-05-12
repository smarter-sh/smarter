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
from smarter.apps.plugin.manifest.models.api_connection.model import SAMApiConnection
from smarter.apps.plugin.manifest.models.api_plugin.model import SAMApiPlugin
from smarter.apps.plugin.models import ApiConnection, PluginDataApi, PluginMeta
from smarter.apps.plugin.tests.base_classes import ManifestTestsMixin, TestPluginBase
from smarter.apps.plugin.tests.mixins import ApiConnectionTestMixin
from smarter.common.exceptions import SmarterValueError
from smarter.common.utils import camel_to_snake_dict
from smarter.lib.journal.enum import SmarterJournalThings
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.loader import SAMLoader


class TestApiPlugin(TestPluginBase, ManifestTestsMixin, ApiConnectionTestMixin):
    """Test SAM manifest using ApiPlugin"""

    _model: SAMApiPlugin = None
    plugin_meta: PluginMeta = None

    @property
    def model(self) -> SAMApiPlugin:
        # override to create a SAMApiPlugin pydantic model from the loader
        if not self._model and self.loader:
            self._model = SAMApiPlugin(**self.loader.pydantic_model_dump())
            self.assertIsNotNone(self._model)
        return self._model

    def test_00_api_connection_mixin(self):
        """
        Test the ApiConnection itself, lest we get ahead of ourselves
        """
        self.assertIsInstance(self.connection_django_model, ApiConnection)
        self.assertIsInstance(self.connection_model, SAMApiConnection)
        self.assertIsInstance(self.connection_loader, SAMLoader)
        self.assertIsInstance(self.connection_manifest, dict)
        self.assertIsInstance(self.connection_manifest_path, str)

        self.assertEqual(self.connection_model.kind, SmarterJournalThings.API_CONNECTION.value)

    def test_01_valid_api_plugin(self):
        """Test that we can load a valid manifest."""
        self.load_manifest(filename="api-plugin.yaml")
        # pylint: disable=W0104
        self.model

    def test_validate_connection_invalid_value(self):
        """Test that the timeout validator raises an error for negative values."""
        self.load_manifest(filename="api-plugin.yaml")

        invalid_connection_string = "this $couldn't possibly be a valid connection name"
        self._manifest["spec"]["connection"] = invalid_connection_string
        self._loader = None
        self._model = None
        with self.assertRaises(SAMValidationError) as context:
            print(self.model)
        self.assertIn(
            "Connection must be a valid cleanstring",
            str(context.exception),
        )

    def test_validate_connection_invalid_type(self):
        """Test that the timeout validator raises an error for negative values."""
        self.load_manifest(filename="api-plugin.yaml")

        invalid_connection_string = 1234567890
        self._manifest["spec"]["connection"] = invalid_connection_string
        self._loader = None
        self._model = None
        with self.assertRaises(ValidationError) as context:
            print(self.model)
        self.assertIn(
            "Input should be a valid string ",
            str(context.exception),
        )

    def test_validate_endpoint_invalid(self):
        """Test that the timeout validator raises an error for negative values."""
        self.load_manifest(filename="api-plugin.yaml")

        invalid_endpoint = "not a good endpoint"
        self._manifest["spec"]["apiData"]["endpoint"] = invalid_endpoint
        self._loader = None
        self._model = None
        with self.assertRaises(SAMValidationError) as context:
            print(self.model)
        self.assertIn(
            "URL endpoint 'not a good endpoint' contains invalid characters",
            str(context.exception),
        )

    def test_validate_endpoint_invalid_type(self):
        """Test that the timeout validator raises an error for negative values."""
        self.load_manifest(filename="api-plugin.yaml")

        invalid_endpoint = 1234567890
        self._manifest["spec"]["apiData"]["endpoint"] = invalid_endpoint
        self._loader = None
        self._model = None
        with self.assertRaises(ValidationError) as context:
            print(self.model)
        self.assertIn(
            "Input should be a valid string",
            str(context.exception),
        )

    def test_validate_parameters_invalid(self):
        """Test that the timeout validator raises an error for negative values."""
        self.load_manifest(filename="api-plugin.yaml")

        invalid_parameters = [
            {
                "name": "limit",
                "description": "The maximum number of results to return.",
            },
        ]

        self._manifest["spec"]["apiData"]["parameters"] = invalid_parameters
        self._loader = None
        self._model = None
        with self.assertRaises(ValidationError) as context:
            # spec.apiData.parameters.0.type
            #   Field required [type=missing, input_value={'name': 'limit', 'descri... of results to return.'}, input_type=dict]
            print(self.model)
        self.assertIn(
            "Field required [type=missing, input_value={'name': 'limit'",
            str(context.exception),
        )

    def test_validate_headers_invalid(self):
        """Test that the timeout validator raises an error for negative values."""
        self.load_manifest(filename="api-plugin.yaml")

        invalid_headers = [
            {
                "name": "Authorization",
                "wrong_key": "The authorization header.",
            },
        ]

        self._manifest["spec"]["apiData"]["headers"] = invalid_headers
        self._loader = None
        self._model = None
        with self.assertRaises(ValidationError) as context:
            # spec.apiData.headers.0.type
            #   Field required [type=missing, input_value={'name': 'Authorization', 'descri... of results to return.'}, input_type=dict]
            print(self.model)
        self.assertIn(
            "Field required [type=missing, input_value={'name': 'Authorization'",
            str(context.exception),
        )

    def test_validate_body_invalid(self):
        """Test that the timeout validator raises an error for negative values."""
        self.load_manifest(filename="api-plugin.yaml")

        invalid_body = "not valid json"

        self._manifest["spec"]["apiData"]["body"] = invalid_body
        self._loader = None
        self._model = None
        with self.assertRaises(ValidationError) as context:
            # spec.apiData.body.0.type
            #   Field required [type=missing, input_value={'name': 'Authorization', 'descri... of results to return.'}, input_type=dict]
            print(self.model)
        self.assertIn(
            "Input should be a valid dictionary",
            str(context.exception),
        )

    def test_django_orm(self):
        """Test that the Django model can be initialized from the Pydantic model."""
        self.load_manifest(filename="api-plugin.yaml")

        self.plugin_meta = PluginMeta(
            account=self.account,
            name=self.model.metadata.name,
            description=self.model.metadata.description,
            plugin_class=SAMPluginCommonMetadataClassValues.API.value,
            author=self.user_profile,
            version="1.0.0",
        )
        self.plugin_meta.save()

        model_dump = self.model.spec.apiData.model_dump()
        model_dump["connection"] = self.connection_django_model
        model_dump["plugin"] = self.plugin_meta
        model_dump["description"] = self.model.metadata.description
        model_dump = camel_to_snake_dict(model_dump)

        django_model = PluginDataApi(**model_dump)
        django_model.save()

        self.assertIsNotNone(django_model)
        self.assertIsInstance(django_model, PluginDataApi)

        self.assertEqual(django_model.plugin.account, self.account)
        self.assertEqual(django_model.plugin.name, self.model.metadata.name)
        self.assertEqual(django_model.plugin.description, self.model.metadata.description)
        self.assertEqual(django_model.plugin.plugin_class, SAMPluginCommonMetadataClassValues.API.value)

        self.assertEqual(django_model.connection, self.connection_django_model)
        self.assertEqual(django_model.endpoint, self.model.spec.apiData.endpoint)

        pydantic_url_params = [param.model_dump() for param in self.model.spec.apiData.url_params or []]
        django_url_params = django_model.url_params or []
        self.assertEqual(pydantic_url_params, django_url_params)

        pydantic_headers = [header.model_dump() for header in self.model.spec.apiData.headers or []]
        django_headers = django_model.headers or []
        self.assertEqual(pydantic_headers, django_headers)

        pydantic_body = self.model.spec.apiData.body or {}
        django_body = django_model.body or {}
        self.assertEqual(pydantic_body, django_body)

        pydantic_parameters = [param.model_dump() for param in self.model.spec.apiData.parameters or []]
        django_parameters = django_model.parameters or []
        self.assertEqual(pydantic_parameters, django_parameters)

        pydantic_test_values = [test_value.model_dump() for test_value in self.model.spec.apiData.test_values or []]
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
        django_model.endpoint = "/api/v1/tests/unauthenticated/list/"
        django_model.save()

        django_model.body = "definitely not valid json"
        with self.assertRaises(SmarterValueError) as context:
            django_model.save()
        self.assertIn(
            "body must be a dict or a list but got: <class 'str'>",
            str(context.exception),
        )

        django_model.headers = "this isn't even json, let alone a valid Pydantic model"
        with self.assertRaises(SmarterValueError) as context:
            django_model.save()
        self.assertIn(
            "headers must be a list of dictionaries but got: <class 'str'>",
            str(context.exception),
        )

        django_model.url_params = "this isn't even json, let alone a valid Pydantic model"
        with self.assertRaises(SmarterValueError) as context:
            django_model.save()
        self.assertIn(
            "url_params must be a list of dictionaries but got: <class 'str'>",
            str(context.exception),
        )

        # this should work
        django_model.body = None
        django_model.headers = None
        django_model.url_params = None
        django_model.test_values = None
        django_model.parameters = None
        django_model.save()

        try:
            django_model.delete()
        except (PluginDataApi.DoesNotExist, ValueError):
            pass
