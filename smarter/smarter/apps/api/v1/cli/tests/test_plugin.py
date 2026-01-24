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

        logger.info("describe() - raw response: %s", response)

        expected = {
            "data": {
                "apiVersion": "smarter.sh/v1",
                "kind": "Plugin",
                "metadata": {
                    "name": "cli_test_plugin",
                    "description": "A 'hello world' style plugin. This is an example plugin to integrate with OpenAI API Function Calling additional information plugin_data, in this module.",
                    "version": "0.2.0",
                    "tags": ["down", "up", "all-around"],
                    "annotations": [
                        {"smarter.sh/tests/owner": "test bank"},
                        {"smarter.sh/tests/host": "sql.lawrencemcdaniel.com"},
                        {
                            "smarter.sh/tests/purpose": "Provide information about Stackademy University courses using SQL queries."
                        },
                        {"smarter.sh/tests/last-updated": "2025-12-31"},
                        {"smarter.sh/tests/documentation": "https://docs.tests.edu/sql-chatbot"},
                        {
                            "smarter.sh/tests/connection-info": "This chatbot connects to the Stackademy SQL database hosted at sql.lawrencemcdaniel.com using the Stackademy SQL plugin to retrieve course information.\n"
                        },
                    ],
                    "pluginClass": "static",
                },
                "spec": {
                    "selector": {
                        "directive": "search_terms",
                        "searchTerms": ["Cli Test", "cli test plugin", "test plugin"],
                    },
                    "prompt": {
                        "provider": "openai",
                        "systemRole": 'Your job is to provide helpful technical information about the OpenAI API Function Calling feature. You should include the following information in your response: "Congratulations!!! OpenAI API Function Calling chose to call this plugin_data. Here is the additional information that you requested:"\n',
                        "model": "gpt-4o-mini",
                        "temperature": 0.5,
                        "maxTokens": 256,
                    },
                    "data": {
                        "staticData": {
                            "about": "In an API call, you can describe functions and have the model intelligently choose to output a JSON object containing arguments to call one or many functions. The Chat Completions API does not call the plugin_data; instead, the model generates JSON that you can use to call the plugin_data in your code. The latest models (gpt-4o et al) have been trained to both detect when a plugin_data should to be called (depending on the input) and to respond with JSON that adheres to the plugin_data signature more closely than previous models. With this capability also comes potential risks. We strongly recommend building in user confirmation flows before taking actions that impact the world on behalf of users (sending an email, posting something online, making a purchase, etc).\n",
                            "links": [
                                {"documentation": "https://platform.openai.com/docs/guides/function-calling"},
                                {"website": "https://openai.com/"},
                                {"wikipedia": "https://en.wikipedia.org/wiki/OpenAI"},
                            ],
                            "platformProvider": "OpenAI",
                        }
                    },
                },
            },
            "message": "Plugin cli_test_plugin described successfully",
            "api": "smarter.sh/v1",
            "thing": "Plugin",
            "metadata": {"key": "78456bd8a768b609fb176442dcac58c4daa41b78cbeb4e901eedde3d07b903a9"},
        }

        data = response["data"]

        self.assertEqual(data[SAMKeys.APIVERSION.value], SmarterApiVersions.V1)
        self.assertEqual(data[SAMKeys.KIND.value], SAMKinds.STATIC_PLUGIN.value)
        self.assertIsInstance(data.get(SAMKeys.METADATA.value, None), dict)
        self.assertEqual(data.get(SAMKeys.METADATA.value, {}).get("name", None), "cli_test_plugin")

        # we should also be able to get the Plugin by name
        path = f"{reverse(self.namespace + ApiV1CliReverseViews.get, kwargs=self.kwargs)}"
        url_with_query_params = f"{path}?{self.query_params}"
        response, status = self.get_response(path=path)
        logger.debug("get() raw response: %s", response)

        expected = {
            "data": {
                "apiVersion": "smarter.sh/v1",
                "kind": "Plugin",
                "name": None,
                "metadata": {"count": 1},
                "kwargs": {"kwargs": {}},
                "data": {
                    "titles": [
                        {"name": "name", "type": "CharField"},
                        {"name": "pluginClass", "type": "ChoiceField"},
                        {"name": "version", "type": "CharField"},
                        {"name": "email", "type": "SerializerMethodField"},
                        {"name": "createdAt", "type": "DateTimeField"},
                        {"name": "updatedAt", "type": "DateTimeField"},
                    ],
                    "items": [
                        {
                            "name": "cli_test_plugin",
                            "pluginClass": "static",
                            "version": "0.2.0",
                            "email": "test-admin-1ccabee51d440caa@mail.com",
                            "createdAt": "2026-01-07T20:53:50.712494Z",
                            "updatedAt": "2026-01-07T20:53:50.712540Z",
                        }
                    ],
                },
            },
            "message": "Plugins got successfully",
            "api": "smarter.sh/v1",
            "thing": "Plugin",
            "metadata": {"key": "1a65b57ec3a3a81039e4973bc3f91638fc18db8ea50213d7f3cc9dba57137faa"},
        }

        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)
        data = response["data"]
        self.assertIsInstance(data[SCLIResponseGet.DATA.value], dict)

        self.assertIsInstance(data[SCLIResponseGet.DATA.value][SCLIResponseGetData.TITLES.value], list)
        self.assertIsInstance(data[SCLIResponseGet.DATA.value][SCLIResponseGetData.ITEMS.value], list)
        self.assertEqual(data[SAMKeys.KIND.value], SAMKinds.STATIC_PLUGIN.value)
        self.assertEqual(data[SAMKeys.APIVERSION.value], SmarterApiVersions.V1)

        path = f"{reverse(self.namespace + ApiV1CliReverseViews.delete, kwargs=self.kwargs)}"
        url_with_query_params = f"{path}?{self.query_params}"
        response, status = self.get_response(path=url_with_query_params)
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)
        self.assertEqual(response["message"], "Plugin cli_test_plugin deleted successfully")
        with self.assertRaises(PluginMeta.DoesNotExist):
            PluginMeta.objects.get(name=self.name, user_profile__account=self.account)
