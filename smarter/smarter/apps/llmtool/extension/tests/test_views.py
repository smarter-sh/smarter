"""Tests of smarter.apps.llmtool.extension.views: the web console's Extensions pages and their api."""

import json
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from waffle.models import Switch

from smarter.apps.llmtool.extension import views
from smarter.apps.llmtool.extension.urls import API
from smarter.apps.llmtool.models import Extension, ExtensionSetting
from smarter.apps.secret.models import Secret

from .mixins import ECHO_SECRET, ExtensionTestMixin, fixture_archive
from .test_registry import RegistryTestMixin

PAGE = "/extensions/"
BASE = f"/extensions/{API}"
SECRET_VALUE = "never-show-this-value"


class ConsoleClientMixin:
    """Django test clients for the superuser and the non-superuser, and a JSON POST helper."""

    def setUp(self):
        super().setUp()  # type: ignore[misc]
        self.client = self.client_for(self.admin_user)  # type: ignore[attr-defined]

    def client_for(self, user) -> Client:
        client = Client()
        client.force_login(user)
        self.addCleanup(client.logout)  # type: ignore[attr-defined]
        return client

    def post(self, path: str, body=None, client=None, expect: int = 200) -> dict:
        """POST JSON to the api, check the status, and return the response's JSON."""
        response = (client or self.client).post(
            BASE + path, data=json.dumps(body or {}), content_type="application/json"
        )
        self.assertEqual(response.status_code, expect, response.content[:500])  # type: ignore[attr-defined]
        return response.json()


class TestExtensionPages(ConsoleClientMixin, ExtensionTestMixin):
    """Test the pages that host the React app."""

    def test_list_page(self):
        """The list page renders the React app's root element with the api's url."""
        response = self.client.get(PAGE)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('id="smarter-extension-list-root"', content)
        self.assertIn(f'smarter-extension-api-url="{BASE}"', content)

    def test_detail_page(self):
        """An installed extension's page renders the React app with its slug; an unknown one is a 404."""
        self.install_echo()
        content = self.client.get(PAGE + "echo/").content.decode()
        self.assertIn('id="smarter-extension-detail-root"', content)
        self.assertIn('smarter-extension-slug="echo"', content)
        self.assertEqual(self.client.get(PAGE + "nope/").status_code, 404)

    def test_superusers_only(self):
        """The pages and the api are for superusers only."""
        client = self.client_for(self.non_admin_user)
        self.assertEqual(client.get(PAGE).status_code, 403)
        self.assertEqual(client.get(PAGE + "echo/").status_code, 403)
        self.assertIn("superusers", self.post("list/", client=client, expect=403)["error"])

    def test_api_is_post_only(self):
        """The api answers only POST."""
        self.assertEqual(self.client.get(BASE + "list/").status_code, 405)


