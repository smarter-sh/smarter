"""Tests of smarter.apps.dashboard.views.console_app: Django serving the single-page console's page."""

import tempfile
from http import HTTPStatus
from pathlib import Path

from django.conf import settings
from django.test import Client, override_settings

from smarter.apps.account.urls import AccountReverseNames
from smarter.apps.dashboard.views.console_app import (
    CONSOLE_INDEX_PATH,
    console_index_html,
)
from smarter.lib.django.shortcuts import reverse
from smarter.lib.unittest.base_classes import SmarterTestBase
from smarter.urls.console import ConsoleReverseNames

INDEX_HTML = '<!doctype html><html><body><div id="smarter-console-root"></div></body></html>'


class TestConsoleApp(SmarterTestBase):
    """The paths that moved into the console answer with its page, from a STATIC_ROOT with a built console."""

    def setUp(self):
        super().setUp()
        static_root = tempfile.TemporaryDirectory()
        self.addCleanup(static_root.cleanup)
        index_path = Path(static_root.name) / CONSOLE_INDEX_PATH
        index_path.parent.mkdir(parents=True)
        index_path.write_text(INDEX_HTML, encoding="utf-8")
        built = override_settings(STATIC_ROOT=static_root.name)
        built.enable()
        self.addCleanup(built.disable)
        self.client = Client()

    def console_paths(self) -> list[str]:
        reset_link = reverse(AccountReverseNames.PASSWORD_RESET_LINK, kwargs={"uidb64": "MTk1NA", "token": "abc-123"})
        return [
            reverse(ConsoleReverseNames.login_view),
            reverse(ConsoleReverseNames.register_view),
            reverse(AccountReverseNames.ACCOUNT_PASSWORD_RESET_REQUEST),
            reset_link,
        ]

    def test_paths_keep_their_urls(self):
        """The moved pages keep the paths that emails, settings and templates use."""
        self.assertEqual(
            self.console_paths(),
            ["/login/", "/register/", "/password-reset-request/", "/password-reset-link/MTk1NA/abc-123/"],
        )
        self.assertEqual(settings.LOGIN_URL, "/login/")

    def test_paths_serve_the_console(self):
        """Each moved path answers with the console's page, uncached, and sets the CSRF cookie."""
        for path in self.console_paths():
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, HTTPStatus.OK)
                self.assertIn("smarter-console-root", response.content.decode())
                self.assertIn("no-cache", response["Cache-Control"])
                self.assertIn(settings.CSRF_COOKIE_NAME, response.cookies)

    def test_a_signed_in_user_gets_the_page_too(self):
        """The console's router, not Django, sends a signed-in user on from the sign-in page."""
        response = self.client.get("/login/")
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_only_get(self):
        self.assertEqual(self.client.post("/login/").status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_index_html(self):
        self.assertEqual(console_index_html(), INDEX_HTML)


class TestConsoleAppNotBuilt(SmarterTestBase):
    """Without a built console, the moved paths answer 503 and say why."""

    def test_not_built(self):
        with tempfile.TemporaryDirectory() as empty_static_root:
            with override_settings(STATIC_ROOT=empty_static_root):
                self.assertIsNone(console_index_html())
                response = Client().get("/login/")
        self.assertEqual(response.status_code, HTTPStatus.SERVICE_UNAVAILABLE)
        self.assertIn("hasn't been built", response.content.decode())
