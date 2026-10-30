"""Test the error pages in smarter.lib.django.http.error_handlers."""

import threading
from http import HTTPStatus

from django.contrib.auth.models import AnonymousUser
from django.core.checks import run_checks
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.db import connection
from django.http import Http404
from django.test import RequestFactory
from django.urls import get_resolver

from smarter.lib.django.http import error_handlers
from smarter.lib.unittest.base_classes import SmarterTestBase

URLCONFS = ("smarter.urls.console", "smarter.urls.api", "smarter.urls.llmclients")

HANDLERS = {
    400: (error_handlers.bad_request, SuspiciousOperation()),
    403: (error_handlers.permission_denied, PermissionDenied()),
    404: (error_handlers.page_not_found, Http404()),
    500: (error_handlers.server_error, None),
}


class TestErrorHandlers(SmarterTestBase):
    """Test that each error page renders, and closes the connections of the thread that rendered it."""

    def request(self):
        """A GET of a page that doesn't exist, from an anonymous visitor."""
        request = RequestFactory().get("/favicon.ico")
        request.user = AnonymousUser()
        return request

    def render_in_thread(self, status: int) -> tuple[int, bool]:
        """
        Render an error page in a new thread, as Django's ASGI handler does.

        The thread queries the database first, so it has a connection open. Returns the page's
        status, and whether the thread's connection is still open after the page rendered.
        """
        view, exception = HANDLERS[status]
        result = {}

        def run():
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            args = (self.request(),) if exception is None else (self.request(), exception)
            result["status"] = view(*args).status_code
            result["open"] = connection.connection is not None

        thread = threading.Thread(target=run)
        thread.start()
        thread.join()
        return result["status"], result["open"]

    def test_each_page_closes_its_threads_connection(self):
        """The 400, 403, 404 and 500 pages render, and leave no connection open in their thread."""
        for status in HANDLERS:
            with self.subTest(status=status):
                self.assertEqual(self.render_in_thread(status), (status, False))

    def test_page_not_found_renders_smarters_404_page(self):
        """The 404 page is Smarter's 404.html, rendered with the request's context processors."""
        response = error_handlers.page_not_found(self.request(), Http404())
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertIn(b"<html", response.content.lower())

    def test_closes_connections_when_the_view_raises(self):
        """The connections are closed even when the error view itself fails."""

        def failing(request, exception):
            raise RuntimeError("boom")

        view = error_handlers.closing_connections(failing)
        connection.ensure_connection()
        with self.assertRaises(RuntimeError):
            view(self.request(), Http404())
        self.assertIsNone(connection.connection)

    def test_every_urlconf_uses_them(self):
        """Every urlconf that a host routes to names these views as its error handlers."""
        for urlconf in URLCONFS:
            for status, (view, _) in HANDLERS.items():
                with self.subTest(urlconf=urlconf, status=status):
                    self.assertIs(get_resolver(urlconf).resolve_error_handler(status), view)

    def test_docstrings_avoid_admindocs_roles(self):
        """Their docstrings aren't Django's, whose ``:template:`` role crashes the Sphinx build."""
        for status, (view, _) in HANDLERS.items():
            with self.subTest(status=status):
                self.assertNotIn(":template:", view.__doc__)
                self.assertIn(f"django.views.defaults.{view.__name__}", view.__doc__)

    def test_django_accepts_their_signatures(self):
        """Django's system check of custom error handlers finds nothing wrong."""
        errors = [e for e in run_checks(tags=["urls"]) if e.id == "urls.E007"]
        self.assertEqual(errors, [])
