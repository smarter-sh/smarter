"""
Test the plugin api, :mod:`smarter.apps.plugin.api.v1.views`, at /api/v1/plugins/, with an api key.

The tests create the plugin of tests/data/static-plugin.yaml, and delete it and its clones afterwards.
"""

import os
from http import HTTPStatus
from unittest.mock import patch

import yaml
from django.test import RequestFactory
from django.urls import reverse
from rest_framework.test import APIClient

from smarter.apps.api.v1.tests.base_class import ApiV1TestBase
from smarter.apps.plugin.api.v1 import views
from smarter.apps.plugin.models import PluginMeta
from smarter.common.exceptions import SmarterValueError
from smarter.lib import json

HERE = os.path.abspath(os.path.dirname(__file__))
MANIFEST = os.path.join(HERE, "..", "..", "..", "tests", "data", "static-plugin.yaml")
NAME = "test_plugin_app_static_plugin"
NAMESPACE = "api:v1:plugin:"


class TestPluginApi(ApiV1TestBase):
    """Create, list, get, clone and delete a plugin with the plugin api."""

    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_key}")
        self.addCleanup(PluginMeta.objects.filter(user_profile=self.user_profile, name__startswith=NAME).delete)
        with open(MANIFEST, encoding="utf-8") as f:
            self.manifest_text = f.read()
        self.manifest = yaml.safe_load(self.manifest_text)

    def url(self, name: str, **kwargs) -> str:
        return reverse(NAMESPACE + name, kwargs=kwargs)

    def create(self) -> PluginMeta:
        response = self.client.post(self.url("plugins_list_view"), data=self.manifest, format="json")
        self.assertEqual(response.status_code, HTTPStatus.FOUND, response.content[:500])
        return PluginMeta.objects.get(user_profile=self.user_profile, name=NAME)

    def test_create_and_list(self):
        plugin = self.create()
        response = self.client.get(self.url("plugins_list_view"))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertIn(plugin.name, json.dumps(response.json()))

    def test_upload(self):
        """Test that a yaml manifest is uploaded, and an invalid one is refused."""
        response = self.client.post(
            self.url("plugin_upload"), data=self.manifest_text, content_type="application/x-yaml"
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND, response.content[:500])
        self.assertTrue(PluginMeta.objects.filter(user_profile=self.user_profile, name=NAME).exists())
        response = self.client.put(
            self.url("plugin_upload"), data=self.manifest_text, content_type="application/x-yaml"
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_get(self):
        """Test that a plugin can be got only while the ALLOW_API_GET switch is on, and an unknown one is a 404."""
        plugin = self.create()
        with patch("smarter.lib.django.waffle.switch_is_active", return_value=True):
            response = self.client.get(self.url("plugin_view", plugin_id=plugin.id))
            self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:500])
            self.assertEqual(
                self.client.get(self.url("plugin_view", plugin_id=999999999)).status_code, HTTPStatus.NOT_FOUND
            )
        with patch("smarter.lib.django.waffle.switch_is_active", return_value=False):
            response = self.client.get(self.url("plugin_view", plugin_id=plugin.id))
        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_clone(self):
        plugin = self.create()
        response = self.client.post(self.url("plugin_clone_view", plugin_id=plugin.id, new_name=f"{NAME}_clone"))
        self.assertEqual(response.status_code, HTTPStatus.FOUND, response.content[:500])
        self.assertTrue(PluginMeta.objects.filter(user_profile=self.user_profile, name=f"{NAME}_clone").exists())

    def test_delete(self):
        plugin = self.create()
        response = self.client.delete(self.url("plugin_view", plugin_id=plugin.id))
        self.assertEqual(response.status_code, HTTPStatus.FOUND, response.content[:500])
        self.assertFalse(PluginMeta.objects.filter(pk=plugin.pk).exists())
        response = self.client.delete(self.url("plugin_view", plugin_id=999999999))
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_create_invalid(self):
        response = self.client.post(self.url("plugins_list_view"), data={"kind": "Plugin"}, format="json")
        self.assertEqual(response.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)

    def test_update(self):
        """Test that a plugin is updated with a PATCH, PUT or POST to its url."""
        plugin = self.create()
        url = self.url("plugin_view", plugin_id=plugin.id)
        self.manifest["metadata"]["description"] = "updated by patch"
        response = self.client.patch(url, data=self.manifest, format="json")
        self.assertEqual(response.status_code, HTTPStatus.FOUND, response.content[:500])
        self.assertEqual(PluginMeta.objects.get(pk=plugin.pk).description, "updated by patch")
        for method in (self.client.put, self.client.post):
            self.manifest["metadata"]["description"] = f"updated by {method.__name__}"
            response = method(url, data=self.manifest, format="json")
            self.assertEqual(response.status_code, HTTPStatus.FOUND, response.content[:500])
            self.assertEqual(PluginMeta.objects.get(pk=plugin.pk).description, f"updated by {method.__name__}")

    def test_update_invalid(self):
        """Test that an update of an unknown plugin, of another plugin's manifest, or of a non-dict body is refused."""
        plugin = self.create()
        response = self.client.patch(self.url("plugin_view", plugin_id=999999999), data=self.manifest, format="json")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        other = dict(self.manifest, metadata=dict(self.manifest["metadata"], name=f"{NAME}_other"))
        response = self.client.patch(self.url("plugin_view", plugin_id=plugin.id), data=other, format="json")
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        response = self.client.patch(self.url("plugin_view", plugin_id=plugin.id), data=[1, 2], format="json")
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_update_plugin_function(self):
        """Test update_plugin() itself, with a plain django request whose body it parses."""
        self.create()
        request = RequestFactory().patch(
            "/api/v1/plugins/", data=json.dumps(self.manifest), content_type="application/json"
        )
        request.user = self.admin_user
        response = views.update_plugin(request)
        self.assertEqual(response.status_code, HTTPStatus.FOUND, response.content)


class TestParseYamlFile(ApiV1TestBase):
    def test_parse_yaml_file(self):
        parse = views.PluginUploadView.parse_yaml_file
        self.assertEqual(parse({"a": 1}), {"a": 1})
        self.assertEqual(parse("a: 1"), {"a": 1})
        self.assertEqual(parse('{"a": 1}'), {"a": 1})
        with self.assertRaises(SmarterValueError):
            parse("a: [unclosed\\n  - {")
