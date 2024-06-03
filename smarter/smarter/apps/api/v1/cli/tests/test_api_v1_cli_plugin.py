# pylint: disable=wrong-import-position
"""Test api/v1/cli endpoints on the Plugin model."""

import os
from http import HTTPStatus

from django.urls import reverse

from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.api.v1.tests.base_class import ApiV1TestBase
from smarter.apps.plugin.models import PluginMeta
from smarter.common.api import SmarterApiVersions
from smarter.common.const import PYTHON_ROOT
from smarter.lib.manifest.enum import SAMKeys, SCLIResponseGet, SCLIResponseGetData


class TestApiV1CliPlugin(ApiV1TestBase):
    """Test api/v1/cli endpoints on the Plugin model."""

    def setUp(self):
        super().setUp()
        self.path = os.path.join(PYTHON_ROOT, "smarter/apps/api/v1/cli/tests/data")
        self.good_manifest_path = os.path.join(self.path, "good-plugin-manifest.yaml")
        with open(self.good_manifest_path, encoding="utf-8") as file:
            self.good_manifest_text = file.read()

    def test_valid_manifest(self):
        """Test that we get OK response when passing a valid manifest"""

        path = reverse("api_v1_cli_apply_view", kwargs={})
        response, status = self.get_response(path, manifest=self.good_manifest_text)

        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)
        self.assertEqual(response["message"], "Plugin CliTestPlugin applied successfully")

        path = f"{reverse('api_v1_cli_deploy_view', kwargs={'kind': 'plugin'})}?name={self.name}"
        response, status = self.get_response(path)
        self.assertEqual(status, HTTPStatus.NOT_IMPLEMENTED)
        self.assertEqual(
            response["error"]["description"], "Smarter API Plugin manifest broker: deploy() not implemented error"
        )

        path = f"{reverse('api_v1_cli_describe_view', kwargs={'kind': 'plugin'})}?name={self.name}"
        response, status = self.get_response(path)
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)

        data = response[SCLIResponseGet.DATA.value]
        self.assertEqual(data[SAMKeys.APIVERSION.value], SmarterApiVersions.V1.value)
        self.assertEqual(data[SAMKeys.KIND.value], SAMKinds.PLUGIN.value)
        self.assertIsInstance(data.get(SAMKeys.METADATA.value, None), dict)
        self.assertEqual(data.get(SAMKeys.METADATA.value, {}).get("name", None), self.name)

        path = f"{reverse('api_v1_cli_logs_kind_view', kwargs={'kind': 'plugin'})}?name={self.name}"
        response, status = self.get_response(path)
        self.assertEqual(status, HTTPStatus.NOT_IMPLEMENTED)
        self.assertEqual(
            response["error"]["description"], "Smarter API Plugin manifest broker: logs() not implemented error"
        )

        path = f"{reverse('api_v1_cli_get_view', kwargs={'kind': 'plugin'})}?name={self.name}"
        response, status = self.get_response(path)
        response = response["data"]
        self.assertIsInstance(response[SCLIResponseGet.DATA.value][SCLIResponseGetData.TITLES.value], list)
        self.assertIsInstance(response[SCLIResponseGet.DATA.value][SCLIResponseGetData.ITEMS.value], list)
        self.assertEqual(data[SAMKeys.KIND.value], SAMKinds.PLUGIN.value)
        self.assertEqual(data[SAMKeys.APIVERSION.value], SmarterApiVersions.V1.value)

        path = reverse("api_v1_cli_manifest_view", kwargs={SAMKeys.KIND.value: "plugin"})
        response, status = self.get_response(path)
        data = response[SCLIResponseGet.DATA.value]
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)
        self.assertEqual(data[SAMKeys.KIND.value], SAMKinds.PLUGIN.value)
        self.assertEqual(data[SAMKeys.APIVERSION.value], SmarterApiVersions.V1.value)

        path = f"{reverse('api_v1_cli_delete_view', kwargs={'kind': 'plugin'})}?name={self.name}"
        response, status = self.get_response(path)
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)
        self.assertEqual(response["message"], "Plugin CliTestPlugin deleted successfully")
        with self.assertRaises(PluginMeta.DoesNotExist):
            PluginMeta.objects.get(name=self.name, account=self.account)
