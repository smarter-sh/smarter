# pylint: disable=wrong-import-position
"""Test api/v1/cli endpoints on the Plugin model."""

import os
from http import HTTPStatus
from urllib.parse import urlencode

from django.urls import reverse

from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.api.v1.tests.base_class import ApiV1TestBase
from smarter.apps.plugin.models import PluginMeta
from smarter.common.api import SmarterApiVersions
from smarter.common.const import PYTHON_ROOT
from smarter.lib.manifest.enum import SAMKeys, SCLIResponseGet, SCLIResponseGetData


KIND = SAMKinds.PLUGIN.value


class TestApiV1CliPlugin(ApiV1TestBase):
    """Test api/v1/cli endpoints on the Plugin model."""

    def setUp(self):
        super().setUp()
        self.path = os.path.join(PYTHON_ROOT, "smarter/apps/api/v1/cli/tests/data")
        self.good_manifest_path = os.path.join(self.path, "good-plugin-manifest.yaml")
        with open(self.good_manifest_path, encoding="utf-8") as file:
            self.good_manifest_text = file.read()
        self.kwargs = {SAMKeys.KIND.value: KIND}
        self.name = "CliTestPlugin"
        self.query_params = urlencode({"name": self.name})

    def test_deploy(self):

        path = f"{reverse(ApiV1CliReverseViews.deploy, kwargs=self.kwargs)}"
        url_with_query_params = f"{path}?{self.query_params}"
        response, status = self.get_response(path=url_with_query_params)
        self.assertEqual(status, HTTPStatus.NOT_IMPLEMENTED)
        self.assertEqual(
            response["error"]["description"],
            "Smarter API Plugin manifest broker: deploy() not implemented error.  deploy() not implemented",
        )

    def test_logs(self):
        path = f"{reverse(ApiV1CliReverseViews.logs, kwargs=self.kwargs)}"
        url_with_query_params = f"{path}?{self.query_params}"
        response, status = self.get_response(path=url_with_query_params)
        self.assertEqual(status, HTTPStatus.NOT_IMPLEMENTED)
        self.assertEqual(
            response["error"]["description"],
            "Smarter API Plugin manifest broker: logs() not implemented error.  logs() not implemented",
        )

    def test_example_manifest(self):
        path = reverse(ApiV1CliReverseViews.manifest, kwargs=self.kwargs)
        response, status = self.get_response(path=path)
        data = response[SCLIResponseGet.DATA.value]
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)
        self.assertEqual(data[SAMKeys.KIND.value], SAMKinds.PLUGIN.value)
        self.assertEqual(data[SAMKeys.APIVERSION.value], SmarterApiVersions.V1)

    def test_valid_manifest(self):
        """Test that we get OK response when passing a valid manifest"""

        # create a Plugin from a valid manifest
        path = reverse(ApiV1CliReverseViews.apply, kwargs=None)
        print("manifest:\n", self.good_manifest_text)
        response, status = self.get_response(path, manifest=self.good_manifest_text)

        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)
        self.assertEqual(response["message"], "Plugin CliTestPlugin applied successfully")

        # invoke the describe endpoint to verify that the Plugin was created
        path = f"{reverse(ApiV1CliReverseViews.describe, kwargs=self.kwargs)}"
        url_with_query_params = f"{path}?{self.query_params}"
        response, status = self.get_response(path=url_with_query_params)
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)

        data = response[SCLIResponseGet.DATA.value]
        self.assertEqual(data[SAMKeys.APIVERSION.value], SmarterApiVersions.V1)
        self.assertEqual(data[SAMKeys.KIND.value], SAMKinds.PLUGIN.value)
        self.assertIsInstance(data.get(SAMKeys.METADATA.value, None), dict)
        self.assertEqual(data.get(SAMKeys.METADATA.value, {}).get("name", None), self.name)

        # we should also be able to get the Plugin by name
        path = f"{reverse(ApiV1CliReverseViews.get, kwargs=self.kwargs)}"
        url_with_query_params = f"{path}?{self.query_params}"
        response, status = self.get_response(path=path)
        print("response:\n", response)
        response = response["data"]
        self.assertIsInstance(response[SCLIResponseGet.DATA.value][SCLIResponseGetData.TITLES.value], list)
        self.assertIsInstance(response[SCLIResponseGet.DATA.value][SCLIResponseGetData.ITEMS.value], list)
        self.assertEqual(data[SAMKeys.KIND.value], SAMKinds.PLUGIN.value)
        self.assertEqual(data[SAMKeys.APIVERSION.value], SmarterApiVersions.V1)

        path = f"{reverse(ApiV1CliReverseViews.delete, kwargs=self.kwargs)}"
        url_with_query_params = f"{path}?{self.query_params}"
        response, status = self.get_response(path=url_with_query_params)
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)
        self.assertEqual(response["message"], "Plugin CliTestPlugin deleted successfully")
        with self.assertRaises(PluginMeta.DoesNotExist):
            PluginMeta.objects.get(name=self.name, account=self.account)
