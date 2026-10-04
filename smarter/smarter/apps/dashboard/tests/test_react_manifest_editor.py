"""Test :mod:`smarter.apps.dashboard.templatetags.react_manifest_editor`."""

import json
import os
from http import HTTPStatus

import yaml
from django.template import Context, Template
from django.test import Client
from django.utils.crypto import get_random_string

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.dashboard.templatetags import react_manifest_editor
from smarter.apps.guardrail.models import Guardrail
from smarter.lib.unittest.base_classes import SmarterTestBase

GUARDRAIL_MANIFEST = os.path.join(
    os.path.dirname(__file__), "..", "..", "guardrail", "manifest", "brokers", "tests", "data", "guardrail.yaml"
)


class TestReactManifestEditorTemplateTag(SmarterTestBase):
    """Test the React manifest-editor template tags."""

    def test_assets(self):
        """Test that the assets tag returns the app's JS and CSS assets, in a template."""
        self.assertEqual(react_manifest_editor.templatetag_manager.app_name, "@smarter/manifest-editor")
        assets = react_manifest_editor.manifest_editor_react_assets()
        self.assertEqual(set(assets.keys()), {"js", "css"})
        template = Template(
            "{% load react_manifest_editor %}{% manifest_editor_react_assets as assets %}{{ assets.js|length }}"
        )
        self.assertEqual(template.render(Context({})), str(len(assets["js"])))

    def test_context(self):
        """Test that the context tag returns the root element's settings, and the cli api urls."""
        context = react_manifest_editor.manifest_editor_context()
        self.assertEqual(context["root_id"], "smarter-manifest-editor-root")
        self.assertEqual(context["data_id"], "smarter-manifest-editor-data")
        self.assertEqual(context["apply_api_url"], "/api/v1/cli/apply/")
        self.assertEqual(context["validate_api_url"], "/api/v1/cli/validate/")
        self.assertEqual(context["delete_api_url"], f"/api/v1/cli/delete/{react_manifest_editor.KIND_PLACEHOLDER}/")
        self.assertEqual(context["kind_placeholder"], react_manifest_editor.KIND_PLACEHOLDER)
        self.assertEqual(len(context["smarter_request_id"]), 32)
        self.assertNotEqual(
            context["smarter_request_id"], react_manifest_editor.manifest_editor_context()["smarter_request_id"]
        )

    def test_context_in_template(self):
        """Test that the context tag renders in a template."""
        template = Template(
            "{% load react_manifest_editor %}{% manifest_editor_context as editor %}{{ editor.apply_api_url }}"
        )
        self.assertEqual(template.render(Context({})), "/api/v1/cli/apply/")


class TestManifestEditorCliApi(TestAccountMixin):
    """
    Test the cli api calls of the manifest editor, as a browser makes them: with the.

    user's Django session, and its CSRF cookie and header.
    """

    def setUp(self):
        super().setUp()
        self.name = f"test_manifest_editor_{get_random_string(8).lower()}"
        self.addCleanup(Guardrail.objects.filter(user_profile=self.user_profile, name=self.name).delete)
        self.client = Client(enforce_csrf_checks=True)
        self.client.force_login(self.admin_user)
        self.addCleanup(self.client.logout)
        self.csrf_token = get_random_string(32)
        self.client.cookies["csrftoken"] = self.csrf_token
        self.context = react_manifest_editor.manifest_editor_context()

    def post(self, url: str, data: dict, csrf: bool = True):
        headers = {"HTTP_X_CSRFTOKEN": self.csrf_token} if csrf else {}
        return self.client.post(url, data=json.dumps(data), content_type="application/json", **headers)

    def manifest(self) -> dict:
        with open(GUARDRAIL_MANIFEST, encoding="utf-8") as f:
            manifest = yaml.safe_load(f)
        manifest["metadata"]["name"] = self.name
        return manifest

    def test_save_and_delete(self):
        """Test that the editor's apply and delete urls save and delete a manifest's resource."""
        response = self.post(self.context["apply_api_url"], self.manifest())
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content)
        self.assertTrue(Guardrail.objects.filter(user_profile=self.user_profile, name=self.name).exists())

        delete_url = self.context["delete_api_url"].replace(self.context["kind_placeholder"], "Guardrail")
        response = self.post(f"{delete_url}?name={self.name}", {})
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content)
        self.assertFalse(Guardrail.objects.filter(user_profile=self.user_profile, name=self.name).exists())

    def test_csrf_required(self):
        """Test that the cli api refuses a session request without the CSRF header."""
        response = self.post(self.context["apply_api_url"], self.manifest(), csrf=False)
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN, response.content)
        self.assertFalse(Guardrail.objects.filter(user_profile=self.user_profile, name=self.name).exists())
