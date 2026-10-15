"""Tests of smarter.apps.llmtool.extension.admin: the read-only Extensions pages of the Django admin console."""

from django.test import Client

from smarter.apps.llmtool.models import Extension

from .mixins import ExtensionTestMixin, fixture_archive

BASE = "/admin/llmtool/extension/"


class TestExtensionAdmin(ExtensionTestMixin):
    """Test the installed extensions' read-only pages, which link to the web console."""

    def setUp(self):
        super().setUp()
        self.client = self.client_for(self.admin_user)

    def client_for(self, user) -> Client:
        client = Client()
        client.force_login(user)
        self.addCleanup(client.logout)
        return client

    def test_changelist(self):
        """The Extensions page lists the installed extensions, each linked to its console page."""
        self.install_echo()
        response = self.client.get(BASE)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("Echo", content)
        self.assertIn('href="/extensions/"', content)
        self.assertIn('href="/extensions/echo/"', content)
        self.assertIn("Manage in the console", content)
        self.assertNotIn("action-select", content)
        self.assertEqual(self.client.get(BASE + "?update_available=yes").status_code, 200)

    def test_non_superuser_is_refused(self):
        """Only superusers see the Extensions pages."""
        client = self.client_for(self.non_admin_user)
        self.assertNotEqual(client.get(BASE).status_code, 200)

    def test_change_page_is_read_only(self):
        """An extension's page shows its versions, update, error and documentation, and can't be saved."""
        extension = self.install_echo()
        self.installer.install(fixture_archive("echo", version="1.1.0"))
        extension.refresh_from_db()
        extension.latest_version = "2.0.0"
        extension.error = "something went wrong"
        extension.save()
        content = self.client.get(f"{BASE}{extension.pk}/change/").content.decode()
        for text in (
            'href="/extensions/echo/"',
            "Version 2.0.0 of Echo is available",
            "something went wrong",
            "Echoes what it is sent",
            "1.0.0",
            "1.1.0",
        ):
            with self.subTest(text=text):
                self.assertIn(text, content)
        self.assertNotIn('name="_save"', content)
        self.client.post(f"{BASE}{extension.pk}/change/", {"enabled": "on"})
        self.assertFalse(Extension.objects.get(pk=extension.pk).enabled)

    def test_add_and_delete_are_not_allowed(self):
        """Extensions are installed and uninstalled in the console, not added or deleted here."""
        extension = self.install_echo()
        self.assertEqual(self.client.get(BASE + "add/").status_code, 403)
        self.assertEqual(self.client.post(f"{BASE}{extension.pk}/delete/", {"post": "yes"}).status_code, 403)
        self.assertTrue(Extension.objects.filter(slug="echo").exists())
