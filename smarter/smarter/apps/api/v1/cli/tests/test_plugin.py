# pylint: disable=wrong-import-position
"""Test api/v1/cli endpoints on the Plugin model."""

import logging
import os
from http import HTTPStatus
from urllib.parse import urlencode

from django.urls import reverse

from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.plugin.models import PluginMeta
from smarter.common.api import SmarterApiVersions
from smarter.lib.manifest.enum import SAMKeys, SCLIResponseGet, SCLIResponseGetData

from .base_class import ApiV1CliTestBase


KIND = SAMKinds.STATIC_PLUGIN.value
HERE = os.path.abspath(os.path.dirname(__file__))

logger = logging.getLogger(__name__)


class TestApiV1CliPlugin(ApiV1CliTestBase):
    """Test api/v1/cli endpoints on the Plugin model."""

    def setUp(self):
        super().setUp()
        self.path = os.path.join(HERE, "data")
        self.good_manifest_path = os.path.join(self.path, "good-plugin-manifest.yaml")
        self.good_manifest_text = self.get_readonly_yaml_file(self.good_manifest_path)
        self.kwargs = {SAMKeys.KIND.value: KIND}
        self.query_params = urlencode({"name": "cli_test_plugin"})

    def test_deploy(self):

        path = f"{reverse(self.namespace + ApiV1CliReverseViews.deploy, kwargs=self.kwargs)}"
        url_with_query_params = f"{path}?{self.query_params}"
        response, status = self.get_response(path=url_with_query_params)
        self.assertEqual(status, HTTPStatus.NOT_IMPLEMENTED)
        self.assertIn("not implemented", response["error"]["description"])

    def test_logs(self):
        path = f"{reverse(self.namespace + ApiV1CliReverseViews.logs, kwargs=self.kwargs)}"
        url_with_query_params = f"{path}?{self.query_params}"
        response, status = self.get_response(path=url_with_query_params)
        self.assertEqual(status, HTTPStatus.NOT_IMPLEMENTED)
        self.assertIn("not implemented", response["error"]["description"])

    def test_example_manifest(self):
        path = reverse(self.namespace + ApiV1CliReverseViews.manifest, kwargs=self.kwargs)
        response, status = self.get_response(path=path)
        data = response[SCLIResponseGet.DATA.value]
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)
        self.assertEqual(data[SAMKeys.KIND.value], SAMKinds.STATIC_PLUGIN.value)
        self.assertEqual(data[SAMKeys.APIVERSION.value], SmarterApiVersions.V1)

    def test_valid_manifest(self):
        """Test that we get OK response when passing a valid manifest"""

        # create a Plugin from a valid manifest
        path = reverse(self.namespace + ApiV1CliReverseViews.apply, kwargs=None)
        response, status = self.get_response(path, manifest=self.good_manifest_text)  # type: ignore[arg-type]

        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)
        self.assertIn("applied successfully", response["message"])

        # invoke the describe endpoint to verify that the Plugin was created
        path = f"{reverse(self.namespace + ApiV1CliReverseViews.describe, kwargs=self.kwargs)}"
        url_with_query_params = f"{path}?{self.query_params}"
        response, status = self.get_response(path=url_with_query_params)
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)

        logger.info("Response: %s", response)

        data = response
        self.assertEqual(data[SAMKeys.APIVERSION.value], SmarterApiVersions.V1)
        self.assertEqual(data[SAMKeys.KIND.value], SAMKinds.STATIC_PLUGIN.value)
        self.assertIsInstance(data.get(SAMKeys.METADATA.value, None), dict)
        self.assertEqual(data.get(SAMKeys.METADATA.value, {}).get("name", None), "cli_test_plugin")

        # we should also be able to get the Plugin by name
        path = f"{reverse(self.namespace + ApiV1CliReverseViews.get, kwargs=self.kwargs)}"
        url_with_query_params = f"{path}?{self.query_params}"
        response, status = self.get_response(path=path)
        response = response["data"]
        self.assertIsInstance(response[SCLIResponseGet.DATA.value][SCLIResponseGetData.TITLES.value], list)
        self.assertIsInstance(response[SCLIResponseGet.DATA.value][SCLIResponseGetData.ITEMS.value], list)
        self.assertEqual(data[SAMKeys.KIND.value], SAMKinds.STATIC_PLUGIN.value)
        self.assertEqual(data[SAMKeys.APIVERSION.value], SmarterApiVersions.V1)

        path = f"{reverse(self.namespace + ApiV1CliReverseViews.delete, kwargs=self.kwargs)}"
        url_with_query_params = f"{path}?{self.query_params}"
        response, status = self.get_response(path=url_with_query_params)
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)
        self.assertEqual(response["message"], "Plugin cli_test_plugin deleted successfully")
        with self.assertRaises(PluginMeta.DoesNotExist):
            PluginMeta.objects.get(name=self.name, account=self.account)
