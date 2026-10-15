"""Tests of smarter.apps.llmtool.extension.admin: the Extensions pages of the Django admin console."""

from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

from smarter.apps.llmtool.extension import registry
from smarter.apps.llmtool.models import Extension, ExtensionSetting
from smarter.apps.secret.models import Secret

from .mixins import ExtensionTestMixin, fixture_archive
from .test_registry import RegistryTestMixin

BASE = "/admin/llmtool/extension/"


class AdminClientMixin:
    """A Django test client, logged in as the test's superuser."""

    def assertRedirectsTo(self, response, url: str) -> None:  # pylint: disable=invalid-name
        """Assert that a response redirects to ``url``."""
        self.assertEqual(response.status_code, 302)  # type: ignore[attr-defined]
        self.assertEqual(response["Location"], url)  # type: ignore[attr-defined]

    def client_for(self, user) -> Client:
        client = Client()
        client.force_login(user)
        self.addCleanup(client.logout)  # type: ignore[attr-defined]
        return client


class TestExtensionAdmin(AdminClientMixin, ExtensionTestMixin):
    """Test the installed extensions' pages."""

    def setUp(self):
        super().setUp()
        self.client = self.client_for(self.admin_user)

    def test_changelist(self):
        """The Extensions page lists the installed extensions, with the browse and upload buttons."""
        self.install_echo()
        response = self.client.get(BASE)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("Echo", content)
        self.assertIn("Browse extensions", content)
        self.assertIn("Upload extension", content)
        self.assertEqual(self.client.get(BASE + "?update_available=yes").status_code, 200)

    def test_non_superuser_is_refused(self):
        """Only superusers see the Extensions pages."""
        client = self.client_for(self.non_admin_user)
        self.assertNotEqual(client.get(BASE).status_code, 200)

    def test_change_page(self):
        """An extension's page shows its tools, settings, switches, documentation, and actions."""
        extension = self.install_echo()
        self.installer.install(fixture_archive("echo", version="1.1.0"))
        extension.refresh_from_db()
        extension.latest_version = "2.0.0"
        extension.error = "something went wrong"
        extension.save()
        content = self.client.get(f"{BASE}{extension.pk}/change/").content.decode()
        for text in (
            "<code>echo</code>",
            "<code>api_key</code>: not set (required)",
            "ext_echo_verbose",
            "Echoes what it is sent",
            "Configure settings",
            "Enable",
            "Version 2.0.0 of Echo is available",
            "something went wrong",
            "Roll back to 1.0.0",
        ):
            with self.subTest(text=text):
                self.assertIn(text, content)

    def test_upload(self):
        """Uploading an archive installs it, disabled; an invalid archive is an error."""
        self.assertEqual(self.client.get(BASE + "upload/").status_code, 200)
        upload = SimpleUploadedFile("echo-1.0.0.zip", fixture_archive("echo"), content_type="application/zip")
        response = self.client.post(BASE + "upload/", {"archive": upload})
        extension = Extension.objects.get(slug="echo")
        self.assertRedirectsTo(response, f"{BASE}{extension.pk}/change/")
        self.assertFalse(extension.enabled)
        response = self.client.post(
            BASE + "upload/", {"archive": SimpleUploadedFile("x.zip", b"not a zip")}, follow=True
        )
        self.assertIn("not a zip file", response.content.decode())

    def test_configure_enable_disable(self):
        """Settings are saved from the generated form, a typed secret becomes a Secret, and the extension is enabled and disabled."""
        extension = self.install_echo()
        url = f"{BASE}{extension.pk}/configure/"
        self.assertIn("Api key: new value", self.client.get(url).content.decode())
        response = self.client.post(f"{BASE}{extension.pk}/enable/", follow=True)
        self.assertIn("needs these settings first", response.content.decode())

        response = self.client.post(url, {"greeting": "hi", "repeat": "2", "api_key__new": "typed-secret"})
        self.assertRedirectsTo(response, f"{BASE}{extension.pk}/change/")
        secret = Secret.objects.get(name="extension_echo_api_key")
        self.secrets.append(secret)
        self.assertEqual(secret.get_secret(), "typed-secret")
        self.assertEqual(ExtensionSetting.objects.get(extension=extension, name="repeat").value, "2")

        self.client.post(url, {"greeting": "", "repeat": "", "api_key": secret.pk})
        self.assertFalse(ExtensionSetting.objects.filter(extension=extension, name="greeting").exists())

        self.client.post(f"{BASE}{extension.pk}/enable/")
        self.assertTrue(Extension.objects.get(pk=extension.pk).enabled)
        self.client.post(f"{BASE}{extension.pk}/disable/")
        self.assertFalse(Extension.objects.get(pk=extension.pk).enabled)

    def test_actions(self):
        """The enable and disable actions report their results."""
        extension = self.enable_echo()
        self.installer.disable(extension)
        response = self.client.post(
            BASE, {"action": "enable_selected", "_selected_action": [extension.pk]}, follow=True
        )
        self.assertIn("Enabled echo", response.content.decode())
        response = self.client.post(
            BASE, {"action": "disable_selected", "_selected_action": [extension.pk]}, follow=True
        )
        self.assertIn("Disabled echo", response.content.decode())

    def test_rollback(self):
        """An earlier version is rolled back to from its button."""
        extension = self.install_echo()
        old = extension.installed_version
        self.installer.install(fixture_archive("echo", version="1.1.0"))
        self.client.post(f"{BASE}{extension.pk}/rollback/{old.pk}/")  # type: ignore[union-attr]
        self.assertEqual(Extension.objects.get(pk=extension.pk).installed_version.version, "1.0.0")  # type: ignore[union-attr]

    def test_delete_uninstalls(self):
        """Deleting an extension uninstalls it, with its resources."""
        extension = self.install_echo()
        self.client.post(f"{BASE}{extension.pk}/delete/", {"post": "yes"})
        self.assertFalse(Extension.objects.filter(slug="echo").exists())
        self.assertFalse(Secret.objects.filter(name="echo_extension_test_secret").exists())

    def test_add_is_not_allowed(self):
        """Extensions are installed by upload or from the registry, not added."""
        self.assertEqual(self.client.get(BASE + "add/").status_code, 403)

    def test_registry_disabled(self):
        """Browsing a disabled registry says why."""
        with patch.object(registry, "is_enabled", return_value=False):
            response = self.client.get(BASE + "browse/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("disabled until SMARTER_EXTENSION_REGISTRY_PUBLIC_KEY is set", response.content.decode())


class TestExtensionAdminRegistry(AdminClientMixin, RegistryTestMixin):
    """Test browsing, installing and updating from the registry in the admin console."""

    def setUp(self):
        super().setUp()
        self.client = self.client_for(self.admin_user)

    def test_browse(self):
        """The registry's extensions are listed with their badges, and filtered."""
        content = self.client.get(BASE + "browse/").content.decode()
        self.assertIn("Echoes what it is sent.", content)
        self.assertIn("Official Smarter Extension", content)
        self.assertIn("Install 1.1.0", content)
        self.assertIn("No extensions match.", self.client.get(BASE + "browse/?q=nothing").content.decode())
        self.assertIn("No extensions match.", self.client.get(BASE + "browse/?badge=community").content.decode())

    def test_browse_detail_and_install(self):
        """An extension's documentation is shown, and it is installed and updated from the registry."""
        content = self.client.get(BASE + "browse/echo/").content.decode()
        self.assertIn("<p>Echoes.</p>", content)
        response = self.client.post(BASE + "install/echo/", {"version": "1.0.0"})
        extension = Extension.objects.get(slug="echo")
        self.assertRedirectsTo(response, f"{BASE}{extension.pk}/change/")
        self.assertIn("Update to 1.1.0", self.client.get(BASE + "browse/").content.decode())

        response = self.client.post(BASE + "check-updates/", follow=True)
        self.assertIn("Updates are available: echo 1.1.0", response.content.decode())
        self.client.post(f"{BASE}{extension.pk}/update/")
        self.assertEqual(Extension.objects.get(pk=extension.pk).installed_version.version, "1.1.0")  # type: ignore[union-attr]
        response = self.client.post(BASE + "check-updates/", follow=True)
        self.assertIn("Every extension is up to date.", response.content.decode())

    def test_browse_errors(self):
        """An unknown extension, or a failed install, returns to the registry with an error."""
        response = self.client.get(BASE + "browse/nope/", follow=True)
        self.assertIn("The registry has no extension nope", response.content.decode())
        response = self.client.post(BASE + "install/echo/", {"version": "9.9.9"}, follow=True)
        self.assertIn("no version 9.9.9", response.content.decode())
