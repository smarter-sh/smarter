# pylint: disable=wrong-import-position
# pylint: disable=R0801
"""Test lambda_openai_v2 function."""

from django.conf import settings
from django.template.loader import render_to_string
from django.test import RequestFactory
from django.urls import get_urlconf, set_urlconf

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.dashboard.views.views.urls import DashboardReverseNames

from ..context_processors import (
    active_sidebar_item,
    base,
    console_reverse,
    sidebar,
    sidebar_context,
)


class TestContextProcessor(TestAccountMixin):
    """Test Dashboard context processor."""

    # pylint: disable=broad-exception-caught
    def test_base(self):
        """Test base."""
        rf = RequestFactory()
        request = rf.get("/login/")
        request.user = self.non_admin_user
        test_context = base(request=request)

        self.assertIn("dashboard", test_context)

    def test_sidebar_on_a_deployed_llmclient_host(self):
        """The sidebar reverses console names even while a deployed LLMClient's urlconf is active."""
        sidebar_context.invalidate()
        self.addCleanup(sidebar_context.invalidate)
        previous = get_urlconf()
        self.addCleanup(set_urlconf, previous)
        set_urlconf("smarter.urls.llmclients")

        context = sidebar_context()

        self.assertEqual(
            context["sidebar"]["dashboard"],
            console_reverse(DashboardReverseNames.namespace, DashboardReverseNames.dashboard),
        )
        self.assertTrue(context["sidebar"]["secrets"].startswith("/"))

    def test_console_reverse_ignores_the_active_urlconf(self):
        """Console_reverse() resolves against settings.ROOT_URLCONF."""
        expected = console_reverse(DashboardReverseNames.namespace, DashboardReverseNames.dashboard)
        previous = get_urlconf()
        self.addCleanup(set_urlconf, previous)
        set_urlconf("smarter.urls.llmclients")

        self.assertEqual(console_reverse(DashboardReverseNames.namespace, DashboardReverseNames.dashboard), expected)
        self.assertEqual(settings.ROOT_URLCONF, "smarter.urls.console")


class TestActiveSidebarItem(TestAccountMixin):
    """The sidebar highlights the item of the page, however the user reached it."""

    def test_longest_url_that_begins_the_path(self):
        """A resource's page is under its list's url, and the longest such url wins."""
        links = {"dashboard": "/dashboard/", "llmhost": "/llmhost/", "llmhostcompute": "/llmhost/compute/"}
        self.assertEqual(active_sidebar_item("/llmhost/llmhosts/rMQx/", links), "llmhost")
        self.assertEqual(active_sidebar_item("/llmhost/compute/rMQx/", links), "llmhostcompute")
        self.assertEqual(active_sidebar_item("/dashboard/", links), "dashboard")
        self.assertIsNone(active_sidebar_item("/login/", links))

    def test_sidebar_of_a_manifest_page(self):
        """A Secret's manifest page highlights Secrets, and the sidebar renders it as the current page."""
        request = RequestFactory().get("/secret/secrets/rMQx/")
        request.user = self.non_admin_user
        context = sidebar(request)
        self.assertEqual(context["sidebar_active"], "secrets")
        html = render_to_string("dashboard/sidebar.html", {**context, "request": request})
        secrets = context["sidebar"]["secrets"]
        self.assertRegex(html, rf'class="menu-link active"\s+href="{secrets}"\s+aria-current="page"')
        self.assertEqual(html.count('aria-current="page"'), 1)
