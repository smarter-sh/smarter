"""
Tests of smarter.apps.llmtool.extension.api.v1: the Extensions REST api under ``/api/v1/extensions/``.

The handlers that carry out each request are the web console's, which ``test_views`` covers in depth. These
tests cover the REST transport: api keys, GET reads with query parameters, JSON and multipart actions,
``{"detail": ...}`` errors, and what a user who is not a superuser may see and do. Every response, including
each error, is validated against the Smarter api's OpenAPI document.
"""

import re
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from smarter.apps.api.v1.contract.tests.mixins import OpenApiResponseMixin
from smarter.apps.api.v1.tests.base_class import ApiV1TestBase
from smarter.apps.llmtool.extension import views
from smarter.apps.llmtool.extension.api.v1.urls import (
    ExtensionApiV1ReverseViews as Names,
)
from smarter.apps.llmtool.models import Extension
from smarter.lib.django.shortcuts import reverse

from .mixins import ExtensionTestMixin, fixture_archive
from .test_registry import RegistryTestMixin

BASE = "/api/v1/extensions/"
FIXED_PATHS = ("registry/", "check-updates/", "install/", "upload/")


def template(path: str) -> str:
    """
    The OpenAPI document's path of a request's path, e.g. ``/extensions/{slug}/enable/`` for ``echo/enable/``.

    :param path: The path, relative to :data:`BASE`.
    :returns: The document's path.
    """
    if path == "" or path in FIXED_PATHS:
        return "/extensions/" + path
    return "/extensions/" + re.sub(r"^[a-z0-9-]+/", "{slug}/", path)


class ApiKeyClientMixin(OpenApiResponseMixin):
    """
    REST clients: the superuser's, with an api key, and that of the user who is not staff, with a session.

    Only staff users may have api keys, so the other user's client logs in instead, as the console's does.
    """

    def setUp(self):
        super().setUp()  # type: ignore[misc]
        self.client = self.api_client(self.token_key)  # type: ignore[attr-defined]
        self.mortal = APIClient()
        self.mortal.force_login(self.non_admin_user)  # type: ignore[attr-defined]
        self.addCleanup(self.mortal.logout)  # type: ignore[attr-defined]

    @staticmethod
    def api_client(key: str) -> APIClient:
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {key}")
        return client

    def call(self, method: str, path: str, body=None, client=None, expect: int = 200, request_format="json") -> dict:
        """Call the api, check the status, and return the response's JSON."""
        client = client or self.client
        if method == "get":
            response = client.get(BASE + path, data=body)
        else:
            response = client.post(BASE + path, data=body or {}, format=request_format)
        self.assertEqual(response.status_code, expect, response.content[:500])  # type: ignore[attr-defined]
        self.assertValidResponse(template(path), method, response.json(), expect)
        return response.json()


class TestExtensionApiV1(ApiKeyClientMixin, ApiV1TestBase, ExtensionTestMixin):
    """Test the installed extensions' reads and actions, with api keys."""

    def test_paths(self):
        """The api is under /api/v1/extensions/."""
        self.assertEqual(reverse(Names.namespace, Names.list_view), BASE)
        self.assertEqual(reverse(f"{Names.namespace}:{Names.enable}", kwargs={"slug": "echo"}), BASE + "echo/enable/")

    def test_anonymous(self):
        """A request without an api key is refused."""
        response = APIClient().get(BASE)
        self.assertIn(response.status_code, (401, 403))

    def test_reads_are_get_and_actions_are_post(self):
        """A read refuses POST, and an action refuses GET."""
        self.install_echo()
        self.assertEqual(self.client.post(BASE).status_code, 405)
        self.assertEqual(self.client.get(BASE + "echo/enable/").status_code, 405)

    def test_list_and_detail(self):
        """The list and the detail are the console's, by GET."""
        self.install_echo()
        data = self.call("get", "")
        self.assertIn("echo", [item["slug"] for item in data["objects"]])
        self.assertIn("registryEnabled", data)
        detail = self.call("get", "echo/")["extension"]
        self.assertIn("ext_echo_echo", [tool["functionName"] for tool in detail["tools"]])
        self.assertEqual(detail["missingSettings"], ["api_key"])
        self.assertIn("nope", self.call("get", "nope/", expect=404)["detail"])

    def test_configure_enable_disable(self):
        """Settings are saved with a JSON body, and the extension is enabled and disabled."""
        self.install_echo()
        self.assertIn("api_key", self.call("post", "echo/enable/", expect=400)["detail"])
        secret = self.secret(f"echo_api_v1_key_{self.hash_suffix}")
        data = self.call(
            "post", "echo/configure/", {"values": {"repeat": 2}, "secrets": {"api_key": {"secretId": secret.pk}}}
        )
        settings = {setting["name"]: setting for setting in data["extension"]["settings"]}
        self.assertEqual(settings["repeat"]["value"], 2)
        self.assertTrue(settings["api_key"]["isSet"])
        self.assertTrue(self.call("post", "echo/enable/")["extension"]["enabled"])
        self.assertFalse(self.call("post", "echo/disable/")["extension"]["enabled"])
        self.assertIn("not valid", self.call("post", "echo/configure/", {"unknown": 1}, expect=400)["detail"])

    def test_availability_rollback_uninstall(self):
        """An extension's availability, version and installation are changed."""
        self.install_echo()
        old = Extension.objects.get(slug="echo").installed_version
        self.installer.install(fixture_archive("echo", version="1.1.0"))
        data = self.call("post", "echo/availability/", {"allAccounts": False, "accountIds": [self.account.pk]})
        self.assertFalse(data["extension"]["allAccounts"])
        data = self.call("post", "echo/rollback/", {"versionId": old.pk})  # type: ignore[union-attr]
        self.assertEqual(data["extension"]["installedVersion"], "1.0.0")
        self.assertIsNone(self.call("post", "echo/uninstall/")["extension"])
        self.assertFalse(Extension.objects.filter(slug="echo").exists())

    def test_upload(self):
        """An archive is installed from a multipart upload; a missing one is a 400."""
        upload = SimpleUploadedFile("echo-1.0.0.zip", fixture_archive("echo"), content_type="application/zip")
        data = self.call("post", "upload/", {"archive": upload}, request_format="multipart")
        self.assertEqual(data["extension"]["slug"], "echo")
        self.assertIn("Choose", self.call("post", "upload/", {}, request_format="multipart", expect=400)["detail"])

    def test_unexpected_errors(self):
        """An unexpected exception, e.g. in a lifecycle hook, is a 500 with its message."""
        self.install_echo()
        with patch.object(views.ExtensionInstaller, "disable", side_effect=RuntimeError("boom")):
            self.assertIn("RuntimeError: boom", self.call("post", "echo/disable/", expect=500)["detail"])


