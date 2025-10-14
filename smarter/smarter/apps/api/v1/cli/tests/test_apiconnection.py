"""Test Api v1 CLI commands for ApiConnection"""

import logging
from http import HTTPStatus
from typing import Optional
from urllib.parse import urlencode

import yaml
from django.urls import reverse

from smarter.apps.account.models import Secret
from smarter.apps.account.tests.factories import secret_factory
from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.plugin.manifest.enum import (
    SAMApiConnectionSpecConnectionKeys,
    SAMApiConnectionSpecKeys,
)
from smarter.apps.plugin.models import ApiConnection
from smarter.common.api import SmarterApiVersions
from smarter.common.conf import settings as smarter_settings
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.journal.enum import SmarterJournalApiResponseKeys
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.manifest.enum import SAMKeys, SAMMetadataKeys

from .base_class import ApiV1CliTestBase


KIND = SAMKinds.API_CONNECTION.value


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return (
        waffle.switch_is_active(SmarterWaffleSwitches.API_LOGGING)
        and waffle.switch_is_active(SmarterWaffleSwitches.PLUGIN_LOGGING)
        and level >= smarter_settings.log_level
    )


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class TestApiCliV1ApiConnection(ApiV1CliTestBase):
    """
    Test Api v1 CLI commands for ApiConnection

    This class is a subclass of ApiV1TestBase, which gives us access to the
    setUpClass and tearDownClass methods, which are used to uniformly
    create and delete a user, account, user_profile and token record for
    testing purposes. ApiV1CliTestBase gives us access to the abstract methods
    that we need to implement in order to test the Api v1 CLI commands for
    Account.
    """

    apiconnection: Optional[ApiConnection] = None

    def setUp(self):
        super().setUp()
        self.kwargs = {SAMKeys.KIND.value: KIND}
        self.query_params = urlencode({"name": self.name})
        self.api_key: Optional[Secret] = None

    def tearDown(self):
        if self.apiconnection is not None:
            try:
                self.apiconnection.delete()
            except ApiConnection.DoesNotExist:
                pass
        if self.api_key is not None:
            try:
                self.api_key.delete()
            except Secret.DoesNotExist:
                pass
        super().tearDown()

    def apiconnection_factory(self):
        self.api_key = secret_factory(
            user_profile=self.user_profile,
            name=self.name,
            description="test password",
            value="test",
        )
        apiconnection = ApiConnection.objects.create(
            account=self.account,
            name=self.name,
            kind=KIND,
            description="test apiconnection",
            base_url="http://localhost:8000/api/v1/cli/example_manifest/plugin/",
            api_key=self.api_key,
            auth_method=ApiConnection.AUTH_METHOD_CHOICES[1][0],
            timeout=30,
            proxy_protocol=ApiConnection.PROXY_PROTOCOL_CHOICES[0][0],
            proxy_host=None,
            proxy_port=None,
            proxy_username=None,
            proxy_password=None,
        )
        return apiconnection

    def validate_response(self, response: dict) -> None:
        # validate the response and status are both good
        self.assertIsInstance(response, dict)

        # validate the structure of the response
        self.assertIn(SmarterJournalApiResponseKeys.DATA, response.keys())
        data = response[SmarterJournalApiResponseKeys.DATA]
        self.assertEqual(data[SAMKeys.APIVERSION.value], SmarterApiVersions.V1)
        self.assertEqual(data[SAMKeys.KIND.value], SAMKinds.API_CONNECTION.value)

        # validate the metadata
        self.assertIn(SmarterJournalApiResponseKeys.METADATA, data.keys())
        metadata = data[SAMKeys.METADATA.value]
        self.assertIn(SAMMetadataKeys.NAME.value, metadata.keys())
        self.assertIn(SAMMetadataKeys.DESCRIPTION.value, metadata.keys())
        self.assertIn(SAMMetadataKeys.VERSION.value, metadata.keys())

    def validate_spec(self, data: dict) -> None:
        self.assertIn(SAMKeys.SPEC.value, data.keys())
        spec = data[SAMKeys.SPEC.value]
        connection = spec["connection"]
        config_fields = [
            "baseUrl",
            "apiKey",
            "authMethod",
            "timeout",
            "proxyProtocol",
            "proxyHost",
            "proxyPort",
            "proxyUsername",
            "proxyPassword",
        ]
        for field in config_fields:
            assert field in connection.keys(), f"{field} not found in config keys: {connection.keys()}"

    def test_example_manifest(self) -> None:
        """Test example-manifest command"""

        path = reverse(self.namespace + ApiV1CliReverseViews.example_manifest, kwargs=self.kwargs)
        response, status = self.get_response(path=path)
        self.assertEqual(status, HTTPStatus.OK)
        self.validate_response(response)
        data = response[SmarterJournalApiResponseKeys.DATA]
        self.validate_spec(data)

    def test_describe(self) -> None:
        """Test describe command"""
        self.apiconnection = self.apiconnection_factory()

        path = reverse(self.namespace + ApiV1CliReverseViews.describe, kwargs=self.kwargs)
        url_with_query_params = f"{path}?{self.query_params}"
        response, status = self.get_response(path=url_with_query_params)

        self.assertEqual(status, HTTPStatus.OK)
        self.validate_response(response)

        data = response[SmarterJournalApiResponseKeys.DATA]
        self.validate_spec(data)

        # verify the data matches the apiconnection
        self.assertEqual(data[SAMKeys.METADATA.value][SAMMetadataKeys.NAME.value], self.apiconnection.name)
        self.assertEqual(
            data[SAMKeys.METADATA.value][SAMMetadataKeys.DESCRIPTION.value], self.apiconnection.description
        )
        self.assertEqual(data[SAMKeys.METADATA.value][SAMMetadataKeys.VERSION.value], self.apiconnection.version)

    def test_apply(self) -> None:
        """Test apply command"""

        self.apiconnection = self.apiconnection_factory()

        # retrieve the current manifest by calling 'describe'
        path = reverse(self.namespace + ApiV1CliReverseViews.describe, kwargs=self.kwargs)
        url_with_query_params = f"{path}?{self.query_params}"
        response, status = self.get_response(path=url_with_query_params)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)

        # muck up the manifest with some test data
        new_url = "http://localhost:8000/api/v1/cli/example_manifest/chatbot/"
        new_description = "new description"
        data = response[SmarterJournalApiResponseKeys.DATA]
        data[SAMKeys.SPEC.value][SAMApiConnectionSpecKeys.CONNECTION.value][
            SAMApiConnectionSpecConnectionKeys.BASE_URL.value
        ] = new_url
        data[SAMKeys.METADATA.value]["description"] = new_description

        # pop the status bc its read-only
        # data.pop(SAMKeys.STATUS.value)

        # convert the data back to yaml, since this is what the cli usually sends
        manifest = yaml.dump(data)
        logger.info("Modified manifest:\n%s", manifest)
        path = reverse(self.namespace + ApiV1CliReverseViews.apply)
        response, status = self.get_response(path=path, manifest=manifest)
        self.assertEqual(status, HTTPStatus.OK)

        self.assertIsInstance(response, dict)

        # requery and validate our changes
        path = reverse(self.namespace + ApiV1CliReverseViews.describe, kwargs=self.kwargs)
        url_with_query_params = f"{path}?{self.query_params}"
        response, status = self.get_response(path=url_with_query_params)
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)

        # validate our changes
        data = response[SmarterJournalApiResponseKeys.DATA]
        self.assertEqual(data[SAMKeys.METADATA.value]["description"], new_description)
        self.assertEqual(data[SAMKeys.SPEC.value]["connection"]["baseUrl"], new_url)

    def test_get(self) -> None:
        """Test get command"""

        # create a apiconnection so that we have something to get.
        self.apiconnection = self.apiconnection_factory()

        def validate_titles(data):
            if "titles" not in data:
                return False

            for item in data["titles"]:
                if not isinstance(item, dict):
                    return False
                if "name" not in item or "type" not in item:
                    return False

            return True

        def validate_items(data):
            if "items" not in data or "titles" not in data:
                raise ValueError("items not found in data")

            if "titles" not in data:
                raise ValueError("titles not found in data")

            title_names = {title["name"] for title in data["titles"]}

            for item in data["items"]:
                if not isinstance(item, dict):
                    raise ValueError(f"item is not a dict: {item}")
                if set(item.keys()) != title_names:
                    difference = list(set(item.keys()).symmetric_difference(title_names))
                    raise ValueError(f"item keys do not match titles: {difference}")

            return True

        path = reverse(self.namespace + ApiV1CliReverseViews.get, kwargs=self.kwargs)
        response, status = self.get_response(path=path)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)

        self.assertIn(SmarterJournalApiResponseKeys.DATA, response.keys())
        data = response[SmarterJournalApiResponseKeys.DATA]
        self.assertEqual(data[SAMKeys.APIVERSION.value], SmarterApiVersions.V1)
        self.assertEqual(data[SAMKeys.KIND.value], SAMKinds.API_CONNECTION.value)

        # validate the metadata
        self.assertIn(SmarterJournalApiResponseKeys.METADATA, data.keys())
        metadata = data[SAMKeys.METADATA.value]
        self.assertIn("count", metadata.keys())
        self.assertEqual(metadata["count"], 1)

        # validate the response data dict, that it has both titles and items
        self.assertIn("data", data.keys())
        data = data["data"]
        self.assertIn("titles", data.keys())
        self.assertIn("items", data.keys())

        if not validate_titles(data):
            self.fail(f"Titles are not valid: {data}")

        if not validate_items(data):
            self.fail(f"Items are not valid: {data}")

    def test_deploy(self) -> None:
        """Test deploy command"""
        # create a apiconnection so that we have something to deploy
        self.apiconnection = self.apiconnection_factory()

        path = reverse(self.namespace + ApiV1CliReverseViews.deploy, kwargs=self.kwargs)
        url_with_query_params = f"{path}?{self.query_params}"
        _, status = self.get_response(path=url_with_query_params)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.NOT_IMPLEMENTED)

    def test_undeploy(self) -> None:
        """Test undeploy command"""

        # create a apiconnection so that we have something to undeploy
        self.apiconnection = self.apiconnection_factory()

        path = reverse(self.namespace + ApiV1CliReverseViews.undeploy, kwargs=self.kwargs)
        url_with_query_params = f"{path}?{self.query_params}"
        _, status = self.get_response(path=url_with_query_params)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.NOT_IMPLEMENTED)

    def test_logs(self) -> None:
        """Test logs command"""
        path = reverse(self.namespace + ApiV1CliReverseViews.logs, kwargs=self.kwargs)
        url_with_query_params = f"{path}?{self.query_params}"
        _, status = self.get_response(path=url_with_query_params)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.NOT_IMPLEMENTED)

    def test_delete(self) -> None:
        """Test delete command"""
        # create a apiconnection so that we have something to delete
        self.apiconnection = self.apiconnection_factory()

        path = reverse(self.namespace + ApiV1CliReverseViews.delete, kwargs=self.kwargs)
        url_with_query_params = f"{path}?{self.query_params}"
        _, status = self.get_response(path=url_with_query_params)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.OK)

        # verify the apiconnection was deleted
        try:
            ApiConnection.objects.get(name=self.name)
            self.fail("ApiConnection was not deleted")
        except ApiConnection.DoesNotExist:
            pass