class TestExtensionApi(ConsoleClientMixin, ExtensionTestMixin):
    """Test the api's views of installed extensions, and their actions."""

    def test_list(self):
        """The list has every installed extension, its state, and the number of updates."""
        extension = self.install_echo()
        extension.latest_version = "9.0.0"
        extension.save()
        data = self.post("list/")
        echo = next(item for item in data["objects"] if item["slug"] == "echo")
        self.assertEqual(echo["displayName"], "Echo")
        self.assertEqual(echo["trustBadgeLabel"], "Unverified")
        self.assertEqual(echo["installedVersion"], "1.0.0")
        self.assertTrue(echo["updateAvailable"])
        self.assertEqual(echo["detailUrl"], PAGE + "echo/")
        self.assertGreaterEqual(data["updatesAvailable"], 1)
        self.assertIn("registryEnabled", data)
        self.assertEqual(self.post("", {})["objects"], data["objects"])

    def test_detail(self):
        """The detail has the extension's tools, settings, switches, versions and resources."""
        self.install_echo()
        detail = self.post("extensions/echo/")["extension"]
        self.assertIn("ext_echo_echo", [tool["functionName"] for tool in detail["tools"]])
        self.assertEqual(detail["missingSettings"], ["api_key"])
        api_key = next(setting for setting in detail["settings"] if setting["name"] == "api_key")
        self.assertEqual((api_key["type"], api_key["isSet"], api_key["required"]), ("secret", False, True))
        self.assertEqual([switch["name"] for switch in detail["switches"]], ["ext_echo_verbose"])
        self.assertEqual(
            [(resource["kind"], resource["name"]) for resource in detail["resources"]], [("Secret", ECHO_SECRET)]
        )
        self.assertEqual([version["version"] for version in detail["versions"]], ["1.0.0"])
        self.assertTrue(detail["versions"][0]["isInstalled"])
        self.assertIn("Echoes what it is sent", detail["docsHtml"])
        self.assertIsNone(detail["loadError"])
        self.assertIn("unknown", self.post("extensions/nope/", expect=404)["error"] + "unknown")

    def test_configure_and_enable(self):
        """Settings are saved, a typed secret becomes a Secret whose value is never returned, and the extension is enabled."""
        self.install_echo()
        self.assertIn("api_key", self.post("extensions/echo/enable/", expect=400)["error"])
        data = self.post(
            "extensions/echo/configure/",
            {"values": {"repeat": 2, "greeting": "hi"}, "secrets": {"api_key": {"value": SECRET_VALUE}}},
        )
        self.addCleanup(Secret.objects.filter(name="extension_echo_api_key").delete)
        self.assertNotIn(SECRET_VALUE, json.dumps(data))
        settings = {setting["name"]: setting for setting in data["extension"]["settings"]}
        self.assertEqual(settings["repeat"]["value"], 2)
        self.assertEqual(settings["api_key"]["secretName"], "extension_echo_api_key")
        self.assertIsNone(settings["api_key"]["value"])
        self.assertEqual(Secret.objects.get(name="extension_echo_api_key").get_secret(), SECRET_VALUE)

        data = self.post("extensions/echo/enable/")
        self.assertTrue(data["extension"]["enabled"])
        self.assertEqual(data["message"], "Enabled Echo.")
        self.assertFalse(self.post("extensions/echo/disable/")["extension"]["enabled"])

    def test_configure_with_an_existing_secret_and_clear(self):
        """A secret setting uses an existing Secret, and is cleared with neither."""
        self.install_echo()
        secret = self.secret("echo_views_key")
        self.post("extensions/echo/configure/", {"secrets": {"api_key": {"secretId": secret.pk}}})
        self.assertEqual(ExtensionSetting.objects.get(extension__slug="echo", name="api_key").secret, secret)
        self.post("extensions/echo/configure/", {"secrets": {"api_key": {}}, "values": {"greeting": None}})
        self.assertFalse(ExtensionSetting.objects.filter(extension__slug="echo", name="api_key").exists())

    def test_configure_errors(self):
        """Invalid requests and values are 400s with a message."""
        self.install_echo()
        cases = [
            ({"values": {"repeat": "many"}}, "repeat"),
            ({"secrets": {"repeat": {"value": "x"}}}, "no secret setting"),
            ({"secrets": {"api_key": {"secretId": 999999999}}}, "not one of"),
            ({"unknown": 1}, "not valid"),
        ]
        for body, message in cases:
            with self.subTest(body=body):
                self.assertIn(message, self.post("extensions/echo/configure/", body, expect=400)["error"])
        response = self.client.post(
            BASE + "extensions/echo/configure/", data="{not json", content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_availability(self):
        """An extension is restricted to listed accounts, or made available to all."""
        self.install_echo()
        data = self.post("extensions/echo/availability/", {"allAccounts": False, "accountIds": [self.account.pk]})
        self.assertFalse(data["extension"]["allAccounts"])
        self.assertEqual([account["id"] for account in data["extension"]["accounts"]], [self.account.pk])
        self.assertIn("every account", self.post("extensions/echo/availability/", {"allAccounts": True})["message"])
        self.assertIn(
            "do not exist",
            self.post("extensions/echo/availability/", {"allAccounts": False, "accountIds": [999999999]}, expect=400)[
                "error"
            ],
        )
        accounts = self.post("accounts/")["objects"]
        self.assertIn(self.account.pk, [account["id"] for account in accounts])

    def test_rollback(self):
        """An earlier version is rolled back to; an unknown version is an error."""
        self.install_echo()
        old = Extension.objects.get(slug="echo").installed_version
        self.installer.install(fixture_archive("echo", version="1.1.0"))
        data = self.post("extensions/echo/rollback/", {"versionId": old.pk})  # type: ignore[union-attr]
        self.assertEqual(data["extension"]["installedVersion"], "1.0.0")
        self.assertIn(
            "no version", self.post("extensions/echo/rollback/", {"versionId": 999999999}, expect=400)["error"]
        )

    def test_uninstall(self):
        """Uninstalling returns no extension, and deletes it."""
        self.install_echo()
        data = self.post("extensions/echo/uninstall/")
        self.assertIsNone(data["extension"])
        self.assertFalse(Extension.objects.filter(slug="echo").exists())

    def test_upload(self):
        """An archive is installed from a multipart upload; a missing or invalid one is an error."""
        upload = SimpleUploadedFile("echo-1.0.0.zip", fixture_archive("echo"), content_type="application/zip")
        response = self.client.post(BASE + "upload/", {"archive": upload})
        self.assertEqual(response.status_code, 200, response.content[:300])
        self.assertEqual(response.json()["extension"]["slug"], "echo")
        self.assertIn("Choose", self.client.post(BASE + "upload/").json()["error"])
        bad = SimpleUploadedFile("x.zip", b"not a zip")
        self.assertIn("not a zip", self.client.post(BASE + "upload/", {"archive": bad}).json()["error"])
        with patch.object(views, "MAX_UPLOAD_BYTES", 10):
            big = SimpleUploadedFile("echo.zip", fixture_archive("echo"))
            self.assertIn("larger", self.client.post(BASE + "upload/", {"archive": big}).json()["error"])

    def test_unexpected_errors(self):
        """An unexpected exception, e.g. in a lifecycle hook, is a 500 with its message."""
        self.install_echo()
        with patch.object(views.ExtensionInstaller, "disable", side_effect=RuntimeError("boom")):
            self.assertIn("RuntimeError: boom", self.post("extensions/echo/disable/", expect=500)["error"])

    def test_detail_of_broken_code(self):
        """An extension whose code no longer loads shows why, without tools."""
        self.install_echo()
        with patch.object(views, "load_version", side_effect=views.SmarterExtensionException("cannot import")):
            detail = self.post("extensions/echo/")["extension"]
        self.assertEqual(detail["loadError"], "cannot import")
        self.assertEqual(detail["tools"], [])

    def test_switch_state(self):
        """A switch's state is reported."""
        self.install_echo()
        Switch.objects.filter(name="ext_echo_verbose").update(active=True)
        self.assertTrue(self.post("extensions/echo/")["extension"]["switches"][0]["active"])


class TestExtensionRegistryApi(ConsoleClientMixin, RegistryTestMixin):
    """Test the api's registry views, against a signed index served by a patched transport."""

    def test_registry(self):
        """The registry's extensions are listed with what each offers."""
        data = self.post("registry/", {"refresh": True})
        self.assertTrue(data["enabled"])
        self.assertIsNone(data["error"])
        echo = data["objects"][0]
        self.assertEqual((echo["slug"], echo["action"], echo["latestVersion"]), ("echo", "install", "1.1.0"))
        self.assertEqual(echo["trustBadgeLabel"], "Official Smarter Extension")
        self.assertIn("<p>Echoes.</p>", echo["docsHtml"])
        self.assertEqual([version["version"] for version in echo["versions"]], ["9.0.0", "1.1.0", "1.0.0"])
        self.assertFalse(echo["versions"][0]["compatible"])

    def test_install_update_and_check(self):
        """An extension is installed, offered its update, and updated."""
        data = self.post("install/", {"slug": "echo", "version": "1.0.0"})
        self.assertEqual(data["extension"]["installedVersion"], "1.0.0")
        echo = self.post("registry/")["objects"][0]
        self.assertEqual((echo["action"], echo["installedVersion"]), ("update", "1.0.0"))
        self.assertIn("Echo 1.1.0", self.post("check-updates/")["message"])
        data = self.post("extensions/echo/update/")
        self.assertEqual(data["extension"]["installedVersion"], "1.1.0")
        self.assertEqual(self.post("registry/")["objects"][0]["action"], "installed")
        self.assertIn("up to date", self.post("check-updates/")["message"])

    def test_install_errors_and_uploads(self):
        """An unknown version is an error, and an uploaded extension is offered nothing."""
        self.assertIn("no version", self.post("install/", {"slug": "echo", "version": "7.0.0"}, expect=400)["error"])
        self.assertIn("not valid", self.post("install/", {}, expect=400)["error"])
        self.install_echo()
        self.assertEqual(self.post("registry/")["objects"][0]["action"], "uploaded")

    def test_registry_errors(self):
        """A disabled or unreachable registry says why."""
        with patch.object(views.registry, "is_enabled", return_value=False):
            data = self.post("registry/")
        self.assertFalse(data["enabled"])
        self.assertIn("SMARTER_EXTENSION_REGISTRY_PUBLIC_KEY", data["error"])
        with patch.object(views.registry, "get_index", side_effect=views.SmarterExtensionException("unreachable")):
            self.assertEqual(self.post("registry/")["error"], "unreachable")

    def test_incompatible(self):
        """An extension without a compatible version is offered nothing."""
        with patch.object(views.registry.RegistryExtension, "latest_compatible", return_value=None):
            self.assertEqual(self.post("registry/")["objects"][0]["action"], "incompatible")

    def test_is_newer(self):
        """Version comparison treats an unparsable version as never newer."""
        self.assertTrue(views.is_newer("1.1.0", "1.0.0"))
        self.assertTrue(views.is_newer("1.0.0", None))
        self.assertFalse(views.is_newer("1.0.0", "1.0.0"))
        self.assertFalse(views.is_newer("not a version", "1.0.0"))