class TestExtensionApiV1ReadOnly(ApiKeyClientMixin, ApiV1TestBase, ExtensionTestMixin):
    """Test what a user who is not a superuser may see and do, with their api key."""

    def test_reads(self):
        """The user sees the extensions that their account may use, without their settings."""
        extension = self.install_echo()
        self.assertIn("echo", [item["slug"] for item in self.call("get", "", client=self.mortal)["objects"]])
        detail = self.call("get", "echo/", client=self.mortal)["extension"]
        self.assertEqual((detail["settings"], detail["accounts"], detail["availableSecrets"]), ([], [], []))
        extension.all_accounts = False
        extension.save()
        self.assertNotIn("echo", [item["slug"] for item in self.call("get", "", client=self.mortal)["objects"]])
        self.call("get", "echo/", client=self.mortal, expect=404)

    def test_actions_are_forbidden(self):
        """Every action is for superusers only."""
        self.install_echo()
        for path in ("echo/enable/", "echo/uninstall/", "check-updates/", "install/"):
            with self.subTest(path=path):
                self.assertIn("superusers", self.call("post", path, client=self.mortal, expect=403)["detail"])
        self.assertTrue(Extension.objects.filter(slug="echo").exists())


class TestExtensionRegistryApiV1(ApiKeyClientMixin, ApiV1TestBase, RegistryTestMixin):
    """Test the registry's read and the registry's actions, against a signed index served by a patched transport."""

    def test_registry(self):
        """The registry's extensions are listed, and refreshed with ?refresh=true."""
        with patch.object(views.registry, "refresh_index", wraps=views.registry.refresh_index) as refresh_index:
            data = self.call("get", "registry/", {"refresh": "true"})
        refresh_index.assert_called_once()
        self.assertTrue(data["enabled"])
        self.assertEqual(data["objects"][0]["slug"], "echo")
        self.assertEqual(data["objects"][0]["action"], "install")
        self.assertIn("not valid", self.call("get", "registry/", {"refresh": "maybe"}, expect=400)["detail"])

    def test_registry_read_only(self):
        """A user who is not a superuser reads the registry, but can't refresh it."""
        with patch.object(views.registry, "refresh_index") as refresh_index:
            data = self.call("get", "registry/", {"refresh": "true"}, client=self.mortal)
        refresh_index.assert_not_called()
        self.assertEqual(data["objects"][0]["slug"], "echo")

    def test_install_check_update(self):
        """An extension is installed from the registry, offered its update, and updated."""
        data = self.call("post", "install/", {"slug": "echo", "version": "1.0.0"})
        self.assertEqual(data["extension"]["installedVersion"], "1.0.0")
        self.assertIn("Echo 1.1.0", self.call("post", "check-updates/")["message"])
        data = self.call("post", "echo/update/")
        self.assertEqual(data["extension"]["installedVersion"], "1.1.0")
        self.assertIn("not valid", self.call("post", "install/", {}, expect=400)["detail"])
